# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import Warning


class FormaPago(models.Model):
    _name = 'sat.forma.pago'

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', required=True)
    active = fields.Boolean('Activo', default=True)

    @api.multi
    def name_get(self):
        return [(r.id, "%s - %s" % (r.code, r.name)) for r in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|',('name', operator, name),('code', operator, name)] + args, limit=limit)
        return recs.name_get()


class MetodoPago(models.Model):
    _name = 'sat.metodo.pago'

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', required=True)
    active = fields.Boolean('Activo', default=True)

    @api.multi
    def name_get(self):
        return [(r.id, "%s - %s" % (r.code, r.name)) for r in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|',('name', operator, name),('code', operator, name)] + args, limit=limit)
        return recs.name_get()

class UsoCFDI(models.Model):
    _name = 'sat.uso.cfdi'

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', required=True)
    active = fields.Boolean('Activo', default=True)

    @api.multi
    def name_get(self):
        return [(r.id, "%s - %s" % (r.code, r.name)) for r in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|',('name', operator, name),('code', operator, name)] + args, limit=limit)
        return recs.name_get()

class TipoRelacion(models.Model):
    _name = 'sat.tipo.relacion'

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', required=True)
    active = fields.Boolean('Activo', default=True)

    @api.multi
    def name_get(self):
        return [(r.id, "%s - %s" % (r.code, r.name)) for r in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search(['|',('name', operator, name),('code', operator, name)] + args, limit=limit)
        return recs.name_get()