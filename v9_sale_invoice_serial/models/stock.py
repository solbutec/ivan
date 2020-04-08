# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,float_is_zero


class stock_move(models.Model):
    _inherit = "stock.move"

    serial_no =  fields.Many2one('stock.production.lot',string='Serial Number')        

class StockRule(models.Model):
    _inherit = 'stock.rule'
    
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        result = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, values, group_id)
        sale_line_id = values.get('sale_line_id')
        serial_number = False
        if sale_line_id:
            serial_number = self.env['sale.order.line'].browse(sale_line_id).serial_no.id
            result.update({
                'serial_no':serial_number or False,
            })

        return result





class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    code = fields.One2many('stock.production.lot.code','lot',string='Codigos alternativos')

class ProductionLotCode(models.Model):
    _name = 'stock.production.lot.code'

    name=fields.Char(string="Codigo",required=True)
    lot = fields.Many2one('stock.production.lot', string='lot')

    _sql_constraints = [
        ('name_uniq_code_lote', 'unique (name)', 'El codigo ya existe!'),
    ]
