# -*- coding: utf-8 -*-

from odoo import fields, models

class MailTemplate(models.Model):
   
   _inherit = "mail.template"

   body_html = fields.Html('Body', translate=False)