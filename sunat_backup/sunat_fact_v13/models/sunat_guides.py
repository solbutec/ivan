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

class SunatEguide(models.Model):
    _name = 'sunat.eguide'
    _table = 'stock_picking'

    name = fields.Char(string='Guia', readonly=True)
    create_date = fields.Datetime(string='Creado en', readonly=True)

    unsigned_document = fields.Binary(string="XML - No firmado", default=None, readonly=True, filename="unsigned_document_filename" ,filters='*.xml', type="xml")
    unsigned_document_filename = fields.Char(string="Unsigned Filename", invisible="1", default="unsigned.XML")

    signed_document = fields.Binary(string="XML - Firmado", default=None, readonly=True, filename="signed_document_filename" ,filters='*.xml', type="xml")
    signed_document_filename = fields.Char(string="Signed Filename", invisible="1", default="signed.XML")
    
    response_document = fields.Binary(string="XML - Respuesta", default=None, readonly=True, filename="response_document_filename",filters='*.xml', type="xml")
    response_document_filename = fields.Char(string="Response Filename", invisible="1", default="response.XML")

    api_message = fields.Text(name="api_message", string="Estado", default='Documento contable sin emitir.', readonly=True)

    sunat_request_status = fields.Text(string="Estado Emisión", name="sunat_request_status", default='No Emitido')
    sunat_request_type = fields.Text(string="Método", name="sunat_request_type", default='Automatizada')

    qr_image = fields.Text(name="qr_image", default='')

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'eguide')
        
        self._cr.execute(
                         """
                            CREATE OR REPLACE VIEW eguide AS 
                            ( 
                              SELECT name as name, 
                                     stock_picking.create_date as create_date,   
                                     stock_picking.unsigned_document as unsigned_document,
                                     stock_picking.signed_document as signed_document, 
                                     stock_picking.response_document as response_document,
                                     stock_picking.api_message as api_message,
                                     stock_picking.sunat_request_type as sunat_request_type,
                                     stock_picking.qr_image as qr_image
                              FROM stock_picking 
                              WHERE name like '%T001%'
                            )                        
                         """
                        )
     #Automated task for submit failed or unsubmited invoices 
    def edocs_submit_guides(self, **kw):
        
        query = "select nextcall from ir_cron where cron_name = '"+str("sunat_edocs")+"'"
        request.cr.execute(query)
        cron_job_edocs = request.cr.dictfetchone()
        nextcall_datetime = str(cron_job_edocs["nextcall"]).split(" ")
        guide_date_limit = nextcall_datetime[0]
        
        query = "select id, name, company_id, unsigned_document, signed_document, response_document from stock_picking where name like '%T001%' and create_date <= '"+str(guide_date_limit)+"' and (sunat_request_status = '"+str("FAIL")+"' or sunat_request_status = '"+str("No Emitido")+"' or sunat_request_status = '"+str("not_requested")+"') and name like '%T001%'"
        request.cr.execute(query)
        guides_unsubmited = request.cr.dictfetchall()        

        #with open('/odoo_peru_sunat/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
        #    json.dump(query, outfile) 
        
        for guide_unsubmited in guides_unsubmited:               
            query = "select res_partner.vat, res_company.api_mode, res_company.sol_ruc, res_company.sol_username, res_company.sol_password, res_company.certs from res_company left join res_partner on res_partner.company_id = res_company.id where res_company.id = "+str(guide_unsubmited['company_id'])+" and res_partner.is_company = TRUE and res_company.partner_id = res_partner.id"
            
            request.cr.execute(query)
            company_fields = request.cr.dictfetchone()                   

            serieParts = str(guide_unsubmited["name"]).split("-")             
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]
            
            sunat_data = {
                            "secuencia_consecutivo":serieConsecutivo,
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

            xmlPath = str(os.path.dirname(os.path.abspath(__file__))).replace("controllers","models")+'/xml'
            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            
            if("T001" in serieConsecutivoString):
                SunatService.fileName = str(company_fields["vat"])+"-09-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
            
            SunatService.initSunatAPI(company_fields["api_mode"], "sendBill")
            sunatResponse = SunatService.processDeliveryGuideFromSignedXML(sunat_data)
                                    
            if(sunatResponse["status"] == "OK"):
                # save xml documents steps for reference in edocs
                response_document_filename = str("R_")+"-09-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

                api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+"REFERENCIA: "+str(sunatResponse["body"]["referencia"]).replace("'",'"')+"\n"+" "+str(sunatResponse["body"]["description"]).replace("'",'"')
                query = "update stock_picking set sunat_request_status = 'OK', api_message = '"+str(api_message)+"', response_document_filename = '"+str(response_document_filename)+"', sunat_request_type = 'Automatizada' where id = "+str(guide_unsubmited["id"])
                request.cr.execute(query)
                #if(serieConsecutivo=="00000008"):
                #    with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                #        json.dump(query, outfile)
            else:
                api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+" "+str(sunatResponse["body"]).replace("'",'"')+"\n"+"CÓDIGO ERROR: "+str(sunatResponse["code"]).replace("'",'"')
                query = "update stock_picking set sunat_request_status = 'FAIL', api_message = '"+str(api_message)+"', sunat_request_type = 'Automatizada' where id = "+str(guide_unsubmited["id"])
                request.cr.execute(query)
                #if(serieConsecutivo):
                #    with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                #        json.dump(serieConsecutivo, outfile)
