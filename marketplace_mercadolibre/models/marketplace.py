from datetime import timedelta
import logging
from datetime import datetime, timedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from ..mercadolibre import Meli


_logger = logging.getLogger(__name__)


class MeliCountry(models.Model):
    _name = 'marketplace.meli.country'
    _description = 'Country where MercadoLibre works.'

    name = fields.Char(required=True)
    code = fields.Char(required=True)


class MeliListingType(models.Model):
    _name = 'marketplace.meli.listing.type'
    _description = 'MercadoLibre Listing Types'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)


class MeliCategory(models.Model):
    _name = 'marketplace.meli.category'
    _description = 'MercadoLibre categories'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one('marketplace.meli.category', 'Parent Category')
    child_ids = fields.One2many('marketplace.meli.category', 'parent_id', 'Children Categories')

    @api.multi
    def name_get(self):
        return [(record.id, record.parent_name) for record in self]

    @property
    def parent_name(self):
        if self.parent_id:
            return '%s / %s' % (self.parent_id.parent_name, self.name)
        else:
            return self.name


class MarketplaceSite(models.Model):
    _inherit = 'marketplace.site'

    provider = fields.Selection(selection_add=[('meli', 'Mercado Libre')])
    meli_country = fields.Many2one('marketplace.meli.country')
    meli_app_id = fields.Char('App ID')
    meli_secret_key = fields.Char('Secret Key')
    meli_auth_token = fields.Char('Access Token')
    meli_refresh_token = fields.Char('Refresh Token')
    meli_expires_in = fields.Datetime('Token Expire time')
    meli_currency_id = fields.Char()

    def meli_authenticate(self):
        client = Meli(self.meli_app_id, self.meli_secret_key)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        redirect_uri = '{base_url}/marketplace/meli/{dbname}/{site_id}/auth_code'.format(base_url=base_url, dbname=self.env.cr.dbname, site_id=self.id)
        return {
            'type': 'ir.actions.act_url',
            'url': client.auth_url(redirect_uri),
            'target': 'new'
        }

    @api.multi
    def write(self, vals):
        now = datetime.now()
        if 'meli_expires_in' in vals and isinstance(vals['meli_expires_in'], int):
            now = str(now)
            vals['meli_expires_in'] = datetime.strptime(now, '%Y-%m-%d %H:%M:%S') + timedelta(seconds=vals['meli_expires_in'] - 300)
        if 'meli_auth_token' in vals:
            vals['environment'] = 'prod' if bool(vals['meli_auth_token']) else 'test'
        return super(MarketplaceSite, self).write(vals)

    @api.model
    def meli_cron_update_all(self):
        return self.search([('provider', '=', 'meli'), ('meli_auth_token', '!=', False)]).update_stock()


class MarketplaceProduct(models.Model):
    _inherit = 'marketplace.product'

    meli_listing_type_id = fields.Many2one('marketplace.meli.listing.type', 'Listing type')
    meli_category_id = fields.Many2one('marketplace.meli.category', 'Category')

    @api.multi
    def _meli_publish_product(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for record in self:
            if not record.site_id.meli_auth_token:
                raise ValidationError(_('You can not publish products until you configure access token for MercadoLibre.'))
            if record.publishment_url:
                continue
            client = Meli(record.site_id.meli_app_id, record.site_id.meli_secret_key, record.site_id.meli_auth_token, record.site_id.meli_refresh_token)
            if fields.Datetime.now() >= record.site_id.meli_expires_in:
                client.get_refresh_token()
                record.site_id.write({
                    'meli_auth_token': client.access_token,
                    'meli_refresh_token': client.refresh_token,
                    'meli_expires_in': client.expires_in or 21600
                })
            product_name = record.alternative_name if record.product_name == 'alt' else record.product_id.display_name if record.product_name == 'variant' else record.product_id.name
            data = {
                'title': product_name,
                'category_id': record.meli_category_id.code,
                'price': int(round(record.price)),
                'currency_id': record.site_id.meli_currency_id,
                'available_quantity': record.stock,
                'buying_mode': 'buy_it_now',
                'listing_type_id': record.meli_listing_type_id.code,
                'description': {'plain_text': record.product_id.marketplace_desc or (hasattr(record.product_id, 'website_description') and record.product_id.website_description) or ''},
                'condition': 'new',
                'seller_custom_field': str(record.id),
                'pictures': [
                    {'source': '%s/marketplace/%s/product_image/%d' % (base_url, self.env.cr.dbname, record.product_id.id)}
                ] + [{'source': '%s/marketplace/%s/extra_image/%d' % (base_url, self.env.cr.dbname, extra.id)} for extra in record.attachment_ids]
            }
            res = client.post('/items', data, {'access_token': client.access_token}).json()
            if res.get('error'):
                error_msg = '\n'.join('%s: %s' % (error.get('code'), error.get('message')) if isinstance(error, dict) else error for error in res.get('cause', [])) or res.get('error')
                raise ValidationError(_('Error publishing %s:\n%s') % (record.product_id.name, error_msg))
            record.publishment_url = res.get('permalink')
            record.reference = res.get('id')

    @api.multi
    def _meli_update_stock(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for record in self:
            if not record.site_id.meli_auth_token:
                raise ValidationError(_('You can not update products until you configure access token for MercadoLibre.'))
            if not record.publishment_url:
                record._meli_publish_product()
                continue
            client = Meli(record.site_id.meli_app_id, record.site_id.meli_secret_key, record.site_id.meli_auth_token, record.site_id.meli_refresh_token)
            if fields.Datetime.now() >= record.site_id.meli_expires_in:
                client.get_refresh_token()
                record.site_id.write({
                    'meli_auth_token': client.access_token,
                    'meli_refresh_token': client.refresh_token,
                    'meli_expires_in': client.expires_in or 21600
                })
            product_name = record.alternative_name if record.product_name == 'alt' else record.product_id.display_name if record.product_name == 'variant' else record.product_id.name
            data = {
                'title': product_name,
                'category_id': record.meli_category_id.code,
                'price': int(round(record.price)),
                'available_quantity': record.stock,
                'buying_mode': 'buy_it_now',
                'pictures': [
                    {'source': '%s/marketplace/product_image/%d' % (base_url, record.product_id.id)}
                ] + [{'source': '%s/marketplace/%s/extra_image/%d' % (base_url, self.env.cr.dbname, extra.id)} for extra in record.attachment_ids]
            }
            res = client.put('/items/%s' % record.reference, data, {'access_token': client.access_token}).json()
            if res.get('error'):
                error_msg = '\n'.join('%s: %s' % (error.get('code'), error.get('message')) for error in res.get('cause', [])) or res.get('error')
                raise ValidationError(_('Error updating %s:\n%s') % (record.product_id.name, error_msg))

            website_description = record.product_id.website_description if hasattr(record.product_id, 'website_description') else ''
            if record.product_id.marketplace_desc or website_description:
                res = client.get('/items/%s/description' % record.reference, {}, {'access_token': client.access_token}).json()
                if res.get('plain_text') in [record.product_id.marketplace_desc, website_description or '']:
                    continue
                res = client.put('/items/%s/description' % record.reference, {'plain_text': record.product_id.marketplace_desc or website_description or ''}, {'access_token': client.access_token}).json()
                if res.get('error'):
                    error_msg = '\n'.join('%s: %s' % (error.get('code'), error.get('message')) for error in res.get('cause', [])) or res.get('error')
                    raise ValidationError(_('Error updating description for %s:\n%s') % (record.product_id.name, error_msg))

    @api.multi
    def _meli_withdraw(self):
        for record in self:
            if not record.publishment_url or not record.reference:
                continue
            client = Meli(record.site_id.meli_app_id, record.site_id.meli_secret_key, record.site_id.meli_auth_token, record.site_id.meli_refresh_token)
            try:
                res = client.put('/items/%s' % record.reference, {'status': 'closed'}, {'access_token': client.access_token}).json()
                if res.get('error'):
                    _logger.error('Product with reference %s was not closed, do it manually on MercadoLibre site\n%s', record.reference, res.get('error'))
            except:
                _logger.error('Product with reference %s was not closed, do it manually on MercadoLibre site', record.reference)
            try:
                res = client.put('/items/%s' % record.reference, {'deleted': 'true'}, {'access_token': client.access_token}).json()
                if res.get('error'):
                    _logger.error('Product with reference %s was not deleted, do it manually on MercadoLibre site\n%s', record.reference, res.get('error'))
            except:
                _logger.error('Product with reference %s was not deleted, do it manually on MercadoLibre site', record.reference)
