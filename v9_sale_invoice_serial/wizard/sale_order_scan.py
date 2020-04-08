# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.



from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,float_is_zero

class sale_order_scan_wizard(models.TransientModel):
    _name = "sale.order.scan"

    scan = fields.Char(string="Scan")

    @api.onchange('scan')
    def add_product_via_scan_wizard(self):
        if self.scan:
            stock_production_lot = self.env['stock.production.lot']
            order = self.env['sale.order'].browse(self._context.get('active_id'))
            stock_p_lots = stock_production_lot.search([('name', '=', self.scan)])
            if not stock_p_lots:
                codes=self.env['stock.production.lot.code'].search([('name', '=', self.scan)])
                if not codes:
                    raise Warning(_(' %s Serial number is not available in system!!') % self.scan)
                else:
                    stock_p_lots=codes.lot
            line_list = []
            serial_no_list = []
            for lot in stock_p_lots:
                if not lot.product_qty > 0.0 :
                    raise Warning(_('Stock not available with %s serial/lot number.') % self.scan)
                for line in order.order_line :
                    serial_no_list.append(line.serial_no.ids)
                if lot.id in serial_no_list :
                    self.scan = ''
                    raise Warning(_('This Serial Number/Lot Is Already In Sale Order Line!!'))
                else :
                    existe=False
                    for order_line in order.order_line:
                        if order_line.product_id.id==lot.product_id.id:
                            order_line.write({'serial_no':[(4, lot.id, None)]})
                            existe=True

                    if lot.product_qty > 0.0 :
                        if existe==False:
                                vals = {
                                    'order_id': order.id,
                                    'product_id': lot.product_id.id,
                                    'name': lot.product_id.name,
                                    'lot_uom_qty': lot.product_qty,
                                    'price_unit': lot.product_id.product_tmpl_id.list_price,
                                    'product_uom': lot.product_id.product_tmpl_id.uom_id.id,
                                    'state': 'draft',
                                    'serial_no':[(6, 0, lot.ids)],
                                    'tax_id': [(6, 0, lot.product_id.taxes_id.ids)],
                                }
                                line_list.append((0, 0 , vals))
            order.write({'order_line' : line_list})
            self.scan = ''
