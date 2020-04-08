# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Kiran Kantesariya.
#
##############################################################################
from odoo import api, fields, models, tools, _

class pos_config(models.Model):
    _inherit = 'pos.config' 

    allow_pos_lot = fields.Boolean('Allow POS Lot/Serial Number', default=True)
    lot_expire_days = fields.Integer('Product Lot/Serial expire days.', default=1)
    pos_lot_receipt = fields.Boolean('Print Lot/Serial on receipt',default=1)

class stock_production_lot(models.Model):
    _inherit = "stock.production.lot"

    total_qty = fields.Float("Total Qty", compute="_computeTotalQty")

    @api.multi
    def _computeTotalQty(self):
        for record in self:
            move_line = self.env['stock.move.line'].search([('lot_id','=',record.id)])
            record.total_qty = 0.0
            for rec in move_line:
                if rec.location_dest_id.usage in ['internal', 'transit']:
                    record.total_qty += rec.qty_done
                else:
                    record.total_qty -= rec.qty_done


class PosOrder(models.Model):
    _inherit = "pos.order"

    def set_pack_operation_lot(self, picking=None):
        """Set Serial/Lot number in pack operations to mark the pack operation done."""

        StockProductionLot = self.env['stock.production.lot']
        PosPackOperationLot = self.env['pos.pack.operation.lot']
        has_wrong_lots = False
        for order in self:
            for move in (picking or self.picking_id).move_lines:
                picking_type = (picking or self.picking_id).picking_type_id
                lots_necessary = True
                if picking_type:
                    lots_necessary = picking_type and picking_type.use_existing_lots
                qty = 0
                qty_done = 0
                pack_lots = []
                pos_pack_lots = PosPackOperationLot.search([('order_id', '=', order.id), ('product_id', '=', move.product_id.id)])
                pack_lot_names = [pos_pack.lot_name for pos_pack in pos_pack_lots]
                if pack_lot_names and lots_necessary:
                    for lot_name in list(set(pack_lot_names)):
                        stock_production_lot = StockProductionLot.search([('name', '=', lot_name), ('product_id', '=', move.product_id.id)])
                        if stock_production_lot:
                            if stock_production_lot.product_id.tracking == 'lot':
                                tt = 0
                                for ll in pack_lot_names:
                                    if ll == lot_name:
                                        tt += 1

                                # if a lot nr is set through the frontend it will refer to the full quantity
                                qty = tt
                            else: # serial numbers
                                qty = 1.0
                            qty_done += qty
                            pack_lots.append({'lot_id': stock_production_lot.id, 'qty': qty})
                        else:
                            has_wrong_lots = True
                elif move.product_id.tracking == 'none' or not lots_necessary:
                    qty_done = move.product_uom_qty
                else:
                    has_wrong_lots = True
                for pack_lot in pack_lots:
                    lot_id, qty = pack_lot['lot_id'], pack_lot['qty']
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'qty_done': qty,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'lot_id': lot_id,
                    })
                if not pack_lots:
                    move.quantity_done = qty_done
        return has_wrong_lots


