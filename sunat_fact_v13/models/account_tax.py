from odoo import models, fields, api, tools, _

class account_invoice(models.Model):

    _inherit = 'account.tax'

    sunat_tributo = fields.Selection([('1000','IGV'),('2000','ISC'),('7152','ICBPER'),('9995','Exportación'),('9996','Gratuito'),('9997','Exonerado'),('9998','Inafecto'),('9998','Otros conceptos de pago')], string='Sunat Tributo', default='1000')
    sunat_tributo_afectacion_igv = fields.Selection([('10','Gravado - Operación Onerosa'),('11','Gravado – Retiro por premio'),('12','Gravado – Retiro por donación'),('13','Gravado – Retiro'),('14','Gravado – Retiro por publicidad'),('15','Gravado – Bonificaciones'),('16','Gravado – Retiro por entrega a trabajadores'),('17','Gravado – IVAP'),('20','Exonerado - Operación Onerosa'),('21','Exonerado – Transferencia Gratuita'),('30','Inafecto - Operación Onerosa'),('31','Inafecto – Retiro por Bonificación'),('32','Inafecto – Retiro'),('33','Inafecto – Retiro por Muestras Médicas'),('34','Inafecto - Retiro por Convenio Colectivo'),('35','Inafecto – Retiro por premio'),('36','Inafecto - Retiro por publicidad'),('40','Exportación')], string='Afectación IGV', default='10')
    sunat_tributo_calculo_isc = fields.Selection([('01','Sistema al valor '),('02','Aplicación del Monto Fijo'),('03','Sistema de Precios de Venta al Público')], string='Sistema de Cálculo ISC', default='01')
    _columns = {"sunat_tributo":fields.Selection([('1000','IGV'),('2000','ISC'),('7152','ICBPER'),('9995','Exportación'),('9996','Gratuito'),('9997','Exonerado'),('9998','Inafecto'),('9998','Otros conceptos de pago')], string='Sunat Tributo', default='1000')}