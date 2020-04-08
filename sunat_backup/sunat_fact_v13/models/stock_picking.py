from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.osv import osv
import json
import os
import qrcode
import base64
import random
from io import BytesIO
import requests 
import sys
from odoo.http import request

from sunatservice.sunatservice import Service

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    unsigned_document = fields.Binary(string="XML - No firmado", default=None, readonly=True, filename="unsigned_document_filename" ,filters='*.xml', type="xml")
    unsigned_document_filename = fields.Char(string="Unsigned Filename", invisible="1", default="unsigned.XML")

    signed_document = fields.Binary(string="XML - Firmado", default=None, readonly=True, filename="signed_document_filename" ,filters='*.xml', type="xml")
    signed_document_filename = fields.Char(string="Signed Filename", invisible="1", default="signed.XML")
    
    response_document = fields.Binary(string="XML - Respuesta", default=None, readonly=True, filename="response_document_filename",filters='*.xml', type="xml")
    response_document_filename = fields.Char(string="Response Filename", invisible="1", default="response.XML")

    api_message = fields.Text(name="api_message", string="Estado", default='Documento contable sin emitir.')
    
    sunat_request_type = fields.Text(name="sunat_request_type", default='Automatizada')
    sunat_request_status = fields.Text(name="sunat_request_status", default='No Emitido')

    qr_image = fields.Text(name="qr_image", default='')

    @api.multi
    def action_done(self):
        name = ''
        for pick in self:
            if pick.id:
                name = pick.name
                stocks_picking = self.env['stock.move.line'].search([('picking_id','=',pick.id)])

                
                items = []
                for stock_pick in stocks_picking:
                    #Getting company
                    company = self.env['res.company'].search([('id','=',int(pick.company_id))])
                    #company.name
                    #company.sol_ruc
                    #company.country_id.code
                    #company.street

                    #Getting partner
                    partner = self.env['res.partner'].search([('id','=',int(pick.partner_id))])
                    #partner.name
                    #partner.vat
                    #partner.country_id.code
                    #partner.street                                        

                    #Getting products
                    product = self.env['product.product'].search([('id','=',int(stock_pick.product_id))])
                    item = {
                               "id":str(stock_pick.product_id.id),
                               "nombre":str(product.name),
                               "cantidad":str(stock_pick.product_qty),
                               "unidadMedidaCantidad":str('ZZ'),
                           }
                    items.append(item)

                    #Getting carrier
                    carrier = self.env['delivery.carrier'].search([('id','=',int(pick.carrier_id))])
                    #carrier.ruc
                    #carrier.name

                    serieParts = str(pick.name).split("-")     
                    #disable for proveedores
                    if(serieParts[0]):                        
                        if("T" not in serieParts[0]): 
                            res = super(stock_picking, self).action_done()
                            for pick in self:
                                if pick.carrier_id:
                                    if pick.carrier_id.integration_level == 'rate_and_ship':
                                        pick.send_to_shipper()
                                    pick._add_delivery_cost_to_so()  
                            return res  

                    serieConsecutivoString = serieParts[0]
                    serieConsecutivo = serieParts[1]     

                    dateParts = str(pick.date).split(" ")

                    sunat_request_type = company.sunat_request_type 

                    if(sunat_request_type=="automatic"):
                        sunat_request_type = "Automatizada"  
                        processInvoiceAction = "fill_only"    
                    else:
                        sunat_request_type = "Documento Validado"
                        processInvoiceAction = "fill_submit"
                    
                    data = {
                                'serie': str(serieConsecutivoString),
                                "numero":str(serieConsecutivo),
                                "fechaEmision":str(dateParts[0]).replace("/","-",3),
                                "nota":str(pick.note),
                                "peso":str(pick.weight),
                                "emisor":{
                                            "id":company.id,
                                            "tipo":company.sunat_tipo_documento,
                                            "nro":company.vat,
                                            "nombre":company.name,
                                            "direccion":str(company.street).capitalize(),
                                            "codigoPais":company.country_id.code
                                         },
                                "receptor":{
                                                "id":partner.id,
                                                "tipo":partner.sunat_tipo_documento,
                                                "nro":partner.vat,
                                                "nombre":partner.name,
                                                "direccion":str(partner.street).capitalize(),
                                                "codigoPais":partner.country_id.code
                                            },
                                "ubigeo":{
                                            "origen":str((str(company.ubigeo) if(company.ubigeo!=False) else str(company.zip))),
                                            "destino":str((str(partner.ubigeo) if(partner.ubigeo!=False) else str(partner.zip))),
                                         },
                                "transportista":{
                                                    "nro":carrier.ruc,
                                                    "nombre":carrier.name
                                                },
                                "items":items, 
                                'sunat_sol':{
                                        "ruc":company.sol_ruc,
                                        'usuario':company.sol_username,
                                        'clave':company.sol_password,
                                        'certificado':{
                                                        'crt':company.cert_pem_filename,
                                                        'key':company.key_pem_filename,
                                                        'pass':company.key_pass,
                                                      }
                                      },
                                "accion": processInvoiceAction,
                                'licencia':"081OHTGAVHJZ4GOZJGJV"
                           }
                

                if(data['transportista']['nro']==False):
                    raise Warning('Debes establecer un transportista')

                if(data['receptor']['nro']==False):
                    raise Warning('Debes establecer un receptor')

                # Start data validation
                Vcompany_address = self.validate_address(company)
                if(bool(Vcompany_address["errors"])==True):
                    raise Warning (str("Compañia emisora")+Vcompany_address["msn"])

                Vcompany_certificate = self.validate_certificate(company)
                if(bool(Vcompany_certificate["errors"])==True):
                    raise Warning (str("Compañia emisora")+Vcompany_certificate["msn"])

                Vpartner_address = self.validate_address(partner)
                if(bool(Vpartner_address["errors"])==True):
                    raise Warning (str("Cliente / Socio")+Vpartner_address["msn"])

                xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
                SunatService = Service()
                SunatService.setXMLPath(xmlPath)
                SunatService.fileName = str(company.vat)+"-09-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)
                SunatService.initSunatAPI(company.api_mode, "sendBill")
                sunatResponse = SunatService.processDeliveryGuide(data)

                base_url = request.env['ir.config_parameter'].get_param('web.base.url')
                base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
                qr = qrcode.QRCode(
                                    version=1,
                                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                                    box_size=20,
                                    border=4,
                                )

                qr_code_text = str(data["emisor"]["nro"]) + str("|") + str(data["emisor"]["tipo_documento"]) + str("|") + str(data["serie"]) + str("|") + str(data["numero"])+ str("|") + str(data["fechaEmision"]) + str("|") + str(data["receptor"]["tipo_documento"]) + str("|") + str(data["receptor"]["nro"])
                qr.add_data(qr_code_text)
                qr.make(fit=True)
                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                self.qr_image = base64.b64encode(temp.getvalue())

                # save xml documents steps for reference in edocs
                if 'xml_response' in sunatResponse:
                    self.response_document = sunatResponse["xml_response"]
                    self.response_document_filename = str("R_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

                if 'xml_signed' in sunatResponse:
                    self.signed_document = sunatResponse["xml_signed"]
                    self.signed_document_filename = str("F_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

                if 'xml_unsigned' in sunatResponse:
                    self.unsigned_document = sunatResponse["xml_unsigned"]
                    self.unsigned_document_filename = str("NF_")+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

                self.sunat_request_type = sunat_request_type

                #with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                #    json.dump(sunatResponse, outfile)
                
                #raise Warning("TEST")

                #original code segment
                res = super(stock_picking, self).action_done()
                for pick in self:
                    if pick.carrier_id:
                        if pick.carrier_id.integration_level == 'rate_and_ship':
                            pick.send_to_shipper()
                        pick._add_delivery_cost_to_so()
                    
                if 'status' in sunatResponse:
                    self.attach_ubl()
                    if(sunatResponse["status"] == "OK"):
                        
                        self.sunat_request_status = 'OK'
                        self.api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+"REFERENCIA: "+str(sunatResponse["body"]["referencia"])+"\n"+" "+str(sunatResponse["body"]["description"])
                        return res
                    else:
                        self.sunat_request_status = 'FAIL'
                        errorMessage = "ESTADO: "+str(sunatResponse["status"])+"\n"+" "+str(sunatResponse["body"])+"\n"+"CÓDIGO ERROR: "+str(sunatResponse["code"])
                        self.api_message = errorMessage
                        raise Warning(errorMessage)
                else:
                    return res
                    
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
        
        if((res_model.zip==False and res_model.ubigeo==False)):
            errors_msn = errors_msn + str(" \n - Establecer código postal / ubigeo")
        
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

    def attach_ubl(self):
        try:
            self._generate_email_ubl_attachment()
            res_ids = [self.id]
            self.env['mail.template'].generate_email(res_ids)
        except Exception as e:
            exc_traceback = sys.exc_info()
            #with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
            #    json.dump(getattr(e, 'message', repr(e))+" ON LINE "+format(sys.exc_info()[-1].tb_lineno), outfile)

    def _generate_email_ubl_attachment(self):
        self.ensure_one()
        ubl_filename = self.signed_document_filename
        xml_signed = self.get_ubl_signed_document()
        try:
            if(xml_signed):
                return self.env['ir.attachment'].with_context({}).create({
                    'name': ubl_filename,
                    'res_model': str(self._name),
                    'res_id': self.id,
                    'datas': xml_signed,
                    'datas_fname': ubl_filename,
                    'type': 'binary',
                })
            #else:
            #    with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
            #        json.dump("XML SIGNED", outfile)
        except Exception as e:
            exc_traceback = sys.exc_info()
            #with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
            #    json.dump(getattr(e, 'message', repr(e))+" ON LINE "+format(sys.exc_info()[-1].tb_lineno), outfile)
            return None
        return None

    def get_ubl_signed_document(self):
        xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
        try:
            serieParts = str(self.name).split("-")
            if(len(serieParts)):
                serieConsecutivoString = serieParts[0]
                serieConsecutivo = serieParts[1]
                fileName = None
                if("T0" in serieConsecutivoString):
                    fileName = str(self.company_id.vat)+"-09-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)

                fileContents = open(xmlPath+'/XMLdocuments/3_signed/'+str(fileName)+".XML", "rb").read()
                encoded = base64.b64encode(fileContents)
                return encoded
            else:
                return None
        except Exception as e:
            exc_traceback = sys.exc_info()
            #with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
            #    json.dump(getattr(e, 'message', repr(e))+" ON LINE "+format(sys.exc_info()[-1].tb_lineno), outfile)
            return None

