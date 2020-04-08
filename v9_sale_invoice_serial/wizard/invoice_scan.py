

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,float_is_zero

class invoice_scan_wizard(models.TransientModel):
    _name = "invoice.scan.wizard"

    scan = fields.Char(string="Scan")


    @api.onchange('scan')
    def add_product_via_scan(self):
        lot_obj = self.env['stock.production.lot']
        if self.scan:
            invoice = self.env['account.invoice'].browse(self._context.get('active_id'))
            lot_ids = lot_obj.search([('name', '=', self.scan)])

            if not lot_ids:
                codes=self.env['stock.production.lot.code'].search([('name', '=', self.scan)])
                if not codes:
                    raise Warning(_(' %s Serial number is not available in system!!') % self.scan)
                else:
                    lot_ids=codes.lot

            line_list = []
            serial_no_list = []
            for lot_id in lot_ids:
                product = lot_id.product_id
                #if not lot_id.product_qty > 0.0 :
                #    raise Warning(_('Stock not available with %s serial/lot number.') % self.scan)
                for line in invoice.invoice_line_ids :
                    serial_no_list.append(line.serial_no.id)

                account = product.property_account_income_id or product.categ_id.property_account_income_categ_id
                if not account:
                    raise Warning(_('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                        (product.name,product.id,product.categ_id.name))
        
                fpos = invoice.fiscal_position_id or invoice.partner_id.property_account_position_id
                if fpos:
                    account = fpos.map_account(account)

                if lot_id.id in serial_no_list :
                    self.scan = ''
                    raise Warning(_('This Serial Number/Lot Is Already In Sale Order Line!!'))
                else :
                    existe = False
                    for order_line in invoice.invoice_line_ids:
                        if order_line.product_id.id == lot_id.product_id.id:
                            order_line.write({'serial_no': [(4, lot_id.id, None)]})
                            existe = True
                    #if lot_id.product_qty  > 0.0 :
                    values = {
                            'name': product and product.display_name or "",
                            'invoice_id':invoice.id,
                            'account_id': account.id or False,
                            'price_unit': product.product_tmpl_id.list_price or 0.0,
                            'quantity': lot_ids[0].product_qty ,
                            'uos_id': product and product.product_tmpl_id and product.product_tmpl_id.uom_id and product.product_tmpl_id.uom_id.id or False,
                            'product_id': product and product.id or False,
                            'invoice_line_tax_id': [(6, 0, product.taxes_id.ids)],
                            'serial_no':[(6, 0, lot_id.ids)],
                        }
                    line_list.append((0, 0, values))
            invoice.write({'invoice_line_ids' : line_list})
            self.scan = False



    