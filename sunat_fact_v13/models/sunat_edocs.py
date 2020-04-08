# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import Warning
from odoo.http import request
import os
import base64
import random
import json
from datetime import datetime

from sunatservice.sunatservice import Service

class SunatEdocs(models.Model):
    _name = 'sunat.edocs'
    _description = "Comprobantes eléctronicos"
    _table = 'account_invoice'
    number = fields.Char(string='Documento', readonly=True)
    date_invoice = fields.Date(string='Creado en', readonly=True)
    qr_image = fields.Text(name="qr_image", default='')

    unsigned_document = fields.Binary(string="XML - No firmado", default=None, readonly=True, filename="unsigned_document_filename" ,filters='*.xml', type="xml")
    unsigned_document_filename = fields.Char(string="Unsigned Filename", invisible="1", default="unsigned.XML")

    signed_document = fields.Binary(string="XML - Firmado", default=None, readonly=True, filename="signed_document_filename" ,filters='*.xml', type="xml")
    signed_document_filename = fields.Char(string="Signed Filename", invisible="1", default="signed.XML")
    
    response_document = fields.Binary(string="XML - Respuesta", default=None, readonly=True, filename="response_document_filename",filters='*.xml', type="xml")
    response_document_filename = fields.Char(string="Response Filename", invisible="1", default="response.XML")

    api_message = fields.Text(name="api_message", string="Estado", default='Documento contable sin emitir.', readonly=True)

    sunat_request_status = fields.Text(string="Estado Emisión", name="sunat_request_status", default='No Emitido')
    sunat_request_type = fields.Text(string="Método", name="sunat_request_type", default='Automatizada')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'edocs')
        self._cr.execute(
                         """
                            CREATE VIEW edocs AS 
                            ( 
                              SELECT number as number, 
                                     create_date as create_date,   
                                     unsigned_document as unsigned_document,
                                     signed_document as signed_document, 
                                     response_document as response_document,
                                     qr_image as qr_image,
                                     api_message as api_message,
                                     sunat_request_type as sunat_request_type
                              FROM account_invoice 
                              WHERE account_invoice.state = 'open' and account_invoice.signed_document!='' and account_invoice.number!=''
                              
                            )                        
                         """
                        )
    
    #Automated task for submit failed or unsubmited invoices 
    def edocs_submit_invoices(self, **kw):

        query = "select nextcall from ir_cron where cron_name = '"+str("sunat_edocs")+"'"
        request.cr.execute(query)
        cron_job_edocs = request.cr.dictfetchone()
        nextcall_datetime = str(cron_job_edocs["nextcall"]).split(" ")
        invoice_date_limit = nextcall_datetime[0]
        
        query = "select id, number, company_id, unsigned_document, signed_document, response_document from account_invoice where date_invoice <= '"+str(invoice_date_limit)+"' and (sunat_request_status = '"+str("FAIL")+"' or sunat_request_status = '"+str("No Emitido")+"' or sunat_request_status = '"+str("not_requested")+"')"
        request.cr.execute(query)
        invoices_unsubmited = request.cr.dictfetchall()
        
        for invoice_unsubmited in invoices_unsubmited:
            query = "select res_partner.vat, res_company.api_mode, res_company.sol_ruc, res_company.sol_username, res_company.sol_password, res_company.certs from res_company left join res_partner on res_partner.company_id = res_company.id where res_company.id = "+str(invoice_unsubmited['company_id'])+" and res_partner.is_company = TRUE and res_company.partner_id = res_partner.id"
            request.cr.execute(query)
            company_fields = request.cr.dictfetchone()

            if(invoice_unsubmited["number"]):
                
                
                serieParts = str(invoice_unsubmited["number"]).split("-")  
                serieConsecutivoString = serieParts[0]
                serieConsecutivo = serieParts[1]                
                
                sunat_data = {
                                "secuencia_consecutivo":serieConsecutivo,
                                "numero":serieConsecutivo, # cdr
                                "serie":serieConsecutivoString,
                                "sunat_sol": {
                                                "ruc":company_fields["sol_ruc"],
                                                'usuario':company_fields["sol_username"],
                                                'clave':company_fields["sol_password"]
                                             },
                                "xml":  {
                                            #"signed":base64.b64decode((invoice_fields["signed_document"]))
                                        },
                                "licencia": "081OHTGAVHJZ4GOZJGJV"
                            }

                # with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w+') as outfile:
                #     json.dump(sunat_data, outfile)

                xmlPath = str(os.path.dirname(os.path.abspath(__file__))).replace("controllers","models")+'/xml'
                SunatService = Service()
                SunatService.setXMLPath(xmlPath)
                
                if("F0" in serieConsecutivoString):
                    SunatService.fileName = str(company_fields["vat"])+"-01-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
                    SunatService.documentType = str("01")
                if("BF" in serieConsecutivoString):
                    SunatService.fileName = str(company_fields["vat"])+"-03-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
                    SunatService.documentType = str("03")
                if("FD" in serieConsecutivoString):
                    SunatService.fileName = str(company_fields["vat"])+"-08-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
                    SunatService.documentType = str("08")
                if("FC" in serieConsecutivoString):
                    SunatService.fileName = str(company_fields["vat"])+"-07-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
                    SunatService.documentType = str("07")

                SunatService.initSunatAPI(company_fields["api_mode"], "sendBill")
                sunatResponse = SunatService.processInvoiceFromSignedXML(sunat_data)
                
                #with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                #            json.dump(SunatService.fileName, outfile)

                if(sunatResponse["status"] == "OK"):
                    # save xml documents steps for reference in edocs
                    response_document_filename = str("R_")+"-01-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

                    api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+"REFERENCIA: "+str(sunatResponse["body"]["referencia"]).replace("'",'"')+"\n"+" "+str(sunatResponse["body"]["description"]).replace("'",'"')
                    query = "update account_invoice set sunat_request_status = 'OK', api_message = '"+str(api_message)+"', response_document_filename = '"+str(response_document_filename)+"', sunat_request_type = 'Automatizada' where id = "+str(invoice_unsubmited["id"])
                    request.cr.execute(query)
                    #if(serieConsecutivo=="00000008"):
                    #    with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                    #        json.dump(query, outfile)
                else:
                    api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+" "+str(sunatResponse["body"]).replace("'",'"')+"\n"+"CÓDIGO ERROR: "+str(sunatResponse["code"]).replace("'",'"')
                    query = "update account_invoice set sunat_request_status = 'FAIL', api_message = '"+str(api_message)+"', sunat_request_type = 'Automatizada' where id = "+str(invoice_unsubmited["id"])
                    request.cr.execute(query)
                    #if(serieConsecutivo):
                    #    with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                    #        json.dump(serieConsecutivo, outfile)
