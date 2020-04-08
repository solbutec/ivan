# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning
from pprint import pprint
import importlib
import os
import base64, json, sys
from sunatservice.sunatservice import Service

class res_company(models.Model):  
        
    _inherit = 'res.company'
    sunat_tipo_documento = fields.Selection([('6','RUC'),('1','DNI'),('4','Carnet extrangeria'),('7','Pasaporte'),('A','CED. DIPLOMATICA DE IDENTIDAD'),('B','DOC.IDENT.PAIS.RESIDENCIA-NO.D'),('C','Tax Identification Number - TIN – Doc Trib PP.NN'),('D','Identification Number - IN – Doc Trib PP. JJ')], string='Tipo Documento', default='6')
    sol_ruc = fields.Text(name="sol_ruc", string="RUC", default='20603408111')
    sol_username = fields.Text(name="sol_username", string="Usuario", default='20603408111MODDATOS')
    sol_password = fields.Text(name="sol_password", string="Contraseña", default='moddatos')
    api_mode = fields.Selection([('SANDBOX','SANDBOX'),('PRODUCTION','PRODUCTION')], string='Modo Servicio', default='SANDBOX')
    certs = fields.Selection([('cert_1','Cert 1'),('cert_2','Cert 2')], string='Certificado', default='cert_1')
    ubigeo = fields.Char('Ubicación Geográfica', translate=True)    
    sunat_request_type = fields.Selection([('automatic','Automatizada'),('validated','Documento Validado')], string='Tipo de Emisión', default='automatic')

    cert_pem = fields.Binary(string="Certificado (PEM)",filename="cert_pem_filename" ,filters='*.pem', type="pem")
    cert_pem_filename = fields.Char(string="Certificado (PEM)", invisible="1", default="rsacert.pem")
    key_pem = fields.Binary(string="Clave Privada (PEM)",filename="key_pem_filename" ,filters='*.pem', type="pem")
    key_pem_filename = fields.Char(string="Clave Privada (PEM)", invisible="1", default="rsakey.pem")
    key_pass = fields.Char(string="Contraseña", default="")

     # Based on odoo_ruc_vat_validation addon solution by py-dev.com
    @api.onchange('vat')
    def on_change_vat(self): 
        xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
        for record in self:
            if (record.vat) :
                ruc = record.vat
                tipo_documento = record.sunat_tipo_documento
                if(ruc!=""):
                    SunatService = Service()
                    SunatService.setXMLPath(xmlPath)
                    response = {}
                    response = SunatService.consultRUC_Pydevs(tipo_documento,ruc)
                    if len(response['data'])==0:
                        raise Warning("El RUC no fue encontrado en registros de SUNAT")
                    else:
                        
                        self.update_document(response)
    
    @api.one
    def update_document(self, response):
        if not self.vat:
            return False
        if self.sunat_tipo_documento and self.sunat_tipo_documento == '1':
           #Valida DNI
            if self.vat and len(self.vat) != 8:
                raise Warning('El Dni debe tener 8 caracteres')
            else:
                d = response
                if not d['error']:
                    d = d['data']
                    self.name = '%s %s %s' % (d['nombres'],
                                               d['ape_paterno'],
                                               d['ape_materno'])

        elif self.sunat_tipo_documento and self.sunat_tipo_documento == '6':
            # Valida RUC
            if self.vat and len(self.vat) != 11:
                raise Warning('El Ruc debe tener 11 caracteres')
            else:
                d = response
                if d['error']:
                    return True
                d = d['data']
                #~ Busca el distrito
                ditrict_obj = self.env['res.country.state']
                prov_ids = ditrict_obj.search([('name', '=', d['provincia']),
                                               ('province_id', '=', False),
                                               ('state_id', '!=', False)])
                dist_id = ditrict_obj.search([('name', '=', d['distrito']),
                                              ('province_id', '!=', False),
                                              ('state_id', '!=', False),
                                              ('province_id', 'in', [x.id for x in prov_ids])], limit=1)
               
            
                self.name = str(d['nombre']).capitalize() if d['nombre_comercial'] == '-' else str(d['nombre']).capitalize() + str(d['nombre_comercial']).capitalize()
                #self.registration_name = d['nombre']
                self.street = d['domicilio_fiscal']
                self.is_company = True
                self.ubigeo = d['ubigeo']
                self.zip = d['ubigeo']
                self.city = d['distrito']

                if dist_id:
                    self.district_id = dist_id.id
                    self.province_id = dist_id.province_id.id
                    self.state_id = dist_id.state_id.id
                    self.country_id = dist_id.country_id.id
        else:
            True
    # @api.onchange('vat')
    # def on_change_vat(self): 
    #     #raise Warning("El RUC no fue encontrado en registros de SUNAT")
    #     xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
    #     for record in self:
    #         if (record.vat) :
    #             ruc = record.vat
    #             if(ruc!=""):
    #                 SunatService = Service()
    #                 SunatService.setXMLPath(xmlPath)
    #                 response = {}
    #                 response = SunatService.consultRUC(ruc)
    #                 if not response:
    #                     raise Warning("El RUC no fue encontrado en registros de SUNAT")
    #                 else:
    #                     self.street = response['address']
    #                     self.name = response["name"]

    @api.model
    def get_current_id(self):
        return self.env.context.get('active_ids', [])

    @api.onchange('cert_pem')
    def _upload_certificate_to_server(self):
        xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
        self.cert_pem_filename = "rsacert.pem"
        crtTarget = str(xmlPath+'/XMLcertificates/')+str(self.cert_pem_filename)
        crtTargetDir = str(xmlPath+'/XMLcertificates')
        try:
            
            if os.path.exists(crtTargetDir):
                path, dirs, files = next(os.walk(crtTargetDir))
                file_count = len(files)
                if(file_count>0):
                    os.system("sudo rm "+str(crtTarget))
            
            if(type(self.cert_pem).__name__=="str"):
                with open(crtTarget, "wb") as f:
                    f.write(base64.b64decode(self.cert_pem))

        except Exception as e:
            # exc_traceback = sys.exc_info()
            raise Warning(str("ERROR | "+getattr(e, 'message', repr(e)))+" ON LINE "+str(format(sys.exc_info()[-1].tb_lineno)))

    
    @api.onchange('key_pem')
    def _upload_certificate_key_to_server(self):
        xmlPath = os.path.dirname(os.path.abspath(__file__))+'/xml'
        self.key_pem_filename = "rsakey.pem"
        crtTarget = str(xmlPath+'/XMLcertificates/')+str(self.key_pem_filename)
        crtTargetDir = str(xmlPath+'/XMLcertificates')
        try:
            
            if os.path.exists(crtTargetDir):
                path, dirs, files = next(os.walk(crtTargetDir))
                file_count = len(files)
                if(file_count>0):
                    os.system("sudo rm "+str(crtTarget))

            if(type(self.key_pem).__name__=="str"):
                with open(crtTarget, "wb") as f:
                    f.write(base64.b64decode(self.key_pem))

        except Exception as e:
            # exc_traceback = sys.exc_info()
            raise Warning(str("ERROR | "+getattr(e, 'message', repr(e)))+" ON LINE "+str(format(sys.exc_info()[-1].tb_lineno)))
    
    #@api.onchange('state_id')
    #def set_location_efact(self):
    #    self.ubigeo = self.state_id.code