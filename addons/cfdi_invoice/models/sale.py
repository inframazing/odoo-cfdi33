# -*- coding: utf-8 -*-

from odoo import models, api

class Sale(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        code = self.env.user.branch_office.sale_sequence.code
        if not code or code == '':
            raise Warning('El usuario actual debe tener relacionada una sucursal y la sucursal una secuencia de ventas.')
        vals['name'] = self.env['ir.sequence'].next_by_code(code)
        return super(Sale, self).create(vals)