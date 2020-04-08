odoo.define('module.Sunat', function (require) {
    "use strict";
    var rpc = require('web.rpc');

    $(document).ready(function () {
        var flagLoaded = false;
        var index_Exc = 0;
        var ubigeoInterval = setInterval(function () {
            if($("select[name='district_id']").length>0)
            {
                $(document).on("click", ".new-customer", function () {
                    $(".pos_sunat_tipo_documento").val(6) // RUC by default
                    var country_id = $("select.client-address-country").val();
                    populate_location(country_id, 0, 0, 0);
                });
        
                $(document).on("change", "select[name='state_id']", function () {
                    var country_id = $("select[name='country_id']").val();
                    var state_id = ($("select[name='state_id']").val() != null) ? $("select[name='state_id']").val() : 0
                    var province_id = ($("select[name='province_id']").val() != null) ? $("select[name='province_id']").val() : 0
                    var district_id = ($("select[name='district_id']").val() != null) ? $("select[name='district_id']").val() : 0
                    populate_location(country_id, state_id, province_id, district_id);
                });
                $(document).on("change", "select[name='province_id']", function () {
                    var country_id = $("select[name='country_id']").val();
                    var state_id = ($("select[name='state_id']").val() != null) ? $("select[name='state_id']").val() : 0
                    var province_id = ($("select[name='province_id']").val() != null) ? $("select[name='province_id']").val() : 0
                    var district_id = ($("select[name='district_id']").val() != null) ? $("select[name='district_id']").val() : 0
                    populate_location(country_id, state_id, province_id, district_id);
                });
                $(document).on("change", "select[name='district_id']", function () {
                    var country_id = $("select[name='country_id']").val();
                    var state_id = ($("select[name='state_id']").val() != null) ? $("select[name='state_id']").val() : 0
                    var province_id = ($("select[name='province_id']").val() != null) ? $("select[name='province_id']").val() : 0
                    var district_id = ($("select[name='district_id']").val() != null) ? $("select[name='district_id']").val() : 0
                    populate_location(country_id, state_id, province_id, district_id);
                });
                $(document).on("change", "select[name='country_id']", function () {
                    var country_id = $("select[name='country_id']").val();
                    var state_id = ($("select[name='state_id']").val() != null) ? $("select[name='state_id']").val() : 0
                    var province_id = ($("select[name='province_id']").val() != null) ? $("select[name='province_id']").val() : 0
                    var district_id = ($("select[name='district_id']").val() != null) ? $("select[name='district_id']").val() : 0
                    populate_location(country_id, state_id, province_id, district_id);
                });
                $(document).on("change", "select[name='district_id']", function () {
                    var district_id = $("select[name='district_id']").val()
                    var district_code = $('option:selected', $("select[name='district_id']")).attr('code');
                    //alert(district_id+" -- "+district_code)
                    $("input[name='zip']").val(district_code);
                    $("input[name='ubigeo']").val(district_code);
                });
                $(document).on("click", ".client-details div.edit", function () {
                    var partner_id = $("input[name='partner_id']").val()
                    set_partner_location(partner_id)
                });
                clearInterval(ubigeoInterval);
            }
        
        },100 );
        setInterval(function () {
            var invoice_number = $("span[name=number]").text();
            var firstPart = invoice_number.substring(0, 2);
            if (firstPart == "fd" || firstPart == "fc") {
                $("button[name=202]").fadeOut();
                $("button[name=202]").find("span").text("Agregar Nota");
                $("button[name=202]").text("Agregar Nota");
                $(".o_statusbar_buttons button").each(function () {
                    var textButton = $(this).text();
                    if (textButton.toLowerCase() == "emitir rectificativa" || textButton.toLowerCase() == "emitir nota")
                        $(this).fadeOut();
                });
            }
            if (firstPart == "F0") {
                if ($(".o_invoice_form").length > 0) {
                    if (index_Exc == 0) {
                        var intervalIdFV = setInterval(function () {
                            var invoice_number = $("span[name=number]").text();
                            var data = { "params": { 'invoice_number': invoice_number } }
                            $.ajax({
                                type: "POST",
                                url: '/sunatefact/can_create_notes',
                                data: JSON.stringify(data),
                                dataType: 'json',
                                contentType: "application/json",
                                async: false,
                                success: function (response) {

                                    if (response.result.found == true) {
                                        $("span[name=number]").css("color", "red")
                                        $("span[name=number]").css("opacity", "0.8")
                                        $("span[name=number]").append("<div class='invoice-cancelled'>Factura anulada con nota - " + response.result.number + "</div>");
                                        $("button[name=202]").fadeOut();
                                    }

                                    // prevent second ajax call
                                    index_Exc++;
                                }
                            });
                        }, 150);
                    }
                }

            }

            var invoice_number = $("span[name=number]").text();
            var firstPart = invoice_number.substring(0, 2);

            if (firstPart == "FC" || firstPart == "FD") {
                $("button[name=202]").fadeOut();
                $(".o_statusbar_buttons button").each(function () {
                    var textButton = $(this).text();
                    if (textButton.toLowerCase() == "emitir rectificativa" || textButton.toLowerCase() == "emitir nota")
                        $(this).fadeOut();
                });
            }

            if (!flagLoaded) {
                $(document).on("blur", "input.vat", function () {
                    setClientDetailsByDocument();
                });
                $(document).on("change", "select.sunat_tipo_documento", function () {
                    var vat = $("input.vat").val();
                    if (vat != "")
                        setClientDetailsByDocument();
                });

                flagLoaded = true;
                $(document).on("click", ".payment-screen .button", function () {
                    if ($(this).hasClass("next")) {
                        // set_invoice_details_einvoicing();
                    }
                });

                $(document).on("click", ".new-customer", function () {
                    $(".pos_sunat_tipo_documento").val(6) // RUC by default
                    var country_id = $("select.client-address-country").val();
                    populate_location(country_id, 0, 0, 0);
                });

                $(document).on("click", ".js_invoice", function () {
                    if ($(this).hasClass("button")) {
                        var intervalIdInvoice = setInterval(function () {
                            var js_invoice = $(".js_invoice");
                            if (js_invoice.hasClass("highlight")) {
                                if ($(".journal-container-custom").length == 0) {
                                    $.ajax({
                                        type: "POST",
                                        url: '/sunatefact/get_invoice_ticket_journal',
                                        data: JSON.stringify({}),
                                        dataType: 'json',
                                        contentType: "application/json",
                                        async: false,
                                        success: function (response) {
                                            if (response.result.journals != null && response.result.journals != '') {
                                                var journals = response.result.journals;
                                                var pos_config = response.result.pos_config;
                                                var option = '';
                                                journals.forEach(function (journal, index) {
                                                    if (journal.id > 0)
                                                        option += '<option value="' + journal.id + '">' + journal.name + '</option>';
                                                });
                                                $(".payment-buttons").append("<div class='journal-container-custom'><label>Documento: </label><select id='journal_id' pos_id='" + pos_config.id + "' class='journal-pos-custom'>" + option + "</select><br><spam id='tipodocumentosec' class='popup popup-error'></spam></div>");
                                                //can't read classes from this addon default template definition, adding it on fire with jquery
                                                $(".journal-pos-custom").css("height", "38px");
                                                $(".journal-pos-custom").css("font-size", "16px");
                                                $(".journal-pos-custom").css("padding", "5px");
                                                $(".journal-pos-custom").css("margin-left", "0px");
                                                $(".journal-pos-custom").css("margin", "5px");
                                                $(".journal-container-custom").css("font-size", "18px");
                                                $("#journal_id").val(pos_config.invoice_journal_id);
                                                //if(pos_config.id=="1"){
                                                //                        var text="CREAR FACTURA";
                                                //                            document.getElementById('tipodocumentosec').innerText=text;
                                                //                                                }else{
                                                //                        var text="CREAR BOLETA";
                                                //                            document.getElementById('tipodocumentosec').innerText=text;
                                                //                }
                                            }

                                        }
                                    });
                                }
                                clearInterval(intervalIdInvoice);
                            }
                            clearInterval(intervalIdInvoice);
                        }, 100000);
                    }
                })

                $(document).on("change", "#journal_id", function () {
                    var intervalJournalSelect = setInterval(function () {
                        var pos_id = $("#journal_id").attr("pos_id");
                        var journal_new_id = $("#journal_id").val();
                        console.log(journal_new_id)
                        if (journal_new_id == "1") {
                            document.getElementById('tipodocumentosec').innerText = "CREAR FACTURA";
                        } else {
                            document.getElementById('tipodocumentosec').innerText = "CREAR BOLETA";
                        }
                        var data = { "params": { 'posID': pos_id, 'journalID': journal_new_id } }
                        //console.log(data)
                        $.ajax({
                            type: "POST",
                            url: '/sunatefact/update_current_pos_conf',
                            data: JSON.stringify(data),
                            dataType: 'json',
                            contentType: "application/json",
                            async: false,
                            success: function (qrImage64) {
                                clearInterval(intervalJournalSelect);
                            }
                        });
                    }, 1000);
                })

            }
            if ($('.pos-content').length > 0) {
                if ($('.modal').length > 0) {
                    if ($(".modal-body:contains('ESTADO: FAIL')"))
                        $(".modal").fadeOut();

                    var popUpDisplayed = $(".popups").find('.modal-dialog:not(.oe_hidden)');
                    var titleText = popUpDisplayed.find(".title").html();
                    popUpDisplayed.find(".title").hide();
                    popUpDisplayed.find(".body").html(titleText)
                }
            }
        }, 2500);



    })

    function setClientDetailsByDocument() {
        var documentNumber = $("input.vat").val();
        var documentType = $("select.pos_sunat_tipo_documento").val();
        var data = { "params": { "doc_num": documentNumber, "doc_type": documentType } }
        $.ajax({
            type: "POST",
            url: '/sunatefact/get_ruc',
            data: JSON.stringify(data),
            dataType: 'json',
            contentType: "application/json",
            async: false,
            success: function (response) {
                if (response.result.status == "OK") {
                    var name = response.result.name;
                    if (response.result.nombre_comercial != '') {
                        name = response.result.nombre_comercial;
                    }
                    if (parseInt(documentType) == 6) {
                        $(".client-name").val(name);
                        $(".client-address-street").val(response.result.address);
                        $(".client-address-city").val(response.result.provincia);
                        $(".client-address-zip").val(response.result.ubigeo);

                    } else if (parseInt(documentType) == 1) {
                        $(".client-name").val(response.result.name);
                    }

                    set_location(response.result.departamento, response.result.provincia, response.result.distrito, response.result.ubigeo)
                } else {                    
                        swal({
                            title: "Consulta de usuario",
                            text: "Sin registros",
                            type: "warning",
                            showCancelButton: true,
                            cancelButtonText: "OK",
                            closeOnCancel: true
                        });
                }
            }
        });
    }

    function set_partner_location(id) {
        var data = { "params": { "id": id } }

        $.ajax({
            type: "POST",
            url: '/sunatefact/set_partner_location',
            data: JSON.stringify(data),
            dataType: 'json',
            contentType: "application/json",
            async: false,
            success: function (response) {
                if (response.result) {
                    var partner = response.result.partner;
                    console.log(partner)
                    var state_id = partner.state_id
                    var province_id = partner.province_id
                    var district_id = partner.district_id

                    var country_id = $("select[name='country_id']").val();

                    populate_location(country_id, state_id, province_id, district_id);
                }
            }
        });
    }

    function set_location(state, province, district, ubigeo) {
        const capitalize = (s) => {
            if (typeof s !== 'string') return ''
            return s.charAt(0).toUpperCase() + s.slice(1)
        }
        var country_id = $("select[name='country_id']").val();
        var data = { "params": { "country_id": country_id, "state": state, "province": province, "district": district, "ubigeo": ubigeo } }
        $.ajax({
            type: "POST",
            url: '/sunatefact/set_location',
            data: JSON.stringify(data),
            dataType: 'json',
            contentType: "application/json",
            async: false,
            success: function (response) {
                if (response.result) {
                    var state = response.result.state
                    var province = response.result.province
                    var district = response.result.district

                    populate_location(country_id, 0, 0, 0);

                    $("select[name='state_id']").val(state.id);

                    var province_option_selected = "<option value='" + province.id + "' code='" + province.code + "'>" + capitalize(String(province.name)) + "</option>";
                    $("select[name='province_id']").html(province_option_selected)

                    var district_option_selected = "<option value='" + district.id + "' code='" + district.code + "'>" + capitalize(String(district.name)) + "</option>";
                    $("select[name='district_id']").html(district_option_selected);
                }
            }
        });
    }

    function populate_location(country_id, state_id, province_id, district_id) {
        const capitalize = (s) => {
            if (typeof s !== 'string') return ''
            return s.charAt(0).toUpperCase() + s.slice(1)
        }
        var data = { "params": { "country_id": country_id, "state_id": state_id, "province_id": province_id, "district_id": district_id } }
        $.ajax({
            type: "POST",
            url: '/sunatefact/populate_location',
            data: JSON.stringify(data),
            dataType: 'json',
            contentType: "application/json",
            async: false,
            success: function (response) {
                if (response.result.country_id > 0) {
                    var state_options = "<option value='0'>seleccionar</option>";
                    var province_options = "<option value='0'>seleccionar</option>";
                    var district_options = "<option value='0'>seleccionar</option>";
                    if (response.result.states) {
                        try {
                            var states = response.result.states
                            states.forEach(function (state, index) {
                                state_options += "<option value='" + state.id + "' code='" + state.code + "'>" + capitalize(String(state.name)) + "</option>";
                            });
                            $("select[name='state_id']").html("");
                            $("select[name='state_id']").append(state_options);
                        }
                        catch (error) {
                        }

                        try {
                            var provinces = response.result.provinces
                            provinces.forEach(function (province, index) {
                                province_options += "<option value='" + province.id + "' code='" + province.code + "'>" + capitalize(String(province.name)) + "</option>";
                            });
                            $("select[name='province_id']").html("");
                            $("select[name='province_id']").append(province_options);
                        }
                        catch (error) {
                        }

                        try {
                            var districts = response.result.districts
                            districts.forEach(function (district, index) {
                                district_options += "<option value='" + district.id + "' code='" + district.code + "'>" + capitalize(String(district.name)) + "</option>";
                            });

                            $("select[name='district_id']").html("");
                            $("select[name='district_id']").append(district_options);
                        }
                        catch (error) {
                        }

                    }
                    $("select[name='state_id']").val(state_id)
                    $("select[name='province_id']").val(province_id)
                    $("select[name='district_id']").val(district_id)
                }
            }
        });
    }
});

odoo.define('sunat_fact.efact_Pos', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var _super_posmodel = models.PosModel.prototype;

    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            // New code
            var partner_model = _.find(this.models, function (model) {
                return model.model === 'res.partner';
            });
            partner_model.fields.push('sunat_tipo_documento');
            // Inheritance
            return _super_posmodel.initialize.call(this, session, attributes);
        },
    });

    var screens = require('point_of_sale.screens');
    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var utils = require('web.utils');
    var field_utils = require('web.field_utils');
    var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;
    var _t = core._t;
    var QWeb = core.qweb;
    var _t = core._t;
    var round_pr = utils.round_precision;
    /* ********************************************************
    screens.ClientListScreenWidget
    ******************************************************** */


    screens.PaymentScreenWidget.include({
        renderElement: function () {
            var self = this;
            this._super();

            this.render_paymentlines();

            this.$('.back').click(function () {
                self.click_back();
            });

            this.$('.next').click(function () {
                self.validate_order();
            });

            this.$('.js_set_customer').click(function () {
                self.click_set_customer();
            });

            this.$('.js_tip').click(function () {
                self.click_tip();
            });
            this.$('.js_factura').click(function () {
                self.click_invoice_factura();
            });
            this.$('.js_email').click(function () {
                self.click_email();
            });
            this.$('.js_cashdrawer').click(function () {
                self.pos.proxy.printer.open_cashbox();
            });
            this.$('.js_give_invoice').click(function () {
                var edoc_type = $(this).attr("edoc_type");
                if (edoc_type == "factura") {
                    self.click_invoice_factura();
                    $('.js_boleta').removeClass('highlight');
                    $('.js_factura').addClass('highlight');
                }
                if (edoc_type == "boleta") {
                    self.click_invoice_boleta();
                    $('.js_factura').removeClass('highlight');
                    $('.js_boleta').addClass('highlight');
                }
                var js_invoice = $(".js_invoice");
                if ($(".journal-container-custom").length == 0) {
                    $.ajax({
                        type: "POST",
                        url: '/sunatefact/get_invoice_ticket_journal',
                        data: JSON.stringify({}),
                        dataType: 'json',
                        contentType: "application/json",
                        async: false,
                        success: function (response) {
                            if (response.result.journals != null && response.result.journals != '') {
                                var journals = response.result.journals;
                                var pos_config = response.result.pos_config;
                                var option = '';
                                var journal_factura_id = null;
                                var journal_boleta_id = null;
                                var document_id = null;
                                journals.forEach(function (journal, index) {
                                    if (journal.id > 0) {
                                        option += '<option value="' + journal.id + '">' + journal.name + '</option>';
                                        if (String(String(journal.name).toLocaleLowerCase()).includes('factura')) {
                                            journal_factura_id = journal.id;
                                        }
                                        if (String(String(journal.name).toLocaleLowerCase()).includes('boleta')) {
                                            journal_boleta_id = journal.id;
                                        }
                                        if (String(String(journal.name).toLocaleLowerCase()).includes(edoc_type)) {
                                            document_id = journal.id;
                                        }
                                    }

                                });
                                var payment_buttons = $(".payment-buttons");
                                payment_buttons.append("<div class='journal-container-custom'><label>Documento: </label><select id='journal_id' pos_id='" + pos_config.id + "' class='journal-pos-custom'>" + option + "</select><br><spam id='tipodocumentosec' class='popup popup-error'></spam></div>");
                                //can't read classes from this addon default template definition, adding it on fire with jquery
                                $(".journal-pos-custom").css("height", "38px");
                                $(".journal-pos-custom").css("font-size", "16px");
                                $(".journal-pos-custom").css("padding", "5px");
                                $(".journal-pos-custom").css("margin-left", "0px");
                                $(".journal-pos-custom").css("margin", "5px");
                                $(".journal-container-custom").css("font-size", "18px");
                                
                                $(".js_factura").attr("journal_id", journal_factura_id);
                                $(".js_boleta").attr("journal_id", journal_boleta_id);
                                payment_buttons.find(".journal-container-custom").hide();
                                $("#journal_id").val(document_id);
                            }

                        }
                    });
                }
                else {
                    var id_document = $(this).attr("journal_id");
                    $('#journal_id').val(id_document);
                }
                var pos_id = $("#journal_id").attr("pos_id");
                var journal_new_id = $("#journal_id").val();
                var data = { "params": { 'posID': pos_id, 'journalID': journal_new_id } }
                $.ajax({
                    type: "POST",
                    url: '/sunatefact/update_current_pos_conf',
                    data: JSON.stringify(data),
                    dataType: 'json',
                    contentType: "application/json",
                    async: false,
                    success: function (qrImage64) {
                    }
                });
            });
        },
        click_invoice_factura: function () {
            var order = this.pos.get_order();
            if(!order.is_to_invoice())
            {
               order.set_to_invoice(true); 
            }
            
            this.$('.js_factura').removeClass('highlight');
            this.$('.js_boleta').removeClass('highlight');
            if (order.is_to_invoice()) {
                this.$('.js_boleta').removeClass('highlight');
                this.$('.js_factura').addClass('highlight');
            } else {
                this.$('.js_factura').removeClass('highlight');
                this.$('.js_boleta').addClass('highlight');
            }
        },
        click_invoice_boleta: function () {
            //alert("in")
            var order = this.pos.get_order();
            if(!order.is_to_invoice())
            {
               order.set_to_invoice(true); 
            }
            this.$('.js_factura').removeClass('highlight');
            this.$('.js_boleta').removeClass('highlight');
            if (order.is_to_invoice()) {
                this.$('.js_factura').removeClass('highlight');
                this.$('.js_boleta').addClass('highlight');
            } else {
                this.$('.js_boleta').removeClass('highlight');
                this.$('.js_factura').addClass('highlight');
            }
        },

    });
    screens.ReceiptScreenWidget.include({
        get_receipt_render_env: function () {
            this.pos.last_receipt_render_env = this._super();
            console.log(this.pos_edoc())
            var pos_edoc = this.pos_edoc();
            this.pos.last_receipt_render_env['ejournal_name'] = pos_edoc['journal_name'];
            this.pos.last_receipt_render_env['enumber'] = pos_edoc['number'];
            this.pos.last_receipt_render_env['total_letters'] = pos_edoc['total_letters'];
            this.pos.last_receipt_render_env['qr_image'] = window.location.origin + '/web/image?model=account.invoice&field=qr_image&id=' + pos_edoc['inv_id'];

            return this.pos.last_receipt_render_env;
        },
        pos_edoc: function () {
            var order = this.pos.get_order();
            var orderID = order.name;
            if (orderID != "") {

                var data = { "params": { 'orderID': orderID } }
                var result = [];
                $.ajax({
                    type: "POST",
                    url: '/sunatefact/get_invoice_ordered',
                    data: JSON.stringify(data),
                    dataType: 'json',
                    contentType: "application/json",
                    async: false,
                    success: function (response) {

                        result['qr_image'] = response.result.qr_image;
                        result['journal_name'] = response.result.journal_name;
                        result['number'] = response.result.number;
                        result['total_letters'] = response.result.total_letters;
                        result['inv_id'] = response.result.inv_id;
                        return result;

                    }

                });
                return result
            } else {

            }

            //}, 2500);
            // }
            var response = set_invoice_details_einvoicing();
            console.log(response);
        },
    });


    screens.ClientListScreenWidget.include({
        display_client_details: function (visibility, partner, clickpos) {
            var self = this;
            var searchbox = this.$('.searchbox input');
            var contents = this.$('.client-details-contents');
            var parent = this.$('.client-list').parent();
            var scroll = parent.scrollTop();
            var height = contents.height();

            contents.off('click', '.button.edit');
            contents.off('click', '.button.save');
            contents.off('click', '.button.undo');
            contents.on('click', '.button.edit', function () { self.edit_client_details(partner); });
            contents.on('click', '.button.save', function () { self.save_client_details(partner); });
            contents.on('click', '.button.undo', function () { self.undo_client_details(partner); });
            this.editing_client = false;
            this.uploaded_picture = null;

            if (visibility === 'show') {
                contents.empty();
                contents.append($(QWeb.render('ClientDetails', { widget: this, partner: partner })));

                var new_height = contents.height();

                if (!this.details_visible) {
                    // resize client list to take into account client details
                    parent.height('-=' + new_height);

                    if (clickpos < scroll + new_height + 20) {
                        parent.scrollTop(clickpos - 20);
                    } else {
                        parent.scrollTop(parent.scrollTop() + new_height);
                    }
                } else {
                    parent.scrollTop(parent.scrollTop() - height + new_height);
                }

                this.details_visible = true;
                this.toggle_save_button();
            } else if (visibility === 'edit') {
                // Connect the keyboard to the edited field
                if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
                    contents.off('click', '.detail');
                    searchbox.off('click');
                    contents.on('click', '.detail', function (ev) {
                        self.chrome.widget.keyboard.connect(ev.target);
                        self.chrome.widget.keyboard.show();
                    });
                    searchbox.on('click', function () {
                        self.chrome.widget.keyboard.connect($(this));
                    });
                }

                this.editing_client = true;
                contents.empty();
                contents.append($(QWeb.render('ClientDetailsEdit', { widget: this, partner: partner })));
                this.toggle_save_button();
                $('#sunat_tipo_documento').val(partner.sunat_tipo_documento);
                // Browsers attempt to scroll invisible input elements
                // into view (eg. when hidden behind keyboard). They don't
                // seem to take into account that some elements are not
                // scrollable.
                contents.find('input').blur(function () {
                    setTimeout(function () {
                        self.$('.window').scrollTop(0);
                    }, 0);
                });

                contents.find('.image-uploader').on('change', function (event) {
                    self.load_image_file(event.target.files[0], function (res) {
                        if (res) {
                            contents.find('.client-picture img, .client-picture .fa').remove();
                            contents.find('.client-picture').append("<img src='" + res + "'>");
                            contents.find('.detail.picture').remove();
                            self.uploaded_picture = res;
                        }
                    });
                });
            } else if (visibility === 'hide') {
                contents.empty();
                parent.height('100%');
                if (height > scroll) {
                    contents.css({ height: height + 'px' });
                    contents.animate({ height: 0 }, 400, function () {
                        contents.css({ height: '' });
                    });
                } else {
                    parent.scrollTop(parent.scrollTop() - height);
                }
                this.details_visible = false;
                this.toggle_save_button();
            }
        },
        close: function () {
            this._super();
            if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
                this.chrome.widget.keyboard.hide();
            }
        }
    });
});


odoo.define("sunat_fact.efact_PosModels", function (require) {
    "use strict";

    var models = require("point_of_sale.models");
    models.load_fields('res.company', 'street');
    models.load_fields('res.company', 'street2');
    models.load_fields('res.company', 'city');
    models.load_fields('res.company', 'email');
    models.load_fields('res.company', 'website');
    models.load_fields('res.company', 'partner_id');

    models.load_fields('res.partner', 'email');
    models.load_fields('res.partner', 'sunat_tipo_documento');
    models.load_fields('res.partner', 'state_id');
    models.load_fields('res.partner', 'province_id');
    models.load_fields('res.partner', 'district_id');

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
            partner_model.fields.push('state_id');
            partner_model.fields.push('province_id');
            partner_model.fields.push('district_id');
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

