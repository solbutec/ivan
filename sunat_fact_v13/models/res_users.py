from odoo import api, fields, models, _

class Users(models.Model):
    
    _inherit = 'res.users'

    @api.multi
    def _is_system(self):
        self.ensure_one()
        return True