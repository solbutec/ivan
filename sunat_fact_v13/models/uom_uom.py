from odoo import api, fields, models, _

class Uom(models.Model):
    
    _inherit = 'uom.uom'

    sunat_unit_code = fields.Char(name="sunat_unit_code", default='')

   