from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.osv import osv

class einvoice_pdf(models.Model):
    _inherit = 'ir.cron'