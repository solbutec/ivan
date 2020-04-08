# -*- coding: utf-8 -*-
{
    'name': 'eDocs Print Format',
    'description': "Addon mejorar plantillas de documentos contables",
    'author': "ROCKSCRIPTS",
    'website': "https://instagram.com/rockscripts",
    'summary': "Formato para documentos contables",
    'version': '0.1',
    "license": "OPL-1",
    'price':'40',
    'currency':'USD',
    'support': 'rockscripts@gmail.com',
    'category': 'module_category_account_voucher',
    "images": ["images/banner.png"],
        # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
             'views/templates.xml',
             'views/template_invoice.xml',
  	     'views/template_quote.xml',
             'views/report_deliveryslip.xml',
            ],
    'qweb': [
                'static/src/xml/pos.xml'
            ],
    #"external_dependencies": {"python" : ["pytesseract"]},
    'installable': True,
}
