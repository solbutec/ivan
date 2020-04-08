from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.osv import osv
from odoo.http import request
import xlrd
import os, json

class product_template(models.Model):
    _inherit = 'product.template' 
    sunat_price_type = fields.Selection([('01','Precio unitario (incluye el IGV)'),('02','Valor referencial unitario en operaciones no onerosas')], string='Tipo precio', default='01')
    hs_code = fields.Text(name="hs_code", string="HS Code", default='')
    sunat_product_code = fields.Char(string="Código Producto")