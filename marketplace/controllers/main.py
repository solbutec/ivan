import base64
import os

import werkzeug

from odoo import http
from odoo.tools import SUPERUSER_ID
from odoo.addons.web.controllers.main import binary_content


class MarketplaceController(http.Controller):

    def placeholder(self, image='placeholder.png'):
        addons_path = http.addons_manifest['web']['addons_path']
        return open(os.path.join(addons_path, 'web', 'static', 'src', 'img', image), 'rb').read()

    def force_contenttype(self, headers, contenttype='image/png'):
        dictheaders = dict(headers)
        dictheaders['Content-Type'] = contenttype
        return dictheaders.items()

    @http.route('/marketplace/<string:db_name>/product_image/<int:product_id>', auth='none', methods=['GET'])
    def product_image(self, db_name, product_id):
        http.request.session.db = db_name
        env = http.request.env(http.request.cr, SUPERUSER_ID, http.request.env.context)
        status, headers, content = binary_content(model='product.product', id=product_id, field='image', env=env)
        if status == 304:
            return werkzeug.wrappers.Response(status=304, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200:
            return http.request.not_found()

        if content:
            image_base64 = base64.b64decode(content)
        else:
            image_base64 = self.placeholder(image='placeholder.png')
            headers = self.force_contenttype(headers, contenttype='image/png')

        headers.append(('Content-Length', len(image_base64)))
        response = http.request.make_response(image_base64, headers)
        response.status_code = status
        return response

    @http.route('/marketplace/<string:db_name>/extra_image/<int:attachment_id>', auth='none', methods=['GET'])
    def extra_image(self, db_name, attachment_id):
        http.request.session.db = db_name
        env = http.request.env(http.request.cr, SUPERUSER_ID, http.request.env.context)
        status, headers, content = binary_content(model='ir.attachment', id=attachment_id, field='datas', env=env)
        if status == 304:
            return werkzeug.wrappers.Response(status=304, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200:
            return http.request.not_found()

        if content:
            image_base64 = base64.b64decode(content)
        else:
            image_base64 = self.placeholder(image='placeholder.png')
            headers = self.force_contenttype(headers, contenttype='image/png')

        headers.append(('Content-Length', len(image_base64)))
        response = http.request.make_response(image_base64, headers)
        response.status_code = status
        return response
