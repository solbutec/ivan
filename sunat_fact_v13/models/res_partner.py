# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo import http
from pprint import pprint
import importlib
import os
import json

from sunatservice.sunatservice import Service

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    ubigeo = fields.Char('Ubicación Geográfica', translate=True)
    sunat_tipo_documento = fields.Selection([('6','RUC'),('1','DNI'),('4','Carnet extrangeria'),('7','Pasaporte'),('A','CED. DIPLOMATICA DE IDENTIDAD'),('B','DOC.IDENT.PAIS.RESIDENCIA-NO.D'),('C','Tax Identification Number - TIN – Doc Trib PP.NN'),('D','Identification Number - IN – Doc Trib PP. JJ')], string='Tipo Documento', default='6')
    _columns = {"sunat_tipo_documento":fields.Selection([('0','DOC.TRIB.NO.DOM.SIN.RUC'),('1','DNI'),('4','CARNET DE EXTRANJERIA'),('6','REG. UNICO DE CONTRIBUYENTES'),('7','PASAPORTE'),('A','CED. DIPLOMATICA DE IDENTIDAD'),('B','DOC.IDENT.PAIS.RESIDENCIA-NO.D'),('C','Tax Identification Number - TIN – Doc Trib PP.NN'),('D','Identification Number - IN – Doc Trib PP. JJ')], string='Tipo Documento', default='6')}

    @api.model
    def create_from_ui(self, partner):
        #with open('/home/rockscripts/Documents/data.json', 'w') as outfile:
        #                    json.dump(partner, outfile)
        """ create or modify a partner from the point of sale ui.
            partner contains the partner's fields. """
        # image is a dataurl, get the data after the comma
        if partner.get('image'):
            partner['image'] = partner['image'].split(',')[1]
        partner_id = partner.pop('id', False)
        if partner_id:  # Modifying existing partner
            self.browse(partner_id).write(partner)
        else:
            partner['lang'] = self.env.user.lang
            partner_id = self.create(partner).id
        return partner_id

        
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
                    #raise Warning(len(response['data']))
                    if len(response['data'])==0:
                        raise Warning("El RUC no fue encontrado en registros de SUNAT")
                    else:
                        
                        self.update_document(response)
                        #self.street = response['address']
                        #self.name = response["name"]
                        #self.city = response["city"]
    
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
                if dist_id:
                    self.district_id = dist_id.id
                    self.province_id = dist_id.province_id.id
                    self.state_id = dist_id.state_id.id
                    self.country_id = dist_id.country_id.id
            
                self.name = str(d['nombre']).capitalize() if d['nombre_comercial'] == '-' else str(d['nombre']).capitalize() + str(d['nombre_comercial']).capitalize()
                #self.registration_name = d['nombre']
                self.street = str(d['domicilio_fiscal']).capitalize()
                self.vat_subjected = True
                self.is_company = True
        else:
            True


    # Service very slow with trhee tries

    # @api.onchange('vat')
    # def on_change_vat(self): 
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
    #                     self.city = response["city"]
    # 