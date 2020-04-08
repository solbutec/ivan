# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import Warning
import os, json, sys, base64
from datetime import datetime
from odoo.http import request
import xlrd
from sunatservice.sunatservice import Service

class SunatEfact(http.Controller):

    @http.route('/sunatefact/set_partner_location/', methods=['POST'], type='json', auth="public", website=True)
    def set_partner_location(self, **kw):
        partner_id = kw.get('id')
        response = {"partner":None}
        if(int(partner_id)>0):
            query = "select state_id, province_id, district_id from res_partner where id = "+str(partner_id)
            request.cr.execute(query)
            partner = request.cr.dictfetchone()
            response["partner"] = partner

        return response

    @http.route('/sunatefact/populate_location/', methods=['POST'], type='json', auth="public", website=True)
    def populate_location(self, **kw):
        country_id = kw.get('country_id') 
        state_id = kw.get('state_id') 
        province_id = kw.get('province_id') 
        district_id = kw.get('district_id') 
        
        response = {"country_id":country_id,"states":None, "provinces":None, "districts":None}

        if(int(country_id)>0):
            query = "select id, name, code from res_country_state where length(code) = 2 and country_id = "+str(country_id)
            #return query
            request.cr.execute(query)
            country_states = request.cr.dictfetchall()
            response["states"] = country_states
        
        if(int(state_id)>0):
            query = "select id, name, code from res_country_state where length(code) = 4 and country_id = " + str(country_id) + " and state_id = " + str(state_id)
            #return query
            request.cr.execute(query)
            state_provinces = request.cr.dictfetchall()
            response["provinces"] = state_provinces
        
        if(int(province_id)>0):
            query = "select id, name, code from res_country_state where length(code) = 6 and country_id = " + str(country_id) + " and state_id = " + str(state_id) + " and province_id = " + str(province_id)
            request.cr.execute(query)
            province_districts = request.cr.dictfetchall()
            response["districts"] = province_districts

        return response
    
    @http.route('/sunatefact/set_location/', methods=['POST'], type='json', auth="public", website=True)
    def set_location(self, **kw):
        country_id = kw.get('country_id')
        state_name = kw.get('state')
        province_name = kw.get('province')
        district_name = kw.get('district')
        ubigeo_code = kw.get('ubigeo')
        
        response = {"state":0,"province":0,"district":0}
        if(int(country_id)>0):
            query = "select id, name, code from res_country_state where length(code) = 2 and country_id = "+str(country_id)+" and  name = '"+ str(state_name)+"'"
            request.cr.execute(query)
            state = request.cr.dictfetchone()
            response["state"] = state

            query = "select id, name, code from res_country_state where length(code) = 4 and country_id = "+str(country_id)+" and  name = '"+ str(province_name)+"'"
            request.cr.execute(query)
            province = request.cr.dictfetchone()
            response["province"] = province

            #with open('/odoo_peru_sunat/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
            #    json.dump(query, outfile)

            query = "select id, name, code from res_country_state where length(code) = 6 and country_id = "+str(country_id)+" and  code = '"+ str(ubigeo_code)+"'"
            request.cr.execute(query)
            district = request.cr.dictfetchone()
            if(district):
                response["district"] = district
            else:
                query = "insert into res_country_state (name,code,country_id,state_id,province_id) values('"+str(district_name)+"','"+str(ubigeo_code)+"',"+str(country_id)+","+str(state['id'])+","+str(province['id'])+")"
                request.cr.execute(query)
                #response["district"] = query 
                
                query = "select id, name, code from res_country_state where length(code) = 6 and country_id = "+str(country_id)+" and  code = '"+ str(ubigeo_code)+"'"
                request.cr.execute(query)
                district = request.cr.dictfetchone()
                response["district"] = district

        return response            

    @http.route('/sunatefact/get_ruc/', methods=['POST'], type='json', auth="public", website=True)
    def get_ruc(self, **kw):
        doc_num = kw.get('doc_num')
        doc_type = kw.get('doc_type')
        xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
        xmlPath = xmlPath.replace("controllers", "models")
        response = {'status' :  "El documento no fue encontrado."}
        try:
            if(doc_num!=""):
                SunatService = Service()
                SunatService.setXMLPath(xmlPath)
                response_service = SunatService.consultRUC_Pydevs(doc_type, doc_num)
                if len(response_service['data'])>0:
                    if(int(doc_type)==6):

                        query = "select id, name, code from res_country_state where length(code) = 6 and country_id = "+str(173)+" and  name like'%"+ str(response_service["data"]['distrito'])+"%'"
                        request.cr.execute(query)
                        district = request.cr.dictfetchone()
                        ubigeo = str("")
                        if(district):
                            ubigeo = district["code"]

                        nombre = str(response_service["data"]['nombre']).capitalize().replace('"','').strip()
                        nombre_comercial = str(response_service["data"]['nombre_comercial']).capitalize().replace('"','').strip()
                        nombre_comercial_tmp = nombre_comercial
                        nombre_comercial = nombre  + nombre_comercial if nombre_comercial != "-" else ""
                        name = str(nombre) if str(nombre_comercial_tmp) == str("-") else str(nombre) + str(" -- ") + str(nombre_comercial_tmp)
                        response = {
                                        'status' :  "OK",
                                        'nmro':doc_num,
                                        'address' : str(response_service["data"]['domicilio_fiscal']).capitalize(),
                                        'name' : name,
                                        'tipo_contribuyente' : response_service["data"]['tipo_contribuyente'],
                                        'nombre_comercial' : nombre_comercial,
                                        'sistema_emision_comprobante' : str(response_service["data"]['sistema_emision_comprobante']).capitalize(),
                                        'sistema_contabilidad' : str(response_service["data"]['sistema_contabilidad']).capitalize(),
                                        'actividad_economica' :  str(response_service["data"]['actividad_economica']).capitalize(),
                                        'estado_contribuyente' : str(response_service["data"]['estado_contribuyente']).capitalize(),
                                        'condicion_contribuyente' : str(response_service["data"]['condicion_contribuyente']).capitalize(),
                                        'distrito' : response_service["data"]['distrito'],
                                        'provincia' : response_service["data"]['provincia'],
                                        'departamento' : response_service["data"]['departamento'],
                                        'ubigeo' : ubigeo
                                    }
                if(int(doc_type)==1):
                    response =  {
                                    'status' :  "OK",
                                    'nmro' :  doc_num,
                                    'name' :  str(str(response_service["data"]['nombres']) +str(" ")+ str(response_service["data"]['ape_paterno']) +str(" ")+ str(response_service["data"]['ape_materno'])).capitalize()
                                }

        except Exception as e:
            exc_traceback = sys.exc_info()
            #with open('/home/rockscripts/Documentos/log_.js', 'w') as outfile:
            #    json.dump(getattr(e, 'message', repr(e))+" ON LINE "+format(sys.exc_info()[-1].tb_lineno), outfile)
            return {'status' :  "FAIL"}

        return response
        
        # don't let create notes over an invoice if a credit note exists with discrepance code equals 2 = Anulacion de la factura
    @http.route('/sunatefact/can_create_notes/', methods=['POST'], type='json', auth="public", website=True)
    def can_create_notes(self, **kw):
        invoice_number = kw.get('invoice_number')
        query = "select id, number from account_invoice where origin = '"+str(invoice_number)+"' and discrepance_code in ('01','02')"
        request.cr.execute(query)
        refund_invoice = request.cr.dictfetchone()
        if(refund_invoice):
            refund_invoice["found"] = True
        else: 
            refund_invoice = {}
            refund_invoice["found"] = False
        return refund_invoice
    
    @http.route('/sunatefact/get_invoice_qr/', methods=['POST'], type='json', auth="public", website=True)
    def get_invoice_qr(self, **kw):
        orderReference = kw.get('orderReference')

        query = "select invoice_id from pos_order where pos_reference = '"+str(orderReference)+"'"

        request.cr.execute(query)
        pos_sale = request.cr.fetchone()
        invoice_id = pos_sale[0]

        query = "select qr_image from account_invoice where id = "+str(invoice_id)
        request.cr.execute(query)    
        account_invoice = request.cr.fetchone()
        qr_image = account_invoice[0]
        return qr_image
    
    @http.route('/sunatefact/get_invoice_ordered/', methods=['POST'], type='json', auth="public", website=True)
    def get_invoice_ordered(self, **kw):
        orderID = kw.get('orderID')
        orderID = str(orderID).replace("c","")
        response = {}
        query = "select invoice_id from pos_order where pos_reference = '"+str(orderID)+"'"
        
        request.cr.execute(query)    
        pos_sale = request.cr.dictfetchone()
        
        try:

            invoice_id = pos_sale['invoice_id']
            query = "select id, qr_image, number, journal_id, amount_total from account_invoice where id = "+str(invoice_id)
            request.cr.execute(query)    
            account_invoice = request.cr.dictfetchone()

            query = "select name from account_journal where id = "+str(account_invoice['journal_id'])
            request.cr.execute(query)    
            account_journal = request.cr.dictfetchone()

            total_letters = self.literal_price(account_invoice['amount_total'])

            response = {"inv_id":account_invoice['id'],"number":account_invoice['number'],"qr_image":account_invoice['qr_image'],"journal_name":account_journal['name'],"total_letters":total_letters}
            
        except Exception as e:
            exc_traceback = sys.exc_info()
            #with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
            #    json.dump(getattr(e, 'message', repr(e))+" ON LINE "+format(sys.exc_info()[-1].tb_lineno), outfile)
        
        return response

    @http.route('/sunatefact/get_invoice_ticket_journal/', methods=['POST'], type='json', auth="public", website=True)
    def get_invoice_ticket_journal(self, **kw):
        response = {}
        uid = http.request.env.context.get('uid')

        query = "select id, name from account_journal where code in ('INV','FAC','BOL')"
        request.cr.execute(query)    
        journals = request.cr.dictfetchall()
        response["journals"] = journals

        
        query = "select pos_config.id, pos_config.invoice_journal_id from pos_config inner join pos_session on pos_session.user_id = "+str(uid)+" and state = 'opened'"
        request.cr.execute(query)    
        pos_config = request.cr.dictfetchone()
        response["pos_config"] = pos_config
                
        return response

    @http.route('/sunatefact/update_current_pos_conf/', methods=['POST'], type='json', auth="public", website=True)
    def update_current_pos_conf(self, **kw):

        posID = kw.get('posID')
        journalID = kw.get('journalID')
        response = {}

        query = "update pos_config set invoice_journal_id = "+str(journalID)+" where id = "+posID
        request.cr.execute(query) 
                
        return True

    @http.route('/sunatefact/populate_representants_list/', methods=['POST'], type='json', auth="public", website=True)
    def populate_representants_list(self, **kw):        
        query = "select * from res_representants"
        request.cr.execute(query) 
        representants = request.cr.dictfetchall() 
        return representants

    @http.route('/sunatefact/save_representants/', methods=['POST'], type='json', auth="public", website=True)
    def save_representants(self, **kw):
        
        id_representant = kw.get('id_representant')
        id_company = kw.get('id_company')
        doc_type = kw.get('doc_type')
        doc_number = kw.get('doc_number')
        name = kw.get('name')
        position = kw.get('position')
        address = kw.get('address')

        currentDateTime = datetime.now()
        date_added = currentDateTime#currentDateTime.strftime("%H:%M:%S")

        if(int(id_representant)==0):
            params = {}
            params ["search_type"] = "check_exist"
            params ["id_company"] = id_company
            params ["doc_number"] = doc_number
            params ["doc_type"] = doc_type
            representant = self.get_representant(params)
            if(representant):
                return False
            else:
                query = "insert into res_representants (id_company, doc_type, doc_number, name, position, address, date_added) values ('"+str(doc_type)+"', '"+str(doc_type)+"', '"+str(doc_number)+"', '"+str(name)+"', '"+str(position)+"', '"+str(address)+"', '"+str(date_added)+"')"
        else:
            query = "update res_representants set doc_type='"+str(doc_type)+"', doc_number='"+str(doc_number)+"', name='"+str(name)+"', position='"+str(position)+"', address='"+str(address)+"' where id='"+str(id_representant)+"'"

        request.cr.execute(query)
        return True

    @http.route('/sunatefact/get_representant/', methods=['POST'], type='json', auth="public", website=True)
    def get_representant(self,data):
        if (data["search_type"]=="check_exist"):
            query = "select * from res_representants where id_company='"+str(data["id_company"])+"' and doc_number = '"+str(data["doc_number"])+"' and doc_type = '"+str(data["doc_type"])+"'"
        else:
            query = "select * from res_representants where id = "+int(data["id_representant"])
        request.cr.execute(query)
        representant = request.cr.dictfetchone()
        return representant

    @http.route('/sunatefact/remove_representant/', methods=['POST'], type='json', auth="public", website=True)
    def remove_representant(self, **kw):  
        id_representant = kw.get('id_representant')    
        query = "delete from res_representants where id="+str(id_representant)
        request.cr.execute(query)
        return True

    @http.route('/dianefact/eguide_submit_single/', methods=['POST'], type='json', auth="public", website=True)
    def eguide_submit_single(self, **kw):
        stock_picking_id = kw.get('stock_picking_id') 
        
        query = "select name, company_id, unsigned_document, signed_document, response_document from stock_picking where id = "+str(stock_picking_id)
        request.cr.execute(query)
        stock_picking = request.cr.dictfetchone()
        
        query = "select res_partner.vat, res_company.api_mode, res_company.sol_ruc, res_company.sol_username, res_company.sol_password, res_company.certs from res_company left join res_partner on res_partner.company_id = res_company.id where res_company.id = "+str(stock_picking['company_id'])+" and res_partner.is_company = TRUE and res_company.partner_id = res_partner.id"
        request.cr.execute(query)
        company_fields = request.cr.dictfetchone()        

        serieParts = str(stock_picking["name"]).split("-")             
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
                                        #"signed":base64.b64decode((stock_picking["signed_document"]))
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
        

        if ('status' in sunatResponse):
            if(sunatResponse["status"] == "OK"):
                # save xml documents steps for reference in edocs
                response_document_filename = str("R_")+"-09-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

                api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+"REFERENCIA: "+str(sunatResponse["body"]["referencia"]).replace("'",'"')+"\n"+" "+str(sunatResponse["body"]["description"]).replace("'",'"')
                query = "update stock_picking set sunat_request_status = 'OK', api_message = '"+str(api_message)+"', response_document_filename = '"+str(response_document_filename)+"', sunat_request_type = 'Manual' where id = "+str(stock_picking_id)
                request.cr.execute(query)

                #if(serieConsecutivo=="00000008"):
                #    with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                #        json.dump(query, outfile)

            else:
                api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+" "+str(sunatResponse["body"]).replace("'",'"')+"\n"+"CÓDIGO ERROR: "+str(sunatResponse["code"]).replace("'",'"')
                query = "update stock_picking set sunat_request_status = 'FAIL', api_message = '"+str(api_message)+"', sunat_request_type = 'Manual' where id = "+str(stock_picking_id)
                request.cr.execute(query)

                #if(serieConsecutivo):
                #    with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
                #        json.dump(serieConsecutivo, outfile)     

        else:
            sunatResponse["status"] = "FAIL"
            api_message = "Servidor no disponible temporalmente."
            query = "update stock_picking set sunat_request_status = 'FAIL', api_message = '"+str(api_message)+"', sunat_request_type = 'Manual' where id = "+str(stock_picking_id)
            request.cr.execute(query)

        response = {
                        "sunat_request_status":sunatResponse["status"],
                        "api_message":api_message
                   }

        return response       

    @http.route('/dianefact/edocs_submit_invoice/', methods=['POST'], type='json', auth="public", website=True)
    def edocs_submit_invoice(self, **kw):
        #self.update_inv()
        #return None
        invoice_id = kw.get('invoice_id') 
        
        query = "select number, company_id, unsigned_document, signed_document, response_document from account_invoice where id = "+str(invoice_id)
        request.cr.execute(query)
        invoice_fields = request.cr.dictfetchone()
        
        query = "select res_partner.vat, res_company.api_mode, res_company.sol_ruc, res_company.sol_username, res_company.sol_password, res_company.certs from res_company left join res_partner on res_partner.company_id = res_company.id where res_company.id = "+str(invoice_fields['company_id'])+" and res_partner.is_company = TRUE and res_company.partner_id = res_partner.id"
        request.cr.execute(query)
        company_fields = request.cr.dictfetchone()        

        serieParts = str(invoice_fields["number"]).split("-")             
        serieConsecutivoString = serieParts[0]
        serieConsecutivo = serieParts[1]

        sunat_data = {
                            "secuencia_consecutivo":serieConsecutivo,
                            "numero":serieConsecutivo,
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
        
        try:
            if ('status' in sunatResponse):
                if(sunatResponse["status"] == "OK"):
                    # save xml documents steps for reference in edocs
                    response_document_filename = str("R_")+"-01-"+str(serieConsecutivoString)+"-"+str(serieConsecutivo)+str(".XML")

                    api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+"REFERENCIA: "+str(sunatResponse["body"]["referencia"]).replace("'",'"')+"\n"+" "+str(sunatResponse["body"]["description"]).replace("'",'"')
                    query = "update account_invoice set sunat_request_status = 'OK', api_message = '"+str(api_message)+"', response_document_filename = '"+str(response_document_filename)+"', sunat_request_type = 'Manual' where id = "+str(invoice_id)
                    request.cr.execute(query)

                    response = {
                                "sunat_request_status":sunatResponse["status"],
                                "api_message":api_message
                                }

                else:
                    api_message = "ESTADO: "+str(sunatResponse["status"])+"\n"+" "+str(sunatResponse["body"]).replace("'",'"')+"\n"+"CÓDIGO ERROR: "+str(sunatResponse["code"]).replace("'",'"')
                    query = "update account_invoice set sunat_request_status = 'FAIL', api_message = '"+str(api_message)+"', sunat_request_type = 'Manual' where id = "+str(invoice_id)
                    request.cr.execute(query)
                    response = {
                                "sunat_request_status":sunatResponse["status"],
                                "api_message":api_message
                                }    

            else:
                sunatResponse["status"] = "FAIL"
                api_message = "Servidor no disponible temporalmente."
                query = "update account_invoice set sunat_request_status = 'FAIL', api_message = '"+str(api_message)+"', sunat_request_type = 'Manual' where id = "+str(invoice_id)
                request.cr.execute(query)

                response = {
                            "sunat_request_status":sunatResponse["status"],
                            "api_message":api_message
                        }

            return response
        except Exception as e:
            exc_traceback = sys.exc_info()
            #with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
            #    json.dump(getattr(e, 'message', repr(e))+" ON LINE "+format(sys.exc_info()[-1].tb_lineno), outfile)

    
    @http.route('/sunatefact/get_segments/', methods=['POST'], type='json', auth="public", website=True)
    def get_segments(self, **kw):
        segments_selection = [] 
        if(self.check_model_table('sunat_productcodes')):
            if(self.check_data_table('sunat_productcodes')):       
                query = "select segment_code, segment_name from sunat_productcodes group by segment_code, segment_name order by segment_code asc"                
                request.cr.execute(query)
                segments = request.cr.dictfetchall()
                for segment in segments: 
                    segments_selection.append((segment['segment_code'], segment['segment_name']))
            else:
                self.install_product_codes_data()
        else:
            self.install_product_codes_data()
        return segments_selection

    @http.route('/sunatefact/get_families/', methods=['POST'], type='json', auth="public", website=True)
    def get_families(self, **kw):
        families_selection = []
        segment_code = kw.get('segment_code')         
        query = "select family_code, family_name from sunat_productcodes where segment_code = '"+str(segment_code)+"' group by family_code, family_name order by family_code asc"                
        request.cr.execute(query)
        families = request.cr.dictfetchall()
        for family in families: 
            families_selection.append((family['family_code'], family['family_name']))
        return families_selection
    
    @http.route('/sunatefact/get_clases/', methods=['POST'], type='json', auth="public", website=True)
    def get_clases(self, **kw):
        classes_selection = []
        family_code = kw.get('family_code')         
        query = "select clase_code, clase_name from sunat_productcodes where family_code = '"+str(family_code)+"' group by clase_code, clase_name order by clase_code asc"                
        request.cr.execute(query)
        classes = request.cr.dictfetchall()
        for family in classes: 
            classes_selection.append((family['clase_code'], family['clase_name']))
        return classes_selection
    
    @http.route('/sunatefact/get_products/', methods=['POST'], type='json', auth="public", website=True)
    def get_products(self, **kw):
        products_selection = []
        class_code = kw.get('class_code')         
        query = "select product_code, product_name from sunat_productcodes where clase_code = '"+str(class_code)+"' group by product_code, product_name order by product_code asc"                
        request.cr.execute(query)
        products = request.cr.dictfetchall()
        for product in products: 
            products_selection.append((product['product_code'], product['product_name']))
        return products_selection

    def install_product_codes_data(self):
        product_codes = self.get_tribute_entity_product_code()
        for product_code in product_codes:            
            query = "insert into sunat_productcodes (segment_code, segment_name, family_code, family_name, clase_code, clase_name, product_code, product_name) values ('"+str(product_code[0])+"','"+str(product_code[1]).replace("'","`")+"','"+str(product_code[2])+"','"+str(product_code[3]).replace("'","\'")+"','"+str(product_code[4])+"','"+str(product_code[5]).replace("'","`")+"','"+str(product_code[6])+"','"+str(product_code[7]).replace("'","`")+"')"                        
            request.cr.execute(query)

    def get_tribute_entity_product_code(self):
        xmlPath = os.path.dirname(os.path.abspath(__file__))+'/data/product_codes.xls'
        loc = (xmlPath) 
        
        wb = xlrd.open_workbook(loc) 
        sheet = wb.sheet_by_index(0) 
        
        # For row 0 and column 0 
        sheet.cell_value(5, 0)
        row_cells = [] 
        for j in range(sheet.nrows):
            if(j>3):
                row_cell = [] 
                for i in range(sheet.ncols): 
                    # 0 - segment cod
                    # 1 - segment name
                    # 2 - family cod
                    # 3 - family name
                    # 4 - clase cod
                    # 5 - clase name
                    # 6 - product cod
                    # 7 - product name
                    if(i==0 or i == 2 or i == 4 or i == 6):
                        row_cell.append(int(sheet.cell_value(j, i)))
                    else:
                        row_cell.append(str(sheet.cell_value(j, i)))
                row_cells.append(row_cell)

        return (row_cells)

    def check_model_table(self, tablename):
        request.cr.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = '{0}'
            """.format(tablename.replace('\'', '\'\'')))
        if request.cr.fetchone()[0] == 1:
            return True
        return False
    
    def check_data_table(self, tablename):
        request.cr.execute("""
            SELECT COUNT(*)
            FROM {0}
            """.format(tablename.replace('\'', '\'\'')))
        if request.cr.fetchone()[0] > 0:
            return True
        return False
    
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

    def update_inv(self, **kw):
        query = "select id, number, origin, move_name, reference from account_invoice where number != ''"
        request.cr.execute(query)
        invoices = request.cr.dictfetchall()
        strQ = str("")
        try:
            for invoice in invoices:
                move_name = str(invoice['move_name']).replace(str(invoice['number']),str(invoice['origin']))
                refer = str(invoice['reference']).replace(str(invoice['number']),str(invoice['origin']))
                query = "update account_invoice set number = '"+str(invoice['origin'])+"', move_name='"+str(move_name)+"' , reference='"+str(refer)+"' where id = "+str(invoice['id'])+str(";")              
                strQ = str(strQ) + str('\n') + str(query)
                #request.cr.execute(query)
               
        except Exception as e:
            exc_traceback = sys.exc_info()
            #with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
            #    json.dump(getattr(e, 'message', repr(e))+" ON LINE "+format(sys.exc_info()[-1].tb_lineno), outfile)
            response = {}
        
        with open('/odoo_sunatperu/custom/addons/sunat_fact/models/log.json', 'w') as outfile:
                json.dump(strQ, outfile)
