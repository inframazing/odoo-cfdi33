# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import Warning

class ProductUomCategory(models.Model):
    _inherit = 'product.uom.categ'

    active = fields.Boolean('Activo', default=True)

class ProductUom(models.Model):
    _inherit = 'product.uom'

    sat_code = fields.Char('Código del SAT', required=True)

    @api.multi
    def name_get(self):
        return [(r.id, "[%s] %s" % (r.sat_code, r.name)) for r in self]

    @api.model
    def disable_uom(self):
        unidades = self.search([])
        unidades.write({'active': False})
        categorias = self.env['product.uom.categ'].search([])
        categorias.write({'active': False})
        return True

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|',('name', operator, name),('sat_code', operator, name)] + args, limit=limit)
        return recs.name_get()

class ProductSatCode(models.Model):
    _name = 'product.sat.category'

    type = fields.Selection([('product', 'Producto'), ('service', 'Servicio')], string='Tipo', required=True, default='product')
    name = fields.Char('Nombre (SAT)', required=True,
                       help="Escriba el nombre del producto o servicio, según el catalogo del SAT. Puede usar el nombre de clase.")
    code = fields.Char('Código', required=True)
    active = fields.Boolean('Activo', default=True)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|',('name', operator, name),('code', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.multi
    def name_get(self):
        return [(r.id, "[%s] %s" % (r.code, r.name)) for r in self]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sat_category = fields.Many2one('product.sat.category', string='Clave producto SAT')
    clave_producto = fields.Char(string='Clave producto SAT', related="sat_category.code", store=False)
    clave_unidad = fields.Char(string='Clave unidad SAT', related='uom_id.sat_code', store=False)

    @api.onchange('categ_id')
    def onchange_categ(self):
        if self.categ_id:
            if self.categ_id.sat_category:
                self.sat_category = self.categ_id.sat_category.id

    @api.constrains('clave_producto')
    def valida_clave_producto(self):
        if self.clave_producto == False:
            raise Warning('No ha asignado ninguna clave de productos y servicios del catalogo del sat')

    @api.constrains('clave_unidad')
    def valida_clave_unidad(self):
        if self.clave_unidad == False:
            raise Warning('No ha asignado ninguna clave para la unidad de medida de este producto segun el catalogo del sat')

class ProductCategory(models.Model):
    _inherit = 'product.category'

    sat_category = fields.Many2one('product.sat.category', string='Clave producto SAT')
