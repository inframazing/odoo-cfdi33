# -*- coding: utf-8 -*-

from odoo import models, fields, api

class BranchOffice(models.Model):
    _name = 'company.branch.office'
    _description = 'Model to store branch offices'

    name = fields.Char('Nombre de la sucursal', required=True, index=True)
    company = fields.Many2one('res.company', string='Compañia Relacionada', required=True)
    partner = fields.Many2one('res.partner', string='Datos de la sucursal', required=True)
    pac_config = fields.Many2one('cfdi.pac.config', string='Datos a utilizar para el timbrado', required=False)
    sale_sequence = fields.Many2one('ir.sequence', 'Secuencia para Ventas', required=True)
    invoice_sequence = fields.Many2one('ir.sequence', 'Secuencia para Facturas', required=True)
    description = fields.Char('Notas de la sucursal o descripción')
    active = fields.Boolean('Activo', default=True)
    warehouse_sales_id = fields.Many2one("stock.warehouse", string="Almacén de Entregas")


class User(models.Model):
    _inherit = 'res.users'

    branch_office = fields.Many2one('company.branch.office', string='Sucursal asignada', required=True)
