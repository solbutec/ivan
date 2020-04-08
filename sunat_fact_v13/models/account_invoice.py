# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning, UserError
from odoo import http
from pprint import pprint
import time
from datetime import datetime
import hmac
import hashlib
import requests 
import json
import os
from odoo.http import request
from decimal import Decimal
import qrcode
import base64
import random
import sys
from io import BytesIO

from sunatservice.sunatservice import Service



class account_invoice(models.Model):

    _inherit = 'account.invoice'
    
    api_message = fields.Text(name="api_message", string="Estado", default='Documento contable sin emitir.', readonly=True)
    discrepance_code = fields.Text(name="discrepance_code", default='', readonly=True)
    discrepance_text = fields.Text(name="discrepance_text", string="Discrepancia", default="", readonly=True) 
    
    _columns = { 'api_message': fields.Text('Estado'),'discrepance': fields.Text('Discrepancia')}
    _defaults = {'api_message':'Documento contable sin emitir.','diario':'factura','discrepance':''}

      
    qr_in_report = fields.Boolean('Ver QR en reporte' , default=True)
    unsigned_document = fields.Binary(string="XML - no firmado", default=None, readonly=True, filename="unsigned.XML" ,filters='*.xml')
    unsigned_document_filename = fields.Char("Unsigned Filename")

    signed_document = fields.Binary(string="XML - Firmado", default=None, readonly=True, filename="unsigned.XML" ,filters='*.xml')
    signed_document_filename = fields.Char("Signed Filename")
    
    response_document = fields.Binary(string="XML - respuesta", default=None, readonly=True, filename="unsigned.XML" ,filters='*.xml')
    response_document_filename = fields.Char("Response Filename")
    qr_image = fields.Text(name="qr_image", default='')

    sunat_request_status = fields.Text(name="sunat_request_status", default='No Emitido')
    sunat_request_type = fields.Text(name="sunat_request_type", default='Automatizada')
    sunat_total_letters = fields.Char(name="sunat_total_letters", default='Automatizada')

    api_message_baja_doc = fields.Html(name="api_message_baja_doc", string="Comunicado de baja", default='sin_baja', readonly=True)
    was_cancelled = fields.Char(default='FAIL')

    @api.multi
    def invoice_validate(self):
        
        urlPath = http.request.httprequest.full_path
        if 'payment/process' in urlPath:
            return super(account_invoice, self).invoice_validate()

        invoice_items = []       

        for invoice in self: 
            if invoice.partner_id.vat=="" or invoice.partner_id.vat==False:
               raise Warning(_("Por favor, establecer el documento del receptor"))

        eDocumentType = self.journal_id.code
        index = 0
        sunat_items = [] 
        totalVentaPedido = 0
        subTotalPedido = 0
        #impuestos
        tributos_globales = {}
        tributos = {}
        
        processInvoiceAction = "fill_only"        

        if(eDocumentType=="FAC" or eDocumentType=="INV"): 
            for invoice in self:      
                sunat_request_type = invoice.company_id.sunat_request_type 

                if(sunat_request_type=="automatic"):
                    sunat_request_type = "Automatizada"  
                    processInvoiceAction = "fill_only"
                else:
                    sunat_request_type = "Documento Validado"
                    processInvoiceAction = "fill_submit"
                
                if(self.isPosOrder(invoice.origin)):
                    processInvoiceAction = "fill_submit"


                items = invoice.invoice_line_ids
                for item in items:
                    item_tributos = []
                    subTotalVenta = ((item.price_unit * item.quantity))

                    for tax in item.invoice_line_tax_ids:   

                        if(tax.amount_type=="fixed"):
                            impuesto = tax.amount * item.quantity                                                
                            monto_afectacion_tributo = ((impuesto))
                            if(bool(tax.price_include)==True):
                                monto_afectacion_tributo = subTotalVenta - ((subTotalVenta / ((float(impuesto)/100) + 1)))

                        if(tax.amount_type=="percent"):
                            impuesto = tax.amount                                      
                            monto_afectacion_tributo = ((subTotalVenta * (float(impuesto)/100)))

                            if(bool(tax.price_include)==True):
                                monto_afectacion_tributo = subTotalVenta - ((subTotalVenta / ((float(impuesto)/100) + 1)))

                        if(bool(tax.price_include)==True):
                            subTotalVenta -= monto_afectacion_tributo

                        totalVenta = subTotalVenta
                        totalVenta +=  monto_afectacion_tributo

                        item_tributo = {
                                            "codigo":tax.sunat_tributo,
                                            "porcentaje":tax.amount,
                                            "tipo_calculo":tax.amount_type, # percent:IGV... and fixed:plastic bags supported
                                            "montoAfectacionTributo":monto_afectacion_tributo,
                                            "total_venta":subTotalVenta,
                                            'tipoAfectacionTributoIGV': tax.sunat_tributo_afectacion_igv, # pendiente si es igv - catalogo 7. 
                                            'sistemaCalculoISC':tax.sunat_tributo_calculo_isc
                                                     #pendiente si es isc - catalogo 8 para codigo = 2000 ISC
                                       }

                        item_tributos.append(item_tributo) 

                    tributos_globales = self.add_global_tributes(item_tributos,tributos_globales)
                    price_unit = item.price_unit

                    if(bool(tax.price_include)==True):                        
                        price_unit = subTotalVenta / item.quantity

                    sunat_item = {
                                    'id':str(item.product_id.id),
                                    'cantidad':str(item.quantity),
                                    "medidaCantidad":str(item.product_id.uom_id.sunat_unit_code),
                                    'descripcion':item.name,
                                    "precioUnidad":price_unit,
                                    'tipoPrecioVentaUnitario':self.get_sunat_product_type_price( item.product_id.id),  #instalar en ficha de producto catalogo 16    01 Precio unitario (incluye el IGV), 02 Valor referencial unitario en operaciones no onerosas                                        
                                    'clasificacionProductoServicioCodigo':self.get_sunat_product_code_classification( item.product_id.id),
                                    "subTotalVenta":subTotalVenta,
                                    'totalVenta':totalVenta, 
                                    "tributos":item_tributos
                                 }
                    sunat_items.append(sunat_item)
                    totalVentaPedido += float(totalVenta)
                    subTotalPedido += float(subTotalVenta)

            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")

            secuencia = str(invoice.number).split("-")
            secuencia_serie = secuencia[0]
            secuencia_consecutivo = secuencia[1] 

            # Start data validation
            Vcompany_address = self.validate_address(invoice.company_id)
            if(bool(Vcompany_address["errors"])==True):
                raise Warning (str("Compañia emisora")+Vcompany_address["msn"])

            Vcompany_certificate = self.validate_certificate(invoice.company_id)
            if(bool(Vcompany_certificate["errors"])==True):
                raise Warning (str("Compañia emisora")+Vcompany_certificate["msn"])

            Vpartner_address = self.validate_address(invoice.partner_id)
            if(bool(Vpartner_address["errors"])==True):
                raise Warning (str("Cliente / Socio")+Vpartner_address["msn"])

            

            sunat_data = {
                                "serie": str(secuencia_serie),
                                "numero":str(secuencia_consecutivo),
                                "emisor":{
                                            "tipo_documento":invoice.company_id.sunat_tipo_documento,
                                            "nro":invoice.company_id.vat,
                                            "nombre":str(invoice.company_id.name).capitalize(),
                                            "direccion":str(invoice.company_id.street).capitalize(),
                                            "ciudad":str(Vcompany_address["address"]["province"]["name"]),
                                            "ciudad_sector":str(Vcompany_address["address"]["district"]["name"]),
                                            "departamento":str(invoice.company_id.state_id.name).capitalize(),
                                            "codigoPostal":invoice.company_id.zip,
                                            "codigoPais":invoice.company_id.country_id.code,
                                            "ubigeo":(str(invoice.company_id.ubigeo) if(str(invoice.company_id.ubigeo)!="") else str(invoice.company_id.zip))
                                         },
                                "receptor": {
                                                "tipo_documento":invoice.partner_id.sunat_tipo_documento,
                                                "nro":invoice.partner_id.vat,
                                                "nombre":str(invoice.partner_id.name).capitalize(),
                                                "direccion":str(invoice.partner_id.street).capitalize(),
                                                "ciudad":str(Vpartner_address["address"]["province"]["name"]),
                                                "ciudad_sector":str(Vpartner_address["address"]["district"]["name"]),
                                                "departamento":str(invoice.partner_id.state_id.name),
                                                "codigoPostal":invoice.partner_id.zip,
                                                "codigoPais":invoice.partner_id.country_id.code,
                                                "ubigeo":(str(invoice.partner_id.ubigeo) if(str(invoice.partner_id.ubigeo)!="") else str(invoice.partner_id.zip))
                                            },
                                "fechaEmision":str(invoice.date_invoice).replace("/","-",3),
                                "fechaVencimiento":str(invoice.date_due).replace("/","-",3),
                                "horaEmision":currentTime,
                                "subTotalVenta":subTotalPedido,
                                "totalVentaGravada":totalVentaPedido,
                                "tipoMoneda":invoice.currency_id.name,
                                "items": sunat_items,
                                "tributos":tributos_globales,
                                "sunat_sol": {
                                            "ruc":invoice.company_id.sol_ruc,
                                            'usuario':invoice.company_id.sol_username,
                                            'clave':invoice.company_id.sol_password,
                                            'certificado':{
                                                            'crt':invoice.company_id.cert_pem_filename,
                                                            'key':invoice.company_id.key_pem_filename,
                                                            'pass':invoice.company_id.key_pass,
                                                          }
                                         },
                                "accion": processInvoiceAction,
                                'licencia':"081OHTGAVHJZ4GOZJGJV"
                            }
            
            serieParts = str(invoice.number).split("-")
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]
            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")

            xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
            
            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            SunatService.fileName = str(invoice.company_id.vat)+"-01-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
            SunatService.initSunatAPI(invoice.company_id.api_mode, "sendBill")
            SunatResponse = SunatService.processInvoice(sunat_data)
            #raise Warning(str(SunatResponse["body"]))
            # save xml documents steps for reference in edocs
            
            if 'xml_response' in SunatResponse:
                self.response_document = SunatResponse["xml_response"]
                self.response_document_filename = str("R_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

            if 'xml_signed' in SunatResponse:
                self.signed_document = SunatResponse["xml_signed"]
                self.signed_document_filename = str("F_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

            if 'xml_unsigned' in SunatResponse:
                self.unsigned_document = SunatResponse["xml_unsigned"]
                self.unsigned_document_filename = str("NF_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")
            
            # generate qr for invoices and tickets in pos
            base_url = request.env['ir.config_parameter'].get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            qr = qrcode.QRCode(
                                version=1,
                                error_correction=qrcode.constants.ERROR_CORRECT_L,
                                box_size=20,
                                border=4,
                              )
            total_tributo_igv = self.get_sumatoria_tributo_igv(tributos_globales)            
            qr_code_text = str(sunat_data["emisor"]["nro"]) + str("|") + str(sunat_data["emisor"]["tipo_documento"]) + str("|") + str(sunat_data["serie"]) + str("|") + str(sunat_data["numero"]) + str("|") + str(total_tributo_igv) + str("|") + str(format(float(sunat_data["totalVentaGravada"]),'.2f')) + str("|") + str(sunat_data["fechaEmision"]) + str("|") + str(sunat_data["receptor"]["tipo_documento"]) + str("|") + str(sunat_data["receptor"]["nro"])
            qr.add_data(qr_code_text)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            self.qr_image = base64.b64encode(temp.getvalue())
            self.qr_in_report = True

            self.sunat_request_type = sunat_request_type
            self.sunat_total_letters = self.literal_price(totalVentaPedido)

            if 'status' in SunatResponse:
                if(SunatResponse["status"] == "OK"):                                                                                    
                    self.api_message = "ESTADO: "+str(SunatResponse["status"])+"\n"+"REFERENCIA: "+str(SunatResponse["body"]["referencia"]).replace("'",'"')+"\n"+" "+str(SunatResponse["body"]["description"]).replace("'",'"')
                    self.sunat_request_status = 'OK'
                    # raise Warning("OK")
                    #raise Warning("Generated")
                    return super(account_invoice, self).invoice_validate()
                else:
                    self.sunat_request_status = 'FAIL'
                    self.api_message = "ESTADO: "+str(SunatResponse["status"])+"\n"+" "+str(SunatResponse["body"])+"\n"+"CÓDIGO ERROR: "+str(SunatResponse["code"])
                    #raise Warning("Generated")
                    return super(account_invoice, self).invoice_validate()
            else:
                return super(account_invoice, self).invoice_validate()

################################################################################################
# Para boleta
################################################################################################
        elif(eDocumentType=="BOL"): 
            for invoice in self:      
                sunat_request_type = invoice.company_id.sunat_request_type 

                if(sunat_request_type=="automatic"):
                    sunat_request_type = "Automatizada"  
                    processInvoiceAction = "fill_only"    
                else:
                    sunat_request_type = "Documento Validado"
                    processInvoiceAction = "fill_submit"

                if(self.isPosOrder(invoice.origin)):
                    processInvoiceAction = "fill_submit"


                items = invoice.invoice_line_ids
                for item in items:
                    item_tributos = []
                    subTotalVenta = ((item.price_unit * item.quantity))

                    for tax in item.invoice_line_tax_ids:   

                        if(tax.amount_type=="fixed"):
                            impuesto = tax.amount * item.quantity                                                
                            monto_afectacion_tributo = ((impuesto))
                            if(bool(tax.price_include)==True):
                                monto_afectacion_tributo = subTotalVenta - ((subTotalVenta / ((float(impuesto)/100) + 1)))

                        if(tax.amount_type=="percent"):
                            impuesto = tax.amount                                      
                            monto_afectacion_tributo = ((subTotalVenta * (float(impuesto)/100)))

                            if(bool(tax.price_include)==True):
                                monto_afectacion_tributo = subTotalVenta - ((subTotalVenta / ((float(impuesto)/100) + 1)))

                        if(bool(tax.price_include)==True):
                            subTotalVenta -= monto_afectacion_tributo

                        totalVenta = subTotalVenta
                        totalVenta +=  monto_afectacion_tributo

                        item_tributo = {
                                            "codigo":tax.sunat_tributo,
                                            "porcentaje":tax.amount,
                                            "tipo_calculo":tax.amount_type, # percent:IGV... and fixed:plastic bags supported
                                            "montoAfectacionTributo":monto_afectacion_tributo,
                                            "total_venta":subTotalVenta,
                                            'tipoAfectacionTributoIGV': tax.sunat_tributo_afectacion_igv, # pendiente si es igv - catalogo 7. 
                                            'sistemaCalculoISC':tax.sunat_tributo_calculo_isc
                                                     #pendiente si es isc - catalogo 8 para codigo = 2000 ISC
                                       }

                        item_tributos.append(item_tributo) 

                    tributos_globales = self.add_global_tributes(item_tributos,tributos_globales)
                    price_unit = item.price_unit

                    if(bool(tax.price_include)==True):                        
                        price_unit = subTotalVenta / item.quantity

                    sunat_item = {
                                    'id':str(item.product_id.id),
                                    'cantidad':str(item.quantity),
                                    "medidaCantidad":str(item.product_id.uom_id.sunat_unit_code),
                                    'descripcion':item.name,
                                    "precioUnidad":price_unit,
                                    'tipoPrecioVentaUnitario':self.get_sunat_product_type_price( item.product_id.id),  #instalar en ficha de producto catalogo 16    01 Precio unitario (incluye el IGV), 02 Valor referencial unitario en operaciones no onerosas                                        
                                    'clasificacionProductoServicioCodigo':self.get_sunat_product_code_classification( item.product_id.id),
                                    "subTotalVenta":subTotalVenta,
                                    'totalVenta':totalVenta, 
                                    "tributos":item_tributos
                                }
                    sunat_items.append(sunat_item)
                    totalVentaPedido += float(totalVenta)
                    subTotalPedido += float(subTotalVenta)

            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")                

            secuencia = str(invoice.number).split("-")             
            secuencia_serie = secuencia[0]
            secuencia_consecutivo = secuencia[1] 

            # Start data validation
            Vcompany_address = self.validate_address(invoice.company_id)
            Vpartner_address = self.validate_address(invoice.partner_id)

            # Start data validation
            Vcompany_address = self.validate_address(invoice.company_id)
            if(bool(Vcompany_address["errors"])):
                raise Warning (str("Cliente / Socio")+Vcompany_address["msn"])

            Vcompany_certificate = self.validate_certificate(invoice.company_id)
            if(bool(Vcompany_certificate["errors"])==True):
                raise Warning (str("Compañia emisora")+Vcompany_certificate["msn"])

            Vpartner_address = self.validate_address(invoice.partner_id)
            if(bool(Vpartner_address["errors"])):
                raise Warning (str("Compañia emisora")+Vpartner_address["msn"])

            sunat_data = {
                                "serie": str(secuencia_serie),
                                "numero":str(secuencia_consecutivo),
                                "emisor":{
                                            "tipo_documento":invoice.company_id.sunat_tipo_documento,
                                            "nro":invoice.company_id.vat,
                                            "nombre":str(invoice.company_id.name).capitalize(),
                                            "direccion":str(invoice.company_id.street).capitalize(),
                                            "ciudad":str(Vcompany_address["address"]["province"]["name"]),
                                            "ciudad_sector":str(Vcompany_address["address"]["district"]["name"]),
                                            "departamento":str(invoice.company_id.state_id.name).capitalize(),
                                            "codigoPostal":invoice.company_id.zip,
                                            "codigoPais":invoice.company_id.country_id.code,
                                            "ubigeo":(str(invoice.company_id.ubigeo) if(str(invoice.company_id.ubigeo)!="") else str(invoice.company_id.zip))
                                        },
                                "receptor": {
                                                "tipo_documento":invoice.partner_id.sunat_tipo_documento,
                                                "nro":invoice.partner_id.vat,
                                                "nombre":str(invoice.partner_id.name).capitalize(),
                                                "direccion":str(invoice.partner_id.street).capitalize(),
                                                "ciudad":str(Vpartner_address["address"]["province"]["name"]),
                                                "ciudad_sector":str(Vpartner_address["address"]["district"]["name"]),
                                                "departamento":str(invoice.partner_id.state_id.name),
                                                "codigoPostal":invoice.partner_id.zip,
                                                "codigoPais":invoice.partner_id.country_id.code,
                                                "ubigeo":(str(invoice.partner_id.ubigeo) if(str(invoice.partner_id.ubigeo)!="") else str(invoice.partner_id.zip))
                                            },
                                "fechaEmision":str(invoice.date_invoice).replace("/","-",3),
                                "fechaVencimiento":str(invoice.date_due).replace("/","-",3),
                                "horaEmision":currentTime,
                                "subTotalVenta":subTotalPedido,
                                "totalVentaGravada":totalVentaPedido,
                                "tipoMoneda":invoice.currency_id.name,
                                "items": sunat_items,
                                "tributos":tributos_globales,
                                "sunat_sol": {
                                            "ruc":invoice.company_id.sol_ruc,
                                            'usuario':invoice.company_id.sol_username,
                                            'clave':invoice.company_id.sol_password,
                                            'certificado':{
                                                                'crt':invoice.company_id.cert_pem_filename,
                                                                'key':invoice.company_id.key_pem_filename,
                                                                'pass':invoice.company_id.key_pass,
                                                              }
                                        },
                                "accion": processInvoiceAction,
                                'licencia':"081OHTGAVHJZ4GOZJGJV"
                            }

            #with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
            #    json.dump(sunat_data, outfile)
            
            #raise Warning("Generado")
            serieParts = str(invoice.number).split("-")             
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]
            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")

            xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
            
            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            SunatService.fileName = str(invoice.company_id.vat)+"-03-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
            SunatService.initSunatAPI(invoice.company_id.api_mode, "sendBill")
            SunatResponse = SunatService.processTicket(sunat_data)

            # save xml documents steps for reference in edocs
            if 'xml_response' in SunatResponse:
                self.response_document = SunatResponse["xml_response"]
                self.response_document_filename = str("R_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

            if 'xml_signed' in SunatResponse:
                self.signed_document = SunatResponse["xml_signed"]
                self.signed_document_filename = str("F_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

            if 'xml_unsigned' in SunatResponse:
                self.unsigned_document = SunatResponse["xml_unsigned"]
                self.unsigned_document_filename = str("NF_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")
            
            # generate qr for invoices and tickets in pos
            base_url = request.env['ir.config_parameter'].get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            qr = qrcode.QRCode(
                                version=1,
                                error_correction=qrcode.constants.ERROR_CORRECT_L,
                                box_size=20,
                                border=4,
                            )

            total_tributo_igv = self.get_sumatoria_tributo_igv(tributos_globales)            
            qr_code_text = str(sunat_data["emisor"]["nro"]) + str("|") + str(sunat_data["emisor"]["tipo_documento"]) + str("|") + str(sunat_data["serie"]) + str("|") + str(sunat_data["numero"]) + str("|") + str(total_tributo_igv) + str("|") + str(format(float(sunat_data["totalVentaGravada"]),'.2f')) + str("|") + str(sunat_data["fechaEmision"]) + str("|") + str(sunat_data["receptor"]["tipo_documento"]) + str("|") + str(sunat_data["receptor"]["nro"])
            qr.add_data(qr_code_text)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            self.qr_image = base64.b64encode(temp.getvalue())
            self.qr_in_report = True

            self.sunat_request_type = sunat_request_type
            self.sunat_total_letters = self.literal_price(totalVentaPedido)
            #raise Warning(SunatResponse["body"]["description"])
            #with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
            #    json.dump(SunatResponse["body"], outfile) 
            if 'status' in SunatResponse:
                if(SunatResponse["status"] == "OK"):                                                                                    
                    self.api_message = "ESTADO: "+str(SunatResponse["status"])+"\n"+"REFERENCIA: "+str(SunatResponse["body"]["referencia"]).replace("'",'"')+"\n"+" "+str(SunatResponse["body"]["description"]).replace("'",'"')
                    self.sunat_request_status = 'OK'
                    # raise Warning("OK")
                    return super(account_invoice, self).invoice_validate()
                else:
                    self.sunat_request_status = 'FAIL'
                    self.api_message = "ESTADO: "+str(SunatResponse["status"])+"\n"+" "+str(SunatResponse["body"])+"\n"+"CÓDIGO ERROR: "+str(SunatResponse["code"])
                    return super(account_invoice, self).invoice_validate()
            else:
                return super(account_invoice, self).invoice_validate()


################################################################################################
# Para Nota Credito
################################################################################################
        elif(eDocumentType=="NCR"): 
            for invoice in self:      
                sunat_request_type = invoice.company_id.sunat_request_type 

                if(sunat_request_type=="automatic"):
                    sunat_request_type = "Automatizada"  
                    processInvoiceAction = "fill_only"    
                else:
                    sunat_request_type = "Documento Validado"
                    processInvoiceAction = "fill_submit"

                if(self.isPosOrder(invoice.origin)):
                    processInvoiceAction = "fill_submit"

                items = invoice.invoice_line_ids
                for item in items:
                    item_tributos = []
                    subTotalVenta = ((item.price_unit * item.quantity))

                    for tax in item.invoice_line_tax_ids:   

                        if(tax.amount_type=="fixed"):
                            impuesto = tax.amount * item.quantity                                                
                            monto_afectacion_tributo = ((impuesto))
                            if(bool(tax.price_include)==True):
                                monto_afectacion_tributo = subTotalVenta - ((subTotalVenta / ((float(impuesto)/100) + 1)))

                        if(tax.amount_type=="percent"):
                            impuesto = tax.amount                                      
                            monto_afectacion_tributo = ((subTotalVenta * (float(impuesto)/100)))

                            if(bool(tax.price_include)==True):
                                monto_afectacion_tributo = subTotalVenta - ((subTotalVenta / ((float(impuesto)/100) + 1)))

                        if(bool(tax.price_include)==True):
                            subTotalVenta -= monto_afectacion_tributo

                        totalVenta = subTotalVenta
                        totalVenta +=  monto_afectacion_tributo

                        item_tributo = {
                                            "codigo":tax.sunat_tributo,
                                            "porcentaje":tax.amount,
                                            "tipo_calculo":tax.amount_type, # percent:IGV... and fixed:plastic bags supported
                                            "montoAfectacionTributo":monto_afectacion_tributo,
                                            "total_venta":subTotalVenta,
                                            'tipoAfectacionTributoIGV': tax.sunat_tributo_afectacion_igv, # pendiente si es igv - catalogo 7. 
                                            'sistemaCalculoISC':tax.sunat_tributo_calculo_isc
                                                     #pendiente si es isc - catalogo 8 para codigo = 2000 ISC
                                       }

                        item_tributos.append(item_tributo) 

                    tributos_globales = self.add_global_tributes(item_tributos,tributos_globales)
                    price_unit = item.price_unit

                    if(bool(tax.price_include)==True):                        
                        price_unit = subTotalVenta / item.quantity

                    sunat_item = {
                                    'id':str(item.product_id.id),
                                    'cantidad':str(item.quantity),
                                    "medidaCantidad":str(item.product_id.uom_id.sunat_unit_code),
                                    'descripcion':item.name,
                                    "precioUnidad":price_unit,
                                    'tipoPrecioVentaUnitario':self.get_sunat_product_type_price( item.product_id.id),  #instalar en ficha de producto catalogo 16    01 Precio unitario (incluye el IGV), 02 Valor referencial unitario en operaciones no onerosas                                        
                                    'clasificacionProductoServicioCodigo':self.get_sunat_product_code_classification( item.product_id.id),
                                    "subTotalVenta":subTotalVenta,
                                    'totalVenta':totalVenta, 
                                    "tributos":item_tributos
                                }
                    sunat_items.append(sunat_item)
                    totalVentaPedido += float(totalVenta)
                    subTotalPedido += float(subTotalVenta)

            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")                

            secuencia = str(invoice.number).split("-")             
            secuencia_serie = secuencia[0]
            secuencia_consecutivo = secuencia[1] 

            
            invoice_origin_document_journal_code = self.get_origin_document_journal_code(self.origin)
            sunat_origin_document_type = self.get_sunat_document_type(invoice_origin_document_journal_code)

            # Start data validation
            Vcompany_address = self.validate_address(invoice.company_id)
            Vpartner_address = self.validate_address(invoice.partner_id)

            Vcompany_certificate = self.validate_certificate(invoice.company_id)
            if(bool(Vcompany_certificate["errors"])==True):
                raise Warning (str("Compañia emisora")+Vcompany_certificate["msn"])

             # Start data validation
            Vcompany_address = self.validate_address(invoice.company_id)
            if(bool(Vcompany_address["errors"])):
                raise Warning (str("Cliente / Socio")+Vcompany_address["msn"])

            Vpartner_address = self.validate_address(invoice.partner_id)
            if(bool(Vpartner_address["errors"])):
                raise Warning (str("Compañia emisora")+Vpartner_address["msn"])

            sunat_data = {
                                "serie": str(secuencia_serie),
                                "numero":str(secuencia_consecutivo),
                                "emisor":{
                                            "tipo_documento":invoice.company_id.sunat_tipo_documento,
                                            "nro":invoice.company_id.vat,
                                            "nombre":str(invoice.company_id.name).capitalize(),
                                            "direccion":str(invoice.company_id.street).capitalize(),
                                            "ciudad":str(Vcompany_address["address"]["province"]["name"]),
                                            "ciudad_sector":str(Vcompany_address["address"]["district"]["name"]),
                                            "departamento":str(invoice.company_id.state_id.name).capitalize(),
                                            "codigoPostal":invoice.company_id.zip,
                                            "codigoPais":invoice.company_id.country_id.code,
                                            "ubigeo":(str(invoice.company_id.ubigeo) if(str(invoice.company_id.ubigeo)!="") else str(invoice.company_id.zip))
                                        },
                                "receptor": {
                                                "tipo_documento":invoice.partner_id.sunat_tipo_documento,
                                                "nro":invoice.partner_id.vat,
                                                "nombre":str(invoice.partner_id.name).capitalize(),
                                                "direccion":str(invoice.partner_id.street).capitalize(),
                                                "ciudad":str(Vpartner_address["address"]["province"]["name"]),
                                                "ciudad_sector":str(Vpartner_address["address"]["district"]["name"]),
                                                "departamento":str(invoice.partner_id.state_id.name),
                                                "codigoPostal":invoice.partner_id.zip,
                                                "codigoPais":invoice.partner_id.country_id.code,
                                                "ubigeo":(str(invoice.partner_id.ubigeo) if(str(invoice.partner_id.ubigeo)!="") else str(invoice.partner_id.zip))
                                            },
                                "notaDescripcion":self.name,
                                "notaDiscrepanciaCode":self.discrepance_code,
                                "documentoOrigen":self.origin,
                                "documentoOrigenTipo": sunat_origin_document_type, #01 factura, 03 boleta, 12 tiket de venta
                                "fechaEmision":str(invoice.date_invoice).replace("/","-",3),
                                "fechaVencimiento":str(invoice.date_due).replace("/","-",3),
                                "horaEmision":currentTime,
                                "subTotalVenta":subTotalPedido,
                                "totalVentaGravada":totalVentaPedido,
                                "tipoMoneda":invoice.currency_id.name,
                                "items": sunat_items,
                                "tributos":tributos_globales,
                                "sunat_sol": {
                                                "ruc":invoice.company_id.sol_ruc,
                                                'usuario':invoice.company_id.sol_username,
                                                'clave':invoice.company_id.sol_password,
                                                'certificado':{
                                                                'crt':invoice.company_id.cert_pem_filename,
                                                                'key':invoice.company_id.key_pem_filename,
                                                                'pass':invoice.company_id.key_pass,
                                                              }
                                             },
                                "accion": processInvoiceAction,
                                'licencia':"081OHTGAVHJZ4GOZJGJV"
                            }

            #with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
            #        json.dump(sunat_data, outfile)
            
            #raise Warning("Generado")
            serieParts = str(invoice.number).split("-")             
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]
            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")

            xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
            
            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            SunatService.fileName = str(invoice.company_id.vat)+"-07-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
            SunatService.initSunatAPI(invoice.company_id.api_mode, "sendBill")
            SunatResponse = SunatService.processCreditNote(sunat_data)
            
            # save xml documents steps for reference in edocs
            if 'xml_response' in SunatResponse:
                self.response_document = SunatResponse["xml_response"]
                self.response_document_filename = str("R_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

            if 'xml_signed' in SunatResponse:
                self.signed_document = SunatResponse["xml_signed"]
                self.signed_document_filename = str("F_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

            if 'xml_unsigned' in SunatResponse:
                self.unsigned_document = SunatResponse["xml_unsigned"]
                self.unsigned_document_filename = str("NF_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")
            
            # generate qr for invoices and tickets in pos
            base_url = request.env['ir.config_parameter'].get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            qr = qrcode.QRCode(
                                version=1,
                                error_correction=qrcode.constants.ERROR_CORRECT_L,
                                box_size=20,
                                border=4,
                            )

            total_tributo_igv = self.get_sumatoria_tributo_igv(tributos_globales)            
            qr_code_text = str(sunat_data["emisor"]["nro"]) + str("|") + str(sunat_data["emisor"]["tipo_documento"]) + str("|") + str(sunat_data["serie"]) + str("|") + str(sunat_data["numero"]) + str("|") + str(total_tributo_igv) + str("|") + str(format(float(sunat_data["totalVentaGravada"]),'.2f')) + str("|") + str(sunat_data["fechaEmision"]) + str("|") + str(sunat_data["receptor"]["tipo_documento"]) + str("|") + str(sunat_data["receptor"]["nro"])
            qr.add_data(qr_code_text)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            self.qr_image = base64.b64encode(temp.getvalue())
            self.qr_in_report = True

            self.sunat_request_type = sunat_request_type
            self.sunat_total_letters = self.literal_price(totalVentaPedido)
            #with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
            #    json.dump(SunatResponse["body"], outfile) 
            if 'status' in SunatResponse:
                if(SunatResponse["status"] == "OK"):
                    self.api_message = "ESTADO: "+str(SunatResponse["status"])+"\n"+"REFERENCIA: "+str(SunatResponse["body"]["referencia"]).replace("'",'"')+"\n"+" "+str(SunatResponse["body"]["description"]).replace("'",'"')
                    self.sunat_request_status = 'OK'
                    # raise Warning("OK")
                    return super(account_invoice, self).invoice_validate()
                else:
                    self.sunat_request_status = 'FAIL'
                    self.api_message = "ESTADO: "+str(SunatResponse["status"])+"\n"+" "+str(SunatResponse["body"])+"\n"+"CÓDIGO ERROR: "+str(SunatResponse["code"])
                    return super(account_invoice, self).invoice_validate()
            else:
                return super(account_invoice, self).invoice_validate()  

################################################################################################
# Para Nota Debito
################################################################################################
        elif(eDocumentType=="NDB"): 
            for invoice in self:      
                sunat_request_type = invoice.company_id.sunat_request_type 

                if(sunat_request_type=="automatic"):
                    sunat_request_type = "Automatizada"  
                    processInvoiceAction = "fill_only"    
                else:
                    sunat_request_type = "Documento Validado"
                    processInvoiceAction = "fill_submit"

                if(self.isPosOrder(invoice.origin)):
                    processInvoiceAction = "fill_submit"

                items = invoice.invoice_line_ids
                for item in items:
                    item_tributos = []
                    subTotalVenta = ((item.price_unit * item.quantity))

                    for tax in item.invoice_line_tax_ids:   

                        if(tax.amount_type=="fixed"):
                            impuesto = tax.amount * item.quantity                                                
                            monto_afectacion_tributo = ((impuesto))
                            if(bool(tax.price_include)==True):
                                monto_afectacion_tributo = subTotalVenta - ((subTotalVenta / ((float(impuesto)/100) + 1)))

                        if(tax.amount_type=="percent"):
                            impuesto = tax.amount                                      
                            monto_afectacion_tributo = ((subTotalVenta * (float(impuesto)/100)))

                            if(bool(tax.price_include)==True):
                                monto_afectacion_tributo = subTotalVenta - ((subTotalVenta / ((float(impuesto)/100) + 1)))

                        if(bool(tax.price_include)==True):
                            subTotalVenta -= monto_afectacion_tributo

                        totalVenta = subTotalVenta
                        totalVenta +=  monto_afectacion_tributo

                        item_tributo = {
                                            "codigo":tax.sunat_tributo,
                                            "porcentaje":tax.amount,
                                            "tipo_calculo":tax.amount_type, # percent:IGV... and fixed:plastic bags supported
                                            "montoAfectacionTributo":monto_afectacion_tributo,
                                            "total_venta":subTotalVenta,
                                            'tipoAfectacionTributoIGV': tax.sunat_tributo_afectacion_igv, # pendiente si es igv - catalogo 7. 
                                            'sistemaCalculoISC':tax.sunat_tributo_calculo_isc
                                                     #pendiente si es isc - catalogo 8 para codigo = 2000 ISC
                                       }

                        item_tributos.append(item_tributo) 

                    tributos_globales = self.add_global_tributes(item_tributos,tributos_globales)
                    price_unit = item.price_unit

                    if(bool(tax.price_include)==True):                        
                        price_unit = subTotalVenta / item.quantity

                    sunat_item = {
                                    'id':str(item.product_id.id),
                                    'cantidad':str(item.quantity),
                                    "medidaCantidad":str(item.product_id.uom_id.sunat_unit_code),
                                    'descripcion':item.name,
                                    "precioUnidad":price_unit,
                                    'tipoPrecioVentaUnitario':self.get_sunat_product_type_price( item.product_id.id),  #instalar en ficha de producto catalogo 16    01 Precio unitario (incluye el IGV), 02 Valor referencial unitario en operaciones no onerosas                                        
                                    'clasificacionProductoServicioCodigo':self.get_sunat_product_code_classification( item.product_id.id),
                                    "subTotalVenta":subTotalVenta,
                                    'totalVenta':totalVenta, 
                                    "tributos":item_tributos
                                }
                    sunat_items.append(sunat_item)
                    totalVentaPedido += float(totalVenta)
                    subTotalPedido += float(subTotalVenta)

            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")                

            secuencia = str(invoice.number).split("-")             
            secuencia_serie = secuencia[0]
            secuencia_consecutivo = secuencia[1] 

            
            invoice_origin_document_journal_code = self.get_origin_document_journal_code(self.origin)
            sunat_origin_document_type = self.get_sunat_document_type(invoice_origin_document_journal_code)

            # Start data validation
            Vcompany_address = self.validate_address(invoice.company_id)
            Vpartner_address = self.validate_address(invoice.partner_id)

            Vcompany_certificate = self.validate_certificate(invoice.company_id)
            if(bool(Vcompany_certificate["errors"])==True):
                raise Warning (str("Compañia emisora")+Vcompany_certificate["msn"])

             # Start data validation
            Vcompany_address = self.validate_address(invoice.company_id)
            if(bool(Vcompany_address["errors"])):
                raise Warning (str("Cliente / Socio")+Vcompany_address["msn"])

            Vpartner_address = self.validate_address(invoice.partner_id)
            if(bool(Vpartner_address["errors"])):
                raise Warning (str("Compañia emisora")+Vpartner_address["msn"])

            sunat_data = {
                                "serie": str(secuencia_serie),
                                "numero":str(secuencia_consecutivo),
                                "emisor":{
                                            "tipo_documento":invoice.company_id.sunat_tipo_documento,
                                            "nro":invoice.company_id.vat,
                                            "nombre":str(invoice.company_id.name).capitalize(),
                                            "direccion":str(invoice.company_id.street).capitalize(),
                                            "ciudad":str(Vcompany_address["address"]["province"]["name"]),
                                            "ciudad_sector":str(Vcompany_address["address"]["district"]["name"]),
                                            "departamento":str(invoice.company_id.state_id.name).capitalize(),
                                            "codigoPostal":invoice.company_id.zip,
                                            "codigoPais":invoice.company_id.country_id.code,
                                            "ubigeo":(str(invoice.company_id.ubigeo) if(str(invoice.company_id.ubigeo)!="") else str(invoice.company_id.zip))
                                        },
                                "receptor": {
                                                "tipo_documento":invoice.partner_id.sunat_tipo_documento,
                                                "nro":invoice.partner_id.vat,
                                                "nombre":str(invoice.partner_id.name).capitalize(),
                                                "direccion":str(invoice.partner_id.street).capitalize(),
                                                "ciudad":str(Vpartner_address["address"]["province"]["name"]),
                                                "ciudad_sector":str(Vpartner_address["address"]["district"]["name"]),
                                                "departamento":str(invoice.partner_id.state_id.name),
                                                "codigoPostal":invoice.partner_id.zip,
                                                "codigoPais":invoice.partner_id.country_id.code,
                                                "ubigeo":(str(invoice.partner_id.ubigeo) if(str(invoice.partner_id.ubigeo)!="") else str(invoice.partner_id.zip))
                                            },
                                "notaDescripcion":self.name,
                                "notaDiscrepanciaCode":self.discrepance_code,
                                "documentoOrigen":self.origin,
                                "documentoOrigenTipo": sunat_origin_document_type, #01 factura, 03 boleta, 12 tiket de venta
                                "fechaEmision":str(invoice.date_invoice).replace("/","-",3),
                                "fechaVencimiento":str(invoice.date_due).replace("/","-",3),
                                "horaEmision":currentTime,
                                "subTotalVenta":subTotalPedido,
                                "totalVentaGravada":totalVentaPedido,
                                "tipoMoneda":invoice.currency_id.name,
                                "items": sunat_items,
                                "tributos":tributos_globales,
                                "sunat_sol": {
                                                "ruc":invoice.company_id.sol_ruc,
                                                'usuario':invoice.company_id.sol_username,
                                                'clave':invoice.company_id.sol_password,
                                                'certificado':{
                                                                'crt':invoice.company_id.cert_pem_filename,
                                                                'key':invoice.company_id.key_pem_filename,
                                                                'pass':invoice.company_id.key_pass,
                                                              }
                                             },
                                "accion": processInvoiceAction,
                                'licencia':"081OHTGAVHJZ4GOZJGJV"
                            }

            #with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
            #        json.dump(sunat_data, outfile)
            
            #raise Warning("Generado")
            serieParts = str(invoice.number).split("-")             
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]
            currentDateTime = datetime.now()
            currentTime = currentDateTime.strftime("%H:%M:%S")

            xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
            
            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            SunatService.fileName = str(invoice.company_id.vat)+"-08-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
            SunatService.initSunatAPI(invoice.company_id.api_mode, "sendBill")
            SunatResponse = SunatService.processDebitNote(sunat_data)
            
            # save xml documents steps for reference in edocs
            if 'xml_response' in SunatResponse:
                self.response_document = SunatResponse["xml_response"]
                self.response_document_filename = str("R_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

            if 'xml_signed' in SunatResponse:
                self.signed_document = SunatResponse["xml_signed"]
                self.signed_document_filename = str("F_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

            if 'xml_unsigned' in SunatResponse:
                self.unsigned_document = SunatResponse["xml_unsigned"]
                self.unsigned_document_filename = str("NF_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")
            
            # generate qr for invoices and tickets in pos
            base_url = request.env['ir.config_parameter'].get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            qr = qrcode.QRCode(
                                version=1,
                                error_correction=qrcode.constants.ERROR_CORRECT_L,
                                box_size=20,
                                border=4,
                              )

            total_tributo_igv = self.get_sumatoria_tributo_igv(tributos_globales)            
            qr_code_text = str(sunat_data["emisor"]["nro"]) + str("|") + str(sunat_data["emisor"]["tipo_documento"]) + str("|") + str(sunat_data["serie"]) + str("|") + str(sunat_data["numero"]) + str("|") + str(total_tributo_igv) + str("|") + str(format(float(sunat_data["totalVentaGravada"]),'.2f')) + str("|") + str(sunat_data["fechaEmision"]) + str("|") + str(sunat_data["receptor"]["tipo_documento"]) + str("|") + str(sunat_data["receptor"]["nro"])
            qr.add_data(qr_code_text)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            self.qr_image = base64.b64encode(temp.getvalue())
            self.qr_in_report = True

            self.sunat_request_type = sunat_request_type
            self.sunat_total_letters = self.literal_price(totalVentaPedido)
            
            if 'status' in SunatResponse:
                if(SunatResponse["status"] == "OK"): 
                    self.api_message = "ESTADO: "+str(SunatResponse["status"])+"\n"+"REFERENCIA: "+str(SunatResponse["body"]["referencia"]).replace("'",'"')+"\n"+" "+str(SunatResponse["body"]["description"]).replace("'",'"')
                    self.sunat_request_status = 'OK'
                    # raise Warning("OK")
                    return super(account_invoice, self).invoice_validate()
                else:
                    self.sunat_request_status = 'FAIL'
                    self.api_message = "ESTADO: "+str(SunatResponse["status"])+"\n"+" "+str(SunatResponse["body"])+"\n"+"CÓDIGO ERROR: "+str(SunatResponse["code"])
                    return super(account_invoice, self).invoice_validate()
            else:
                return super(account_invoice, self).invoice_validate()  
        
        else: 
            return super(account_invoice, self).invoice_validate()


    def can_create_notes(self):
        query = "select id, number from account_invoice where origin = '"+str(self.id)+"' and discrepance_code in ('01','02')"
        request.cr.execute(query)
        refund_invoice = request.cr.dictfetchone()
        if(refund_invoice):
            refund_invoice["found"] = True
        else: 
            refund_invoice = {}
            refund_invoice["found"] = False
        return refund_invoice     

    def restablecer_documento(self):

        if(self.sunat_request_status==str("OK")):
            raise Warning('El documento no puede ser regenerado porque ya ha sido aceptado esta correcto. Solo se permite las acciones de comunicación de baja y crear una rectificativa sobre este documento.')
        
        if(self.was_cancelled == str('OK')):
            raise Warning('El documento no puede ser regenerado porque tiene comunicado de baja.')

        response = self.can_create_notes()
        if(response["found"]==True):
            raise Warning('El documento no puede ser regenerado porque tiene nota de crédito.')

        self.state = "draft"
        self.api_message_baja_doc = "sin_baja"
        self.sunat_request_status = "No Emitido"
        self.api_message = "Documento contable sin emitir."
        self.discrepance_code = ""
        self.discrepance_text = ""
        self.unsigned_document = None
        self.unsigned_document_filename = ''
        self.signed_document = None
        self.signed_document_filename = ''
        self.response_document = None
        self.response_document_filename = ''
        self.qr_image = None

    def comunicacion_de_baja(self):
        if(self.was_cancelled == str('OK')):
            raise Warning('El documento ya tiene comunicacion de baja. Ver estado en pestaña SUNAT e-fact de este formulario para más información del comunicado.')
        try:
            xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
            sequence_cancel_edoc = self.env['ir.sequence'].next_by_code(str("CBAJA"))

            SunatService = Service()
            SunatService.setXMLPath(xmlPath)
            year = datetime.today().strftime('%Y')
            month = str(int(datetime.today().strftime('%m')))
            day = datetime.today().strftime('%d')
            SunatService.fileName = str(self.company_id.vat)+"-"+str(sequence_cancel_edoc)
            SunatService.initSunatAPI(self.company_id.api_mode, "sendSummary")

            serieParts = str(self.number).split("-")             
            serieConsecutivoString = serieParts[0]
            serieConsecutivo = serieParts[1]

            DocumentTypeCode = None
            if("F0" in self.number):
                DocumentTypeCode = str("01")
            if("BF" in  self.number):
                DocumentTypeCode = str("03")
            if("FD" in  self.number):
                DocumentTypeCode = str("08")
            if("FC" in  self.number):
                DocumentTypeCode = str("07")

            secuencia = str(self.number).split("-")
            secuencia_serie = secuencia[0]
            secuencia_consecutivo = secuencia[1] 

            fecha_comunicacion = datetime.today().strftime('%Y-%m-%d')

            # Start data validation
            Vcompany_address = self.validate_address(self.company_id)
            if(bool(Vcompany_address["errors"])==True):
                raise Warning (str("Compañia emisora")+Vcompany_address["msn"])

            Vcompany_certificate = self.validate_certificate(self.company_id)
            if(bool(Vcompany_certificate["errors"])==True):
                raise Warning (str("Compañia emisora")+Vcompany_certificate["msn"])

            Vpartner_address = self.validate_address(self.partner_id)
            if(bool(Vpartner_address["errors"])==True):
                raise Warning (str("Cliente / Socio")+Vpartner_address["msn"])
            
            processInvoiceAction = "fill_only"        
            sunat_request_type = self.company_id.sunat_request_type
            if(sunat_request_type=="automatic"):
                sunat_request_type = "Automatizada"
                processInvoiceAction = "fill_only"
            else:
                sunat_request_type = "Documento Validado"
                processInvoiceAction = "fill_submit"
                    

            sunat_data =   {
                                "document_id": str(sequence_cancel_edoc),
                                "reference":{
                                                'tipo_edoc':DocumentTypeCode,
                                                "serie": str(secuencia_serie),
                                                "numero":str(secuencia_consecutivo),
                                                "fecha_emision":str(self.date_invoice).replace("/","-",3),
                                                'motivo':str('Anulación del documento electrónico'),
                                            },                                                                
                                "fecha_comunicacion":str(fecha_comunicacion),                                
                                "emisor":{
                                            "tipo_documento":self.company_id.sunat_tipo_documento,
                                            "nro":self.company_id.vat,
                                            "nombre":str(self.company_id.name).capitalize(),
                                            "direccion":str(self.company_id.street).capitalize(),
                                            "ciudad":str(Vcompany_address["address"]["province"]["name"]),
                                            "ciudad_sector":str(Vcompany_address["address"]["district"]["name"]),
                                            "departamento":str(self.company_id.state_id.name).capitalize(),
                                            "codigoPostal":self.company_id.zip,
                                            "codigoPais":self.company_id.country_id.code,
                                            "ubigeo":(str(self.company_id.ubigeo) if(str(self.company_id.ubigeo)!="") else str(self.company_id.zip))
                                        },
                                "sunat_sol": {
                                                "ruc":self.company_id.sol_ruc,
                                                'usuario':self.company_id.sol_username,
                                                'clave':self.company_id.sol_password,
                                                'certificado':{
                                                                'crt':self.company_id.cert_pem_filename,
                                                                'key':self.company_id.key_pem_filename,
                                                                'pass':self.company_id.key_pass,
                                                            }
                                            },
                                "accion": processInvoiceAction,
                                'licencia':"081OHTGAVHJZ4GOZJGJV"
                            }

            SunatResponse = SunatService.processDocumentCancel(sunat_data)
            self.api_message_baja_doc = str(SunatResponse['body'])
            self.was_cancelled = str(SunatResponse['statusCode'])
        
        except Exception as e:
           exc_traceback = sys.exc_info()
           #with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
           #    json.dump(getattr(e, 'message', repr(e))+" ON LINE "+format(sys.exc_info()[-1].tb_lineno), outfile)

    def exist_main_tribute(self,tributos, tributo):
        if(tributos.__len__()>0):
            found = False
            for tributo_code in tributos:
                if(str(tributo_code) == tributo["codigo"]):
                    found = True
        else:
            found = False
        return found

    def exist_child_tribute(self,tributos, tributo):
        if(tributos.__len__()>0):
            found = False
            
            for tributo_code in tributos:
                if(str(tributo_code) == tributo["codigo"]):
                    for tributo_item_percent_differenced in tributos[str(tributo_code)]:                        
                        if(tributo_item_percent_differenced["porcentaje"] == tributo["porcentaje"]):
                            found = True
        else:
            found = False
        return found

    def add_global_tributes(self, item_tributos, tributos_globales):        
        if(item_tributos.__len__()>0):
            
            for item_tributo in item_tributos:
                tributo_global_nuevo = {
                                            "codigo":item_tributo["codigo"],
                                            "total_venta":item_tributo["total_venta"],
                                            "porcentaje":item_tributo["porcentaje"],
                                            "sumatoria":item_tributo["montoAfectacionTributo"],
                                            "tipo_calculo":item_tributo["tipo_calculo"]
                                        }

                if(self.exist_main_tribute(tributos_globales,item_tributo)==False):
                    tributos_globales.update({str(item_tributo["codigo"]):[]})                                               
                    tributos_globales[str(item_tributo["codigo"])].append(tributo_global_nuevo)

                else:
                    position_child_tribute = self.exist_child_tribute(tributos_globales, item_tributo)
                    if(position_child_tribute==False):
                        tributos_globales[str(item_tributo["codigo"])].append(tributo_global_nuevo)
                    else:
                        for tributo_item_percent_differenced in tributos_globales[str(item_tributo["codigo"])]:                        
                            if(tributo_item_percent_differenced["porcentaje"] == item_tributo["porcentaje"]):
                                tributo_global_update = {
                                                            "total_venta":(float(tributo_item_percent_differenced["total_venta"])+float(item_tributo["total_venta"])),                                                            
                                                            "sumatoria":(float(tributo_item_percent_differenced["sumatoria"])+float(item_tributo["montoAfectacionTributo"]))
                                                        }

                                tributo_item_percent_differenced.update(tributo_global_update)                      
        
        return tributos_globales
    
    def get_origin_document_journal_code(self, origin_number):
        query = "select account_invoice.journal_id, account_journal.code from account_invoice left join account_journal on account_invoice.journal_id = account_journal.id where account_invoice.number = '"+str(origin_number)+"'"
        request.cr.execute(query)
        account_journal = request.cr.dictfetchone()
        return account_journal["code"]

    def get_sunat_document_type(self, journal_code):
        if journal_code == "FAC" or journal_code == "INV":
            return str("01")
        if journal_code == "BOL":
            return str("03")
        if journal_code == "TCV":
            return str("12")


    def get_sunat_product_type_price(self, item_id):
        query = "select sunat_price_type from product_template where id = "+str(item_id)
        request.cr.execute(query)
        product = request.cr.dictfetchone()
        return product["sunat_price_type"]
    
    def get_sunat_product_code_classification(self, item_id):
        query = "select sunat_product_code from product_template where id = "+str(item_id)
        request.cr.execute(query)
        product = request.cr.dictfetchone()
        sunat_product_code_parts = str(product["sunat_product_code"]).split(" -- ")
        return sunat_product_code_parts[0]

    # validate address for company and partner
    def validate_address(self, res_model):
        province_id = res_model.province_id.id
        district_id = res_model.district_id.id
        response = {"errors":False,"msn":"", "address":{}}
        errors_msn = str("")

        if(int(province_id)>0):
            if(int(province_id)>0):
                # select district
                query = "select name, code, state_id, province_id from res_country_state where id = "+str(district_id)
                request.cr.execute(query)
                district = request.cr.dictfetchone()
                district["name"] = str(str(str(district["name"]).replace("(PE)","")).strip()).capitalize()

                # select state
                query = "select name, code from res_country_state where id = "+str(district["state_id"])
                request.cr.execute(query)
                state = request.cr.dictfetchone()
                state["name"] = str(str(str(state["name"]).replace("(PE)","")).strip()).capitalize()

                # select province
                query = "select name, code from res_country_state where id = "+str(district["province_id"])
                request.cr.execute(query)
                province = request.cr.dictfetchone()
                province["name"] = str(str(str(province["name"]).replace("(PE)","")).strip()).capitalize()
                
                address = {"province":province,"state":state,"district":district}
                response["address"] = address
            else:
                response["errors"] = True
                errors_msn = errors_msn + str(" \n - Seleccionar districto")
        else:
            response["errors"] = True
            errors_msn = errors_msn + str(" \n - Seleccionar provincia")
        
        if(bool(response["errors"])):
            response["msn"] = errors_msn
        
        return response
    
    def validate_certificate(self, _company):
        response = {"errors":False,"msn":""}
        errors_msn = str("")
        if(_company.cert_pem == None):
            errors_msn = str(errors_msn) + str(" \n- Certificado con extension .pem es requerido")
            response["errors"] = True
        if(_company.key_pem == None):
            errors_msn = str(errors_msn) + str(" \n- La clave privada con extension .pem es requerida")
            response["errors"] = True

        if(bool(response["errors"])):
            response["msn"] = errors_msn

        return response

    def isPosOrder(self,origin):
        query = "select id from pos_order where name = '"+str(origin).strip()+"'"
        request.cr.execute(query)
        pos_order = request.cr.dictfetchone()
        if(pos_order):
            return bool(True)
        else:
            return bool(False)   
    
    def literal_price(self, numero):
        indicador = [("",""),("MIL","MIL"),("MILLON","MILLONES"),("MIL","MIL"),("BILLON","BILLONES")]
        entero = int(numero)
        decimal = int(round((numero - entero)*100))
        #print 'decimal : ',decimal 
        contador = 0
        numero_letras = ""
        while entero >0:
            a = entero % 1000
            if contador == 0:
                en_letras = self.convierte_cifra(a,1).strip()
            else :
                en_letras = self.convierte_cifra(a,0).strip()
            if a==0:
                numero_letras = en_letras+" "+numero_letras
            elif a==1:
                if contador in (1,3):
                    numero_letras = indicador[contador][0]+" "+numero_letras
                else:
                    numero_letras = en_letras+" "+indicador[contador][0]+" "+numero_letras
            else:
                numero_letras = en_letras+" "+indicador[contador][1]+" "+numero_letras
            numero_letras = numero_letras.strip()
            contador = contador + 1
            entero = int(entero / 1000)
        numero_letras = (numero_letras+" con " + str(decimal) +"/100 SOLES").upper().replace(' /100','00/100').replace(' 0/100',' 00/100')
        return numero_letras
 
    def convierte_cifra(self, numero,sw):
            lista_centana = ["",("CIEN","CIENTO"),"DOSCIENTOS","TRESCIENTOS","CUATROCIENTOS","QUINIENTOS","SEISCIENTOS","SETECIENTOS","OCHOCIENTOS","NOVECIENTOS"]
            lista_decena = ["",("DIEZ","ONCE","DOCE","TRECE","CATORCE","QUINCE","DIECISEIS","DIECISIETE","DIECIOCHO","DIECINUEVE"),
                            ("VEINTE","VEINTI"),("TREINTA","TREINTA Y "),("CUARENTA" , "CUARENTA Y "),
                            ("CINCUENTA" , "CINCUENTA Y "),("SESENTA" , "SESENTA Y "),
                            ("SETENTA" , "SETENTA Y "),("OCHENTA" , "OCHENTA Y "),
                            ("NOVENTA" , "NOVENTA Y ")
                        ]
            lista_unidad = ["",("UN" , "UNO"),"DOS","TRES","CUATRO","CINCO","SEIS","SIETE","OCHO","NUEVE"]
            centena = int (numero / 100)
            decena = int((numero -(centena * 100))/10)
            unidad = int(numero - (centena * 100 + decena * 10))
            #print "centena: ",centena, "decena: ",decena,'unidad: ',unidad
        
            texto_centena = ""
            texto_decena = ""
            texto_unidad = ""
        
            #Validad las centenas
            texto_centena = lista_centana[centena]
            if centena == 1:
                if (decena + unidad)!=0:
                    texto_centena = texto_centena[1]
                else :
                    texto_centena = texto_centena[0]
        
            #Valida las decenas
            texto_decena = lista_decena[decena]
            if decena == 1 :
                texto_decena = texto_decena[unidad]
            elif decena > 1 :
                if unidad != 0 :
                    texto_decena = texto_decena[1]
                else:
                    texto_decena = texto_decena[0]
            #Validar las unidades
            #print "texto_unidad: ",texto_unidad
            if decena != 1:
                texto_unidad = lista_unidad[unidad]
                if unidad == 1:
                    texto_unidad = texto_unidad[sw]
        
            return "%s %s %s" %(texto_centena,texto_decena,texto_unidad)
    
    def get_unit_price(self, price_unit, quantity, item_tributos, price_included):
        total_tax_amount = float(0.0)

        #with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
        #    json.dump(item_tributos, outfile)

        for tribute in item_tributos:
            total_tax_amount += float(tribute['montoAfectacionTributo']) 


        price_unit = float(price_unit) * (float(total_tax_amount) / float(quantity))
        #rice_unit = float(price_unit) - float(tax_amount)
        return str(price_unit)
    
    def _generate_email_ubl_attachment(self):
        self.ensure_one()
        attachments = self.env['ir.attachment']
        if self.type not in ('out_invoice', 'out_refund'):
            return attachments
        if self.state not in ('open', 'paid'):
            return attachments
            
        ubl_filename = self.signed_document_filename
        xml_signed = self.get_ubl_signed_document()
        if(xml_signed):
            return self.env['ir.attachment'].with_context({}).create({
                'name': ubl_filename,
                'res_model': str(self._name),
                'res_id': self.id,
                'datas': xml_signed,
                'datas_fname': ubl_filename,
                'type': 'binary',
            })
        else:
            return None

    def get_ubl_signed_document(self):
        xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
        try:
            serieParts = str(self.number).split("-")
            if(len(serieParts)):
                serieConsecutivoString = serieParts[0]
                serieConsecutivo = serieParts[1]
                fileName = None
                if("F0" in serieConsecutivoString):
                    fileName = str(self.company_id.vat)+"-01-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
                if("BF" in serieConsecutivoString):
                    fileName = str(self.company_id.vat)+"-03-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
                if("FD" in serieConsecutivoString):
                    fileName = str(self.company_id.vat)+"-08-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
                if("FC" in serieConsecutivoString):
                    fileName = str(self.company_id.vat)+"-07-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)

                fileContents = open(xmlPath+'/XMLdocuments/3_signed/'+str(fileName)+".XML", "rb").read()
                encoded = base64.b64encode(fileContents)
                return encoded
            else:
                return None
        except Exception as e:
            exc_traceback = sys.exc_info()
            return None


    def get_sumatoria_tributo_igv(self, tributos_globales):
        igv_items = tributos_globales["1000"]
        total = 0.0
        for igv_item in igv_items:
            total += float(igv_item['sumatoria'])
        return format(float(total),'.2f')
