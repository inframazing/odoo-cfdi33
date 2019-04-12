# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
import logging
import zipfile
import base64
from os.path import basename
import re


_log = logging.getLogger("========= WIZARD TIMBRADO =========")


class WizardDownloadInvoice(models.TransientModel):
    _name = "wizard.cfdi_download_invoice"

    rfc = fields.Char('RFC', size=13)
    folio = fields.Char('Folio', size=5)
    cliente = fields.Many2one('res.partner', string="Cliente")
    fecha_inicio = fields.Date('Fecha inicial')
    fecha_fin = fields.Date('Fecha final')
    busqueda = fields.Selection([
        ('rfc', 'RFC'),
        ('folio', 'Folio'),
        ('cliente', 'Cliente'),
        ('fechas', 'Rango de fechas',)
    ], default='rfc', string="Tipo de búsqueda")
    file_name = fields.Char('Nombre de archivo')
    file_zip = fields.Binary('Archivo')

    @api.multi
    def download_zip(self):
        if self.busqueda == 'rfc':
            rule = re.compile(
                r'^([A-ZÑ\x26]{3,4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
            if not rule.search(self.rfc):
                msg = "Formato de RFC Invalido\n"
                msg = msg + "El formato correcto es el siguiente:\n\n"
                msg = msg + "-Apellido Paterno (del cual se van a utilizar las primeras 2 letras). \n"
                msg = msg + "-Apellido Materno (de este solo se utilizará la primera letra).\n"
                msg = msg + "-Nombre(s) (sin importar si tienes uno o dos nombres, solo se utilizará la primera letra del primer nombre).\n"
                msg = msg + "-Fecha de Nacimiento (día, mes y año).\n"
                msg = msg + "-Sexo (Masculino o Femenino).\n"
                msg = msg + "-Entidad Federativa de nacimiento (Estado en el que fue registrado al nacer)."
                raise Warning(msg)
            invoices = self.env["account.invoice"].search(['&', ('cfdi', '=', 'true'),
                                                           ('partner_id.vat', '=', self.rfc)])
            self.fill_zip(invoices, 'RFC')
        elif self.busqueda == 'folio':
            invoices = self.env["account.invoice"].search(['&', ('cfdi', '=', 'true'),
                                                           ('number', 'like', self.folio)])
            self.fill_zip(invoices, 'folio')
        elif self.busqueda == 'cliente':
            invoices = self.env["account.invoice"].search(['&', ('cfdi', '=', 'true'),
                                                           ('partner_id.name', '=', self.cliente.name)])
            self.fill_zip(invoices, 'cliente')
        else:
            if self.fecha_inicio > self.fecha_fin:
                raise Warning("La fecha inicial no puede ser mayor a la fecha final")

            invoices = self.env["account.invoice"].search(['&', '&', ('cfdi', '=', 'true'),
                                                           ('create_date', '>=', self.fecha_inicio),
                                                           ('create_date', '<=', self.fecha_fin)])
            self.fill_zip(invoices, 'rango de fechas')

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/wizard.cfdi_download_invoice/%s/file_zip/file.zip' % (
                self.id),
            'target': 'new',
        }

    @api.multi
    def fill_zip(self, invoices, busqueda):
        if(len(invoices) > 0):
            zf = zipfile.ZipFile('/tmp/example.zip', 'w', zipfile.ZIP_DEFLATED)
            i = 0
            for invoice in invoices:
                if invoice.cfdi:
                    try:
                        if i < 5:
                            file_xml = ""
                            if invoice.number:
                                file_xml = "/tmp/%s.xml" % str(invoice.number).replace("/", "_")
                            else:
                                file_xml += "/tmp/%s.xml" % str(invoice.uuid)
                            f = open(file_xml, 'w')
                            f.write(base64.b64decode(invoice.xml_cfdi))
                            f.close()

                            if invoice.state == 'cancel' and invoice.xml_acuse:
                                file_acuse_xml = ""
                                if invoice.number:
                                    file_acuse_xml = "/tmp/acuse_%s.xml" % str(invoice.number).replace("/", "_")
                                else:
                                    file_acuse_xml = "/tmp/acuse_%s.xml" % str(invoice.uuid)
                                f = open(file_acuse_xml, 'w')
                                f.write(base64.b64decode(invoice.xml_acuse))
                                f.close()
                                zf.write(file_acuse_xml, basename(file_acuse_xml))

                            zf.write(file_xml, basename(file_xml))

                            pdf_bin = self.env["report"].get_pdf([invoice.id], "cfdi_invoice.invoice_report_template",
                                                                 data={})
                            file_pdf = ""
                            if invoice.number:
                                file_pdf = "/tmp/%s.pdf" % str(invoice.number).replace("/", "_")
                            else:
                                file_pdf = "/tmp/%s.pdf" % str(invoice.uuid)

                            f = open(file_pdf, 'w')
                            f.write(pdf_bin)
                            f.close()

                            zf.write(file_pdf, basename(file_pdf))
                        i = i + 1
                    finally:
                        pass

            try:
                f = open('/tmp/Leeme.txt', 'w')
                f.write('Sistema desarrollado por DESITEG https://desiteg.tk')
                f.close()
                file_x = "/tmp/Leeme.txt"
                zf.write(file_x, basename(file_x))
            finally:
                zf.close()
            with open('/tmp/example.zip', 'rb') as fin:
                bytes_ok = fin.read()
                bs = bytes_ok.encode("base64")
                self.write({
                    'file_name': 'file.zip',
                    'file_zip': bs
                })
                self.env.cr.commit()
        else:
            warning = u"La búsqueda por %s no arrojo resultados." % busqueda
            raise Warning(warning)