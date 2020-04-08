# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    serial_no =  fields.Many2many('stock.production.lot',string='Serial Number')

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(sale_order_line, self)._prepare_invoice_line(qty)
        res.update({'serial_no':self.serial_no.ids})
        return res
