from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    marketplace_pricelist_id = fields.Many2one('product.pricelist', related='product_variant_id.marketplace_pricelist_id', readonly=False)
    marketplace_product_ids = fields.One2many('marketplace.product', related='product_variant_id.marketplace_product_ids', readonly=False)
    marketplace_desc = fields.Text(related='product_variant_id.marketplace_desc', readonly=False)
    marketplace_publishment_rule = fields.Selection(related='product_variant_id.marketplace_publishment_rule', readonly=False)
    marketplace_stock_rule = fields.Integer(related='product_variant_id.marketplace_stock_rule', readonly=False)

    @api.multi
    def marketplace_publish_update(self):
        return self.mapped('marketplace_product_ids').update_stock()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    marketplace_pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')
    marketplace_product_ids = fields.One2many('marketplace.product', 'product_id', 'Marketplaces')
    marketplace_desc = fields.Text()
    marketplace_publishment_rule = fields.Selection([
        ('never', 'No publish'),
        ('stock', 'If stock'),
        ('always', 'Always publish')
    ], 'Publishment rule', default='always', help="""Indicates when should products be published:
    - No publish: no matter what, product will not be published.
    - If stock: publishes the product only if there is a minimun stock.
    - Always: publishes the product even if there is no stock.

    If no option is selected, then rule will be based on marketplace rules.
    """)
    marketplace_stock_rule = fields.Integer('Minimun stock', default=1, help='When Publishment rule is "If stock", product '
                                            'will be published based on this minimun amount.')

    @api.multi
    def marketplace_publish_update(self):
        return self.mapped('marketplace_product_ids').update_stock()


class MarketplaceProduct(models.Model):
    _inherit = 'marketplace.product'

    description = fields.Text(related='product_id.marketplace_desc', readonly=False)
