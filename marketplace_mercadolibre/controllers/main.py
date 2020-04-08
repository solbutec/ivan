import json
import logging

import werkzeug

from odoo import _, fields, http, tools
from ..mercadolibre import Meli

_logger = logging.getLogger(__name__)


class MeliController(http.Controller):

    @http.route('/marketplace/meli/<string:db_name>/<int:site_id>/auth_code', auth='none', methods=['GET'])
    def auth_code(self, db_name, site_id, **params):
        if 'code' not in params:
            return http.Response('No se recibio codigo de autorizacion', status=403)
        http.request.session.db = db_name
        env = http.request.env(http.request.cr, tools.SUPERUSER_ID, http.request.env.context)
        site_obj = env['marketplace.site'].search([('id', '=', site_id)])
        if not site_obj:
            return http.Response('site_id invalido.', status=403)
        client = Meli(site_obj.meli_app_id, site_obj.meli_secret_key)
        base_url = env['ir.config_parameter'].get_param('web.base.url')
        client.authorize(params.get('code'), '%s/marketplace/meli/%s/%d/auth_code' % (base_url, db_name, site_id))
        site_obj.write({
            'meli_auth_token': client.access_token,
            'meli_refresh_token': client.refresh_token,
            'meli_expires_in': client.expires_in or 21600
        })
        return werkzeug.utils.redirect('{base_url}/web/#id={site_id}&view_type=form&model=marketplace.site&action={action_id}'.format(**{
            'base_url': base_url,
            'site_id': site_id,
            'action_id': env.ref('marketplace.marketplace_site_action').id
        }))

    @http.route('/marketplace/meli/<string:db_name>/<int:site_id>/notifications', type='json', auth='none', methods=['POST'], csrf=False)
    def notifications(self, db_name, site_id, **kwargs):
        http.request.session.db = db_name
        env = http.request.env(http.request.cr, tools.SUPERUSER_ID, http.request.env.context)
        site_obj = env['marketplace.site'].sudo().search([('id', '=', site_id)])
        if not site_obj:
            return http.Response('site_id invalido.', status=403)
        data = json.loads(http.request.httprequest.data)
        if data.get('topic', '') == 'created_orders':
            client = Meli(site_obj.meli_app_id, site_obj.meli_secret_key, site_obj.meli_auth_token, site_obj.meli_refresh_token)
            if fields.Datetime.now() >= site_obj.meli_expires_in:
                client.get_refresh_token()
                site_obj.write({
                    'meli_auth_token': client.access_token,
                    'meli_refresh_token': client.refresh_token,
                    'meli_expires_in': client.expires_in or 21600
                })
            res = client.get(data.get('resource'), {'access_token': client.access_token}).json()
            repetidos = http.request.env['sale.order'].sudo().search([('ref_mercadolibre', 'ilike', '%d' % res['id'])])
            if repetidos:
                raise ValueError('Ya existe el pedido # %d' % res['id'])
            _logger.info('Referencia ML: %d, existentes: %s', res['id'], repetidos)
            buyer = res['buyer']
            items = res['order_items']
            partner = http.request.env['res.partner'].sudo().search([('phone', 'ilike', buyer['phone']['number'])], limit=1)
            if not partner:
                partner = partner.create({
                    'name': '%s %s' % (buyer['first_name'], buyer['last_name']),
                    'vat': '66.666.666-6',
                    'street': 'ML',
                    'city': 'ML',
                    'customer': True,
                    'email': buyer['email'],
                    'phone': buyer['phone']['number'],
                    'comment': 'Usuario de Mercado Libre: %s' % buyer['nickname']
                })
            order = http.request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'ref_mercadolibre': str(res['id']),
            })
            product_obj = http.request.env['marketplace.product'].sudo()
            lines = []
            for item in items:
                product = product_obj.search([('reference', '=', item['item']['id'])], limit=1)
                lines.append((0, 0, {
                    'product_id': product.product_id.id,
                    'product_qty': item['quantity'],
                    'price_unit': item['unit_price']
                }))
            order.order_line = lines
            order.sudo().message_post(body=_('Presupuesto creado desde Mercado Libre'))
        return {'ok': 'ok'}
