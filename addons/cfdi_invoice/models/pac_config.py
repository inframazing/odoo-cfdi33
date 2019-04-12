# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning
from suds.client import Client
from suds.sudsobject import asdict
import base64
from OpenSSL import crypto
import tempfile
from subprocess import check_output, CalledProcessError
import subprocess

import logging

_logger = logging.getLogger("========= PAC =========")


class PacConfig(models.Model):
    _name = 'cfdi.pac.config'

    name = fields.Char('Identificador del Registro', required=True)
    user = fields.Char('Usuario', required=True)
    password = fields.Char('Contraseña', required=True)
    url = fields.Char('URL del Servicio de Timbrado', required=True)
    timbrar = fields.Char('Función para Timbrar', required=True)
    cancelar = fields.Char('Función para Cancelar', required=True)
    cer = fields.Binary('Certificado (CER)', required=True)
    cer_name = fields.Char('Cer file name')
    key = fields.Binary('Llave (KEY)', required=True)
    key_name = fields.Char('Key file name')
    key_pem = fields.Char('KEY PEM', compute='_compute_key_pem', store=True)
    contrasena = fields.Char('Contraseña de la llave', required=True)
    no_cer = fields.Char('No. Certificado', compute='_compute_cer', store=True)
    start_date = fields.Date('Inicio Vigencia', compute='_compute_cer', store=True)
    end_date = fields.Date('Fin Vigencia', compute='_compute_cer', store=True)
    active = fields.Boolean('Activo', default=True)
    timbres = fields.Integer('Timbres usados')
    cancelaciones = fields.Integer('Cancelaciones usadas')
    acuse = fields.Char('Acuse de cancelación', required=True)
    status = fields.Char(string='Status CFDI', required=True)

    @api.onchange('url')
    def _check_url(self):
        if self.url and len(self.url) > 0:
            try:
                client = Client(self.url)
            except:
                raise Warning('No es posible conectarse con el PAC en la URL especificada.')

    @api.depends('cer')
    def _compute_cer(self):
        for r in self:
            if r.cer and len(r.cer) > 0:
                cer = crypto.load_certificate(crypto.FILETYPE_ASN1, base64.b64decode(r.cer))
                no_cer = "%x" % cer.get_serial_number()
                r.no_cer = no_cer.replace('33', '@').replace('3', '').replace('@', '3')
                r.start_date = cer.get_notBefore()[:4] + "-" + cer.get_notBefore()[4:6] + "-" + cer.get_notBefore()[6:8]
                r.end_date = cer.get_notBefore()[:4] + "-" + cer.get_notBefore()[4:6] + "-" + cer.get_notBefore()[6:8]

    @api.depends('key', 'contrasena')
    def _compute_key_pem(self):
        for r in self:
            if r.key and r.contrasena and len(r.key) > 0 and len(r.contrasena) > 0:
                fname_key = tempfile.NamedTemporaryFile().name
                file_key = open(fname_key, "wb")
                file_key.write(base64.b64decode(r.key))
                file_key.flush()
                file_key.close()
                fname_password = tempfile.NamedTemporaryFile().name
                file_password = open(fname_password, "w")
                file_password.write(r.contrasena.encode('iso-8859-1'))
                file_password.flush()
                file_password.close()
                cmd = 'openssl pkcs8 -inform DER -outform PEM -in %s -passin file:%s' % (
                    fname_key, fname_password)
                args = cmd.split(' ')
                try:
                    output = check_output(args, stderr=subprocess.STDOUT)
                except CalledProcessError as e:
                    raise Warning("No se puede abrir la llave (key) con la contraseña proporcionada.\n"
                                  "¿Selecciono el archivo correcto?\n"
                                  "¿La contraseña es correcta, incluyendo mayúsculas y minúsculas?\n"
                                  "%s" % e.output)
                r.key_pem = output

    def _to_dict(self, d):
        out = {}
        for k, v in asdict(d).iteritems():
            if hasattr(v, '__keylist__'):
                out[k] = self._to_dict(v)
            elif isinstance(v, list):
                out[k] = []
                for item in v:
                    if hasattr(item, '__keylist__'):
                        out[k].append(self._to_dict(item))
                    else:
                        out[k].append(item)
            else:
                if isinstance(v, str):
                    v = v.decode('utf-8', errors='ignore')
                if isinstance(v, unicode):
                    v = v.encode('utf-8', errors='ignore')
                out[k] = v
        return out

    '''
     Este método es el que realizará solicitud de timbrado 
    '''
    def timbrar_xml(self, object, xml):
        user = self.user
        password = self.password
        url = self.url
        client = Client(url)
        method = getattr(client.service, self.timbrar)
        response = method(user, password, base64.b64encode(xml))
        dict = self._to_dict(response)
        _logger.info(dict)
        return {
            'validate': dict['validate'],  # Boolean
            'xml': dict['xml'],  # Base64 XML with timbre fiscal
            'uuid': dict['uuid'],
            'code': dict['codigo'],
            'description': dict['mensaje'],
        }

    def cancelar_carta(self, uuid):
        user = self.user
        password = self.password
        rfc = self.env.user.company_id.vat[2:]
        certificado = self.cer
        llave = self.key
        password_llave = self.contrasena
        url = self.url
        client = Client(url)
        method = getattr(client.service, self.cancelar)
        response = method(user, password, rfc, uuid, certificado, llave, password_llave)
        return self._to_dict(response)

    '''
     Este es quien realiza la solicitud para la cancelación de los CFDI, de acuerdo a las reglas establecidas
    '''
    def cancelar_cfdi(self, receptor, total, uuid):
        user = self.user
        password = self.password
        emisor = self.env.user.company_id.vat
        certificado = self.cer
        llave = self.key
        password_llave = self.contrasena
        url = self.url
        client = Client(url)
        method = getattr(client.service, self.cancelar)
        response = method(user, password, emisor, receptor, uuid, str(total), certificado, llave, password_llave)
        dict = self._to_dict(response)
        _logger.info(dict)
        return {
            'validate': int(dict['codigo']) == 201,
            'code': dict['codigo'],
            'description': dict['mensaje'],
            'estado': dict['estado'],
            'EsCancelable': dict['EsCancelable'],
            'EstatusCancelacion': dict['EstatusCancelacion']
        }

    '''
     Este método es el que realizará la descarga del xml de acuse de cancelación
    '''
    def descargar_acuse(self, uuid):
        user = self.user
        password = self.password
        url = self.url
        client = Client(url)
        method = getattr(client.service, self.acuse)
        response = method(user, password, uuid)
        dict = self._to_dict(response)
        _logger.info(dict)
        return {
            'validate': int(dict['codigo']) == 100,
            'code': dict['codigo'],
            'description': dict['mensaje'],
            'xml': dict['acuse'],
        }
    
    '''
     Este método es el que realiza la consulta para verificar el estado en el que se encuentra el CFDI.
    '''
    def consultar_status(self,invoice):
        user = self.user
        password = self.password
        emisor = self.env.user.company_id.vat
        url = self.url
        client = Client(url)
        method = getattr(client.service, self.status)
        response = method(user, password, emisor, invoice['receptor'], invoice['total'], invoice['uuid'])
        dict = self._to_dict(response)
        _logger.info(dict)
        return {
            'validate': int(dict['codigo']) == 100,
            'code': dict['codigo'],
            'description': dict['mensaje'],
            'estado': dict['estado'],
            'EsCancelable': dict['EsCancelable'],
            'EstatusCancelacion': dict['EstatusCancelacion']
        }