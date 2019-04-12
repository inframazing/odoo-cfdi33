# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo import tools
from odoo.exceptions import Warning

import logging

from PIL import Image
from io import BytesIO
import base64
import math

_paper_sizes = {
    'A0': [841, 1189],
    'A1': [594, 841],
    'A2': [420, 594],
    'A3': [297, 420],
    'A4': [210, 297],
    'A5': [148, 210],
    'A6': [105, 148],
    'A7': [74, 105],
    'A8': [52, 74],
    'A9': [37, 57],
    'B0': [1000, 1414],
    'B1': [707, 1000],
    'B2': [500, 707],
    'B3': [353, 500],
    'B4': [250, 353],
    'B5': [176, 250],
    'B6': [125, 176],
    'B7': [88, 125],
    'B8': [62, 88],
    'B9': [33, 62],
    'B10': [31, 44],
    'C5E': [163, 229],
    'Comm10E': [105, 241],
    'DLE': [110, 220],
    'Executive': [190.5, 254],
    'Folio': [210, 330],
    'Ledger': [431.8, 279.4],
    'Legal': [215.9, 355.6],
    'Letter': [215.9, 279.4],
    'Tabloid': [279.4, 431.8]
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    color_primary = fields.Char("Color primario", default="rgba(24,85,132,1)")
    color_secondary = fields.Char("Color secundario", default="rgba(124,185,232,1)")
    color_title = fields.Char("Color titulos", default="rgba(100,126,142,1)")
    color_text = fields.Char("Color de texto", default="rgba(20,26,32,1)")
    color_highlight = fields.Char("Color de resaltado", default="rgba(108,151,226,1)")
    color_important = fields.Char("Color datos importantes", default="rgba(251,96,127,1)")
    opacity = fields.Float("Transparencia", default="0.8", help="Ponga un número entre 0 y 1 que determina que tan transparente lucira su logo en el fondo de la página.")
    paper = fields.Many2one('report.paperformat', string='Formato de papel')
    paper_landscape = fields.Many2one('report.paperformat', string='Formato de papel Horizontal')
    background_image = fields.Binary("Imagen para fondo de página")
    background = fields.Binary("Computed image", compute='_gen_background', store=True)
    background_landscape = fields.Binary("Computed image", compute='_gen_background_landscape', store=True)
    x = fields.Integer('x')
    y = fields.Integer('y')
    x_l = fields.Integer('x_l')
    y_l = fields.Integer('y_l')


    @api.constrains('opacity')
    def check_opacity(self):
        if self.opacity < 0 or self.opacity > 1:
            raise Warning("El valor de opacidad debe ser fijado entre 0 y 1.")

    @api.onchange('opacity')
    def onchange_opacity(self):
        self.background_image = None
        self.background = None
        self.background_landscape = None

    @api.onchange('paper', 'paper_landscape')
    def onchange_paper(self):
        self.background_image = None
        self.background = None

    @api.depends('background_image', 'opacity', 'paper')
    def _gen_background(self):
        for rec in self:
            if not rec.paper or not rec.background_image or rec.opacity < 0 or rec.opacity > 1:
                rec.background = None
                return
            if rec.paper.format in _paper_sizes:
                size_x = _paper_sizes[rec.paper.format][0]
                size_y = _paper_sizes[rec.paper.format][1]
            else:
                size_x = rec.paper.page_width
                size_y = rec.paper.page_height
            if rec.paper.orientation == 'Landscape':
                aux = size_x
                size_x = size_y
                size_y = aux
            top = rec.paper.margin_top
            bottom = rec.paper.margin_bottom
            right = rec.paper.margin_right
            left = rec.paper.margin_left
            px = rec.paper.dpi * 1.251647 / 25.4
            x = int((size_x - right - left) * px)
            y = int((size_y - top - bottom) * px)
            extra = int((top + bottom) * px)
            # Ajustar tamaño de imagen agregando espacio en blanco
            img_r = tools.image_resize_image(rec.background_image, (x, y+2*extra))
            # Cambiar imagen b64 a PIL
            imgt = Image.open(BytesIO(base64.b64decode(img_r)))
            imgt = imgt.crop((0, extra, x, y + extra))
            imgt = imgt.convert("RGBA")
            alpha = Image.new("RGBA", imgt.size, (255, 255, 255, int(255*rec.opacity)))
            inter = Image.alpha_composite(imgt, alpha)
            alpha.putalpha(255)
            result = Image.alpha_composite(alpha, inter)
            buffered = BytesIO()
            result.save(buffered, format="PNG")
            rec.background = base64.b64encode(buffered.getvalue())
            rec.x = x
            rec.y = y

    @api.depends('background_image', 'opacity', 'paper_landscape')
    def _gen_background_landscape(self):
        for rec in self:
            if not rec.paper_landscape or not rec.background_image or rec.opacity < 0 or rec.opacity > 1:
                rec.background_landscape = None
                return
            if rec.paper_landscape.format in _paper_sizes:
                size_x = _paper_sizes[rec.paper_landscape.format][0]
                size_y = _paper_sizes[rec.paper_landscape.format][1]
            else:
                size_x = rec.paper_landscape.page_width
                size_y = rec.paper_landscape.page_height
            if rec.paper_landscape.orientation == 'Landscape':
                aux = size_x
                size_x = size_y
                size_y = aux
            top = rec.paper_landscape.margin_top
            bottom = rec.paper_landscape.margin_bottom
            right = rec.paper_landscape.margin_right
            left = rec.paper_landscape.margin_left
            px = rec.paper_landscape.dpi * 1.251647 / 25.4
            x = int((size_x - right - left) * px)
            y = int((size_y - top - bottom) * px)
            extra = int((top + bottom) * px)
            # Ajustar tamaño de imagen agregando espacio en blanco
            img_r = tools.image_resize_image(rec.background_image, (x, y+2*extra))
            # Cambiar imagen b64 a PIL
            imgt = Image.open(BytesIO(base64.b64decode(img_r)))
            imgt = imgt.crop((0, extra, x, y + extra))
            imgt = imgt.convert("RGBA")
            alpha = Image.new("RGBA", imgt.size, (255, 255, 255, int(255*rec.opacity)))
            inter = Image.alpha_composite(imgt, alpha)
            alpha.putalpha(255)
            result = Image.alpha_composite(alpha, inter)
            buffered = BytesIO()
            result.save(buffered, format="PNG")
            rec.background_landscape = base64.b64encode(buffered.getvalue())
            rec.x_l = x
            rec.y_l = y
