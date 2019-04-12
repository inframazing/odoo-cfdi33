# -*- coding: utf-8 -*-

# This code is part of Odoo/Desiteg project.
# Development by:
# Salvador Daniel Pelayo <salvador.pelayo@desiteg.com>

{
    'name': 'Report Style Background',
    'version': '0.1',
    'description': '''
    Add background image (watermark) to page report.
    ''',
    'category': 'Report',
    'author': 'Salvador Daniel Pelayo Gómez',
    'website': 'http://desiteg.com',
    'depends': [
        'base', 'report', 'web_widget_colorpicker',
    ],
    'external_dependencies': {
        'python': [
            'PIL'
        ]
    },
    'data': [
        'views/report_preview.xml',
        'views/res_company_view.xml'
    ],
    'application': False,
    'installable': True,
}
