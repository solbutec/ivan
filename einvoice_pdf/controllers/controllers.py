# -*- coding: utf-8 -*-
from odoo import http

class einvoice_pdf(http.Controller):

    @http.route('/dianefact/update_context/', methods=['POST'], type='json')
    def update_context(self, **kw):
        uid = http.request.env.context.get('uid')
        