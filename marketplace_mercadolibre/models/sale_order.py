from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ref_mercadolibre = fields.Char('Referencia ML')

    _sql_constraints = [
        ('unique_ref_ml', 'unique(ref_mercadolibre)', 'Ya fue capturada la orden.')
    ]
