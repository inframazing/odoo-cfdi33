# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    name = fields.Char(copy=False)

    impuesto = fields.Selection(
        [
            ('002', 'IVA'),
            ('003', ' IEPS'),
            ('001', 'ISR'),
            ('004', 'ISH')
        ], string='Impuesto aplica a', default='002', required=True)
    
    tipo_factor = fields.Selection(
        [
            ('Tasa', 'Tasa'),
            ('Cuota', 'Cuota'),
            ('Exento', 'Exento')
        ], string='Tipo factor', default='Tasa', required=True)

    @api.onchange('tipo_factor')
    def _onchange_tipo(self):
        if self.tipo_factor == 'Tasa':
            self.amount_type = 'percent'
        elif self.tipo_factor == 'Cuota':
            self.amount_type = 'fixed'
        else:
            self.amount_type = 'percent'
            self.amount = 0.0
