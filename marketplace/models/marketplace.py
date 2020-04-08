from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.image import image_resize_image_small


class MarketplaceProduct(models.Model):
    _name = 'marketplace.product'
    _description = 'Details of product in a Marketplace'
    _rec_name = 'product_id'

    @api.model
    def default_get(self, d_fields):
        res = super(MarketplaceProduct, self).default_get(d_fields)
        if 'default_provider' in self.env.context:
            providers = self.env['marketplace.site'].search([('provider', '=', self.env.context['default_provider'])])
            if providers:
                res['site_id'] = providers[0].id
        return res

    product_id = fields.Many2one('product.product', 'Product', required=True)
    site_id = fields.Many2one('marketplace.site', 'Site', required=True)
    provider = fields.Selection(related='site_id.provider')
    published = fields.Boolean(compute='_compute_published')
    reference = fields.Char()
    publishment_url = fields.Char()
    stock = fields.Float(compute='_compute_stock')
    price = fields.Float(compute='_compute_price')
    product_name = fields.Selection([
        ('template', 'Parent / Template'),
        ('variant', 'Variant'),
        ('alt', 'Other')
    ], required=True, default='template')
    alternative_name = fields.Char()
    attachment_ids = fields.Many2many('ir.attachment', string='Extra images')

    _sql_constraints = [
        ('unique_product_site', 'unique(product_id, site_id)', 'This product is already published on this site')
    ]

    @api.onchange('product_name')
    def _onchange_product_name(self):
        if self.product_name == 'alt' and not self.alternative_name:
            self.alternative_name = self.product_id.name

    @api.depends('publishment_url')
    def _compute_published(self):
        for record in self:
            record.published = bool(record.publishment_url)

    @api.depends('product_id')
    def _compute_stock(self):
        for record in self:
            record.stock = record.product_id.virtual_available if record.product_id.type == 'product' else 10

    @api.depends('product_id', 'site_id')
    def _compute_price(self):
        for record in self:
            if not record.product_id:
                record.price = 0
                continue
            if self.env.user.has_group('product.group_sale_pricelist') and (record.product_id.marketplace_pricelist_id or record.site_id.pricelist_id):
                price = (record.product_id.marketplace_pricelist_id or record.site_id.pricelist_id).get_product_price(record.product_id, 1, False)
            else:
                price = record.product_id.lst_price
            if record.site_id.fee_type == 'amount':
                record.price = price + record.site_id.fee_amount
            elif record.site_id.fee_type == 'percent':
                record.price = price * (1 + record.site_id.fee_amount / 100.0)
            else:
                record.price = price

    @api.multi
    def publish(self):
        for record in self:
            if not record.check_publishment_rule:
                continue
            if hasattr(record, '_%s_publish_product' % record.site_id.provider):
                getattr(record, '_%s_publish_product' % record.site_id.provider)()
            else:
                raise ValidationError(_('Not implemented for %s provider.') % record.site_id.provider)
        return True

    @api.multi
    def update_stock(self):
        for record in self:
            if not record.check_publishment_rule:
                continue
            if hasattr(record, '_%s_update_stock' % record.site_id.provider):
                getattr(record, '_%s_update_stock' % record.site_id.provider)()
            else:
                raise ValidationError(_('Not implemented for %s provider.') % record.site_id.provider)
        return True

    @api.multi
    def withdraw(self):
        for record in self:
            if hasattr(record, '_%s_withdraw' % record.site_id.provider):
                getattr(record, '_%s_withdraw' % record.site_id.provider)()
            else:
                raise ValidationError(_('Not implemented for %s provider.') % record.site_id.provider)
            self.write({
                'reference': False,
                'publishment_url': False
            })
        return True

    @property
    def check_publishment_rule(self):
        if self.product_id.marketplace_publishment_rule == 'always':
            return True
        elif self.product_id.marketplace_publishment_rule == 'never':
            return False
        elif self.product_id.marketplace_publishment_rule == 'stock':
            return self.stock >= self.product_id.marketplace_stock_rule
        elif self.site_id.publishment_rule == 'always':
            return True
        elif self.site_id.publishment_rule == 'never':
            return False
        elif self.site_id.publishment_rule == 'stock':
            return self.stock >= self.site_id.minimun_stock_rule
        else:
            return False

    @api.multi
    def unlink(self):
        try:
            self.withdraw()
        except ValidationError:
            pass
        return super(MarketplaceProduct, self).unlink()


class MarketplaceSite(models.Model):
    _name = 'marketplace.site'
    _description = 'Marketplace site'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, copy=False)
    image = fields.Binary(attachment=True, copy=False)
    provider = fields.Selection([('manual', 'Manual configuration')], required=True, default='manual')
    active = fields.Boolean(default=True)
    environment = fields.Selection([('test', 'test'), ('prod', 'Production')], default='test', required=True)
    marketplace_product_ids = fields.One2many('marketplace.product', 'site_id', 'Products')
    publishment_rule = fields.Selection([
        ('never', 'No publish'),
        ('stock', 'If stock'),
        ('always', 'Always publish')
    ], default='always', required=True, help="""
    Indicates when should products be published:
    - No publish: no matter what, product will not be published.
    - If stock: publishes the product only if there is a minimun stock.
    - Always: publishes the product even if there is no stock.
    """)
    minimun_stock_rule = fields.Integer(default=1, help='When Publishment rule is "If stock", product '
                                        'will be published based on this minimun amount.')

    fee_type = fields.Selection([('percent', 'Percent'), ('amount', 'Amount')])
    fee_amount = fields.Float()
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')

    @api.multi
    def publish(self):
        return self.mapped('marketplace_product_ids').publish()

    @api.multi
    def update_stock(self):
        return self.mapped('marketplace_product_ids').update_stock()

    @api.multi
    def withdraw(self):
        return self.mapped('marketplace_product_ids').withdraw()

    @api.model
    def create(self, vals):
        if 'image' in vals:
            vals['image'] = image_resize_image_small(vals['image'])
        return super(MarketplaceSite, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'image' in vals:
            vals['image'] = image_resize_image_small(vals['image'])
        return super(MarketplaceSite, self).write(vals)
