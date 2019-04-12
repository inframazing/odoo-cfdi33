# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ResCurrency(models.Model):
    _name = "res.currency"

    rate = fields.Float(digits=(12, 16))
    rate_inv = fields.Float(string="Rate Inverse", compute="_compute_rate_inv", store=True, group_operator='avg')

    @api.one
    def _compute_rate_inv(self):
        self.rate_inv = 1 / self.rate if self.rate != 0 else 1


class ResCurrencyRate(models.Model):
    _name = "res.currency.rate"

    rate = fields.Float(digits=(12, 16))
