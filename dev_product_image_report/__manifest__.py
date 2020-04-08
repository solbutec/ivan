# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Devintelle Software Solutions (<http://devintellecs.com>).
#
##############################################################################


{
    'name': 'Print Product Image-ON Sale, Purchase, Invoice Report',
    'version': '12.0.1.0',
    'sequence': 1,
    'category': 'Sales',
    'description': """
         odoo Apps will Print product image on sale order, Purchase order , Invoice report
          odoo Product Image on Sale Order Report
          odoo Product Image on Purchase Order Report
          odoo Product Image on Customer Invoice Report
    """,
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',
    'summary': 'odoo Apps will Print product image on sale order, Purchase order , Invoice report',
    'depends': ['sale','purchase'],
    'data': [
        'report/print_sale_order.xml',
    ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price':10.0,
    'currency':'EUR', 
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

