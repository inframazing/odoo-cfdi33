# -*- coding: utf-8 -*-

import re
from odoo import fields, models, api
from odoo.exceptions import Warning
import logging


class ResPartner(models.Model):
    _inherit = 'res.partner'

    name = fields.Char(required=True)
    forma_pago = fields.Many2one('sat.forma.pago', string='Forma de pago',default=lambda self: self.get_default_id('cfdi_invoice.sat_forma_pago_03'))
    metodo_pago = fields.Many2one('sat.metodo.pago', string='Método de pago',default=lambda self: self.get_default_id('cfdi_invoice.sat_metodo_pago_PPD'))
    uso_cfdi = fields.Many2one('sat.uso.cfdi', string='Uso CFDI (cliente)',default=lambda self: self.get_default_id('cfdi_invoice.sat_uso_cfdi_P01'))
    customer = fields.Boolean(default=False)
    supplier = fields.Boolean(default=False)

    def get_default_id(self, ref):
        try:
            return self.env.ref(ref).id
        except:
            return False

    @api.constrains("vat")
    def check_vat(self):
        return

    @api.one
    @api.constrains('vat')
    def valida_RFC(self):
        if self.parent_id == False:
            if self.vat == False:
                raise Warning("Error de Validacion : El cliente %s no tiene ningun RFC asignado, favor de asignarlo primero" % (self.name))
            else:
                if self.company_type == 'company':
                    # Valida RFC en base al patron de una persona Moral
                    if len(self.vat) != 12:
                        raise Warning(
                            "El RFC %s no tiene la logitud de 12 caracteres para personas Morales que establece el sat" % (self.vat))
                    else:
                        patron_rfc = re.compile(
                            r'^([A-ZÑ\x26]{3}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                        if not patron_rfc.search(self.vat):
                            msg = "Formato RFC de Persona Moral Incorrecto"
                            raise Warning(msg)
                elif self.company_type == 'person':
                    # Valida el RFC en base al patron de una Persona Fisica
                    if len(self.vat) != 13:
                        raise Warning(
                            "El RFC %s no tiene la logitud de 13 caracteres para personas Fisicas que establece el sat" % (self.vat))
                    else:
                        patron_rfc = re.compile(
                            r'^([A-ZÑ\x26]{4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                        if not patron_rfc.search(self.vat):
                            msg = "Formato RFC de Persona Fisica Incorrecto"
                            raise Warning(msg)
