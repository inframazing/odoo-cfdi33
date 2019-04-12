# -*- coding: utf-8 -*-

{
    'name': 'CFDI 3.3',
    'version': '0.2',
    'description': '''
    Factura Electronica para Mexico (CFDI 3.3)
    
    Debido a la encriptación que se utiliza para la facturación se necesitan los siguientes paquetes:
        * openssl
        * python-openssl
    
    Los puede instalar con los siguientes comandos:
        * apt-get install openssl
        * apt-get install python-openssl
    ''',
    'category': 'Accounting',
    'author': 'Desiteg SCRUM Team',
    'website': 'http://desiteg.com',
    'depends': [
        'base', 'sale', 'account', 'account_cancel', 'account_accountant', 'base_vat', 'report_style_background', 'stock'
    ],
    'external_dependencies': {
        'python': [
            'OpenSSL',
            'pyqrcode',
            'png',
        ],
        'bin': [
            'openssl'
        ],
    },
    'data': [
        'data/sat_forma_pago_data.xml',
        'data/sat_metodo_pago_data.xml',
        'data/sat_tipo_relacion_data.xml',
        'data/sat_uso_cfdi_data.xml',
        'data/sat_catalogo_productos_data.xml',
        'data/sat_catalogo_unidades_data.xml',
        'data/company_branch_office_data.xml',
        'data/default_res_partner.xml',
        'report/payment_report.xml',
        'report/invoice_report.xml',
        'data/mail_template_payment_data.xml',
        'data/mail_template_invoice_data.xml',
        'data/cron_consultar_status_cfdi.xml',
        'views/sat_catalogo_view.xml',
        'views/pac_config_view.xml',
        'views/company_branch_office_view.xml',
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
        'views/product_view.xml',
        'views/cfdi_menu.xml',
        'views/account_tax_view.xml',
        'views/account_invoice_view.xml',
        'views/account_payment_view.xml',
        'security/ir.model.access.csv',
        'security/account.invoice.xml',
        'wizard/wizard_download_invoice.xml',
        #'wizard/wizard_global_invoice.xml'
    ],
    'application': True,
    'installable': True,
}
