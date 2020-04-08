


odoo.define("einvoice_pdf.efact_Pos", function (require) {
    "use strict";
   
    var models = require("point_of_sale.models");
    models.load_fields('res.company', 'street');
    models.load_fields('res.company', 'street2');
    models.load_fields('res.company', 'city');
    models.load_fields('res.company', 'email');
    models.load_fields('res.company', 'website');
    models.load_fields('res.company', 'partner_id');

    models.load_fields('res.partner', 'email');
    models.load_fields('res.partner', 'fe_nit');
    models.load_fields('res.partner', 'sunat_tipo_documento');

    models.load_fields('res.users', 'login');

    var _super_posmodel = models.PosModel.prototype;
    var exports = {};
    var models = require('point_of_sale.models');

    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            // New code
            var company_model = _.find(this.models, function (model) {
                return model.model === 'res.company';
            });
            company_model.fields.push('street');
            company_model.fields.push('city');
            company_model.fields.push('website');
            company_model.fields.push('login');
            company_model.fields.push('email');
            company_model.fields.push('partner_id');
            
            // Inheritance
            return _super_posmodel.initialize.call(this, session, attributes);
        },
    });

    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {

            // New code
            var partner_model = _.find(this.models, function (model) {
                return model.model === 'res.partner';
            });
            partner_model.fields.push('street');
            partner_model.fields.push('city');
            partner_model.fields.push('login');
            partner_model.fields.push('website');
            partner_model.fields.push('email');
            partner_model.fields.push('fe_nit');
            partner_model.fields.push('sunat_tipo_documento');

            // Inheritance
            return _super_posmodel.initialize.call(this, session, attributes);
        },
    });

    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            var users_model = _.find(this.models, function (model) {
                return model.model === 'res.users';
            });
            users_model.fields.push('login');
            // Inheritance
            return _super_posmodel.initialize.call(this, session, attributes);
        },
    });

    return exports;
});

