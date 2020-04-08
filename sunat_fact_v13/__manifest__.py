# -*- coding: utf-8 -*-
{
'name': 'Sunat - Emisión electrónica Peruana',
'description': "Addon para enviar documentos a sunat",
'author': "ROCKSCRIPTS",
    'website': "https://instagram.com/rockscripts",
    'summary': "Emisión de documentos contables a Sunat a través de punto de venta, sitio web de comercio y en sección de facturación.",
    'version': '0.1',
    "license": "OPL-1",
    'price':'320',
    'currency':'EUR',
    'support': 'rockscripts@gmail.com',
    'category': 'module_category_account_voucher',
    "images": ["images/banner.png"],
      # any module necessary for this one to work correctly
    'depends': ['base','account','delivery'], 
    # always loaded
    'data': [
                #'security/ir.model.access.csv',
                'views/views.xml',
                'views/templates.xml',
                'views/pe_cpe.xml',
                'views/pe_cpe_guide.xml',
            ],
    'qweb': [
                'static/src/xml/pos_ticket.xml',
                'static/src/xml/pos_screen.xml'
            ],
    # only loaded in demonstration mode
    'demo': [
                'demo/demo.xml',
            ],
    #"external_dependencies": {"python" : ["pytesseract"]},
    'installable': True,
}
