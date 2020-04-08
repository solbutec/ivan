# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from sunatservice.sunatservice import Service
import json

class AccountInvoiceRefund(models.TransientModel):
    """Credit Notes"""

    _name = "account.invoice.refund"
    _description = "Notas"
    
    @api.model
    def _get_reason(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.name
        return ''

    date_invoice = fields.Date(string='Fecha de la nota', default=fields.Date.context_today, required=True)
    date = fields.Date(string='Fecha Contable')
    description = fields.Char(string='Motivo', required=True, default=_get_reason)
    refund_only = fields.Boolean(string='Technical field to hide filter_refund in case invoice is partially paid', compute='_get_refund_only')
    filter_refund = fields.Selection([('refund', 'Create a draft credit note'), ('cancel', 'Cancel: create credit note and reconcile'), ('modify', 'Modify: create credit note, reconcile and create a new draft invoice')],
    #filter_refund = fields.Selection([('refund', 'Crear nota para validar')],
        default='refund', string='Method', required=True, help='Elige cómo quieres acreditar o debitar esta factura. No puede modificar y cancelar si la factura ya está conciliada')
    sunat_note = fields.Selection([('07','Crédito'),('08','Débito')], string='Nota', default='07')
    CD_VALUES = [('01','Anulación operación'),('02','Anulacion error RUC'),('03','Corrección en descripción'),('04','Descuento global'),('05','Descuento por Item'),('06','Descuento Total'),('07','Devolución por Item'),('08','Bonificación'),('09','Disminución en valor'),('10','Otros conceptos')]
    credit_discrepance = fields.Selection(CD_VALUES, string='Discrepancia', default='01')
    DB_VALUES = [('01','Intereses de mora'),('02','Aumento en el valor'),('03','Penalidades / otros conceptos')]
    debit_discrepance = fields.Selection(DB_VALUES, string='Discrepancia', default='01')
    #add_credit = fields.Boolean()
    #@api.onchange('sunat_note')
    #def on_change_sunat_note(self):
    #    if(self.sunat_note=='07'):
    #        self.credit_discrepance.hide = False
    #        self.debit_discrepance.hide = True
    #    else:
    #        self.credit_discrepance.hide = True
    #        self.debit_discrepance.hide = False
            
    @api.depends('date_invoice')
    @api.one
    def _get_refund_only(self):
        invoice_id = self.env['account.invoice'].browse(self._context.get('active_id',False))
        if len(invoice_id.payment_move_line_ids) != 0 and invoice_id.state != 'paid':
            self.refund_only = True
        else:
            self.refund_only = False


    @api.multi
    def compute_refund(self, mode='refund'):

        inv_obj = self.env['account.invoice']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        sequence_obj = self.env['ir.sequence']
        journal_obj = self.env['account.journal']
        context = dict(self._context or {})
        
              
        xml_id = False
        new_note_id = 0

        for form in self:
            created_inv = []
            date = False
            description = False
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'cancel']:
                    raise UserError(_('Cannot create credit note for the draft/cancelled invoice.'))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise UserError(_('Cannot create a credit note for the invoice which is already reconciled, invoice should be unreconciled first, then only you can add credit note for this invoice.'))

                date = form.date or False
                description = form.description or inv.name
                refund = inv.refund(form.date_invoice, date, description, inv.journal_id.id)
                new_note_id = refund.id
                created_inv.append(refund.id)
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_ids
                    to_reconcile_ids = {}
                    to_reconcile_lines = self.env['account.move.line']
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_lines += line
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    refund.action_invoice_open()
                    for tmpline in refund.move_id.line_ids:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_lines += tmpline
                    to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    if mode == 'modify':
                        invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                        invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                        tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': form.date_invoice,
                            'state': 'draft',
                            'number': False,
                            'invoice_line_ids': invoice_lines,
                            'tax_line_ids': tax_lines,
                            'date': date,
                            'origin': inv.origin,
                            'fiscal_position_id': inv.fiscal_position_id.id
                        })
                        for field in inv_obj._get_refund_common_fields():
                            if inv_obj._fields[field].type == 'many2one':
                                invoice[field] = invoice[field] and invoice[field][0]
                            else:
                                invoice[field] = invoice[field] or False
                        inv_refund = inv_obj.create(invoice)
                        body = _('Correction of <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a><br>Reason: %s') % (inv.id, inv.number, description)
                        inv_refund.message_post(body=body)
                        if inv_refund.payment_term_id.id:
                            inv_refund._onchange_payment_term_date_invoice()
                        created_inv.append(inv_refund.id)
                xml_id = inv.type == 'out_invoice' and 'action_invoice_out_refund' or \
                         inv.type == 'out_refund' and 'action_invoice_tree1' or \
                         inv.type == 'in_invoice' and 'action_invoice_in_refund' or \
                         inv.type == 'in_refund' and 'action_invoice_tree2'
        if xml_id:
            result = self.env.ref('account.%s' % (xml_id)).read()[0]
            if mode == 'modify':
                # When refund method is `modify` then it will directly open the new draft bill/invoice in form view
                if inv_refund.type == 'in_invoice':
                    view_ref = self.env.ref('account.invoice_supplier_form')
                else:
                    view_ref = self.env.ref('account.invoice_form')
                result['views'] = [(view_ref.id, 'form')]
                result['res_id'] = inv_refund.id
            else:

                invoiceNote = self.env['account.invoice'].browse(int(new_note_id)) 
                
                
                if(self.sunat_note=="07"):
                   journal = journal_obj.search([('code','=',str("NCR"))])
                   journal_credit_sequence_obj = sequence_obj.search([('code','=',str("NCR"))], limit=1)
                   sequence_credit = sequence_obj.next_by_code(str("NCR"))
                   discrepance_text = ''
                   for selection in self.CD_VALUES:
                       if(self.credit_discrepance == selection[0]):
                          discrepance_text = selection[1]
                       
                   invoiceNote.update({"number":str(sequence_credit),"journal_id":int(journal.id),"discrepance_code":str(self.credit_discrepance),"discrepance_text":str(discrepance_text),"type":"out_refund"})
                   journal_credit_sequence_obj.update({'number_next_actual':int(journal_credit_sequence_obj.number_next_actual)-1})
                
                if(self.sunat_note=="08"):

                   result['id'] = "210"
                   result['xml_id'] = 'account.action_invoice_out_invoice'
                   result['display_name'] = 'Notas de Débito'
                   #result['domain'].append(('type', '=', 'out_invoice'))
                   #raise Warning(result)
                   journal = journal_obj.search([('code','=',str("NDB"))])
                   sequence_debit = sequence_obj.next_by_code(str("NDB"))
                   journal_debit_sequence_obj = sequence_obj.search([('code','=',str("NDB"))], limit=1)
                   discrepance_text = ''
                   for selection in self.DB_VALUES:
                       if(self.debit_discrepance == selection[0]):
                          discrepance_text = selection[1]
                   invoiceNote.update({"number":str(sequence_debit),"journal_id":int(journal.id),"discrepance_code":str(self.debit_discrepance),"discrepance_text":str(discrepance_text),"type":"out_invoice"})
                   journal_debit_sequence_obj.update({'number_next_actual':int(journal_debit_sequence_obj.number_next_actual)-1})

                invoice_domain = safe_eval(result['domain'])

                if(self.sunat_note=="08"):
                   invoice_domain = []
                   invoice_domain.append(('type', '=', 'out_invoice'))

                invoice_domain.append(('id', 'in', created_inv))
                result['domain'] = invoice_domain
                #raise Warning(result)
            return result
        return True

    @api.multi
    def invoice_refund(self):
        data_refund = self.read(['filter_refund'])[0]['filter_refund']
        return self.compute_refund(data_refund)
        inv_obj = self.env['account.invoice']
        context = dict(self._context or {})
        data_refund = self.read(['filter_refund'])[0]['filter_refund']
        for form in self:
            for inv in inv_obj.browse(context.get('active_ids')):
                eDocumentType = inv.journal_id.code
                if(eDocumentType!="FAC" or eDocumentType!="INV" or eDocumentType!="NCR" or eDocumentType!="NDB"): 
                    data_refund = self.read(['filter_refund'])[0]['filter_refund']
                    return self.super_compute_refund(data_refund)
                else:
                    return self.compute_refund(data_refund)

        

    

    @api.multi
    def super_compute_refund(self, mode='refund'):
        inv_obj = self.env['account.invoice']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        context = dict(self._context or {})
        xml_id = False

        for form in self:
            created_inv = []
            date = False
            description = False
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'cancel']:
                    raise UserError(_('Cannot create credit note for the draft/cancelled invoice.'))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise UserError(_('Cannot create a credit note for the invoice which is already reconciled, invoice should be unreconciled first, then only you can add credit note for this invoice.'))

                date = form.date or False
                description = form.description or inv.name
                refund = inv.refund(form.date_invoice, date, description, inv.journal_id.id)
                
                created_inv.append(refund.id)
                
                if mode in ('cancel', 'modify'):
                    
                    movelines = inv.move_id.line_ids
                    to_reconcile_ids = {}
                    to_reconcile_lines = self.env['account.move.line']
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_lines += line
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    refund.action_invoice_open()
                    for tmpline in refund.move_id.line_ids:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_lines += tmpline
                    to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    if mode == 'modify':
                        invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                        invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                        tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': form.date_invoice,
                            'state': 'draft',
                            'number': False,
                            'invoice_line_ids': invoice_lines,
                            'tax_line_ids': tax_lines,
                            'date': date,
                            'origin': inv.origin,
                            'fiscal_position_id': inv.fiscal_position_id.id,
                        })
                        for field in inv_obj._get_refund_common_fields():
                            if inv_obj._fields[field].type == 'many2one':
                                invoice[field] = invoice[field] and invoice[field][0]
                            else:
                                invoice[field] = invoice[field] or False
                        inv_refund = inv_obj.create(invoice)
                        if inv_refund.payment_term_id.id:
                            inv_refund._onchange_payment_term_date_invoice()
                        created_inv.append(inv_refund.id)
                xml_id = inv.type == 'out_invoice' and 'action_invoice_out_refund' or \
                         inv.type == 'out_refund' and 'action_invoice_tree1' or \
                         inv.type == 'in_invoice' and 'action_invoice_in_refund' or \
                         inv.type == 'in_refund' and 'action_invoice_tree2'
                # Put the reason in the chatter
                subject = _("Credit Note")
                body = description
                refund.message_post(body=body, subject=subject)
        if xml_id:
            result = self.env.ref('account.%s' % (xml_id)).read()[0]
            invoice_domain = safe_eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result
        return True