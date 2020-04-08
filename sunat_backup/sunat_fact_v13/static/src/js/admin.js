odoo.define('module.SunatBackend', function(require) {
    "use strict";
    var mainIntervalTime = 7000;
    var rpc = require('web.rpc');
    var session_info = odoo.session_info;
    /**
     * Define documents types
     */
    var docTypes = {}
    docTypes["1"] = "DNI";
    docTypes["6"] = "RUC";
    docTypes["7"] = "Pasaporte";
    docTypes["4"] = "Carnet extrangeria";
    $(document).on("click", ".o_cp_buttons  .btn", function() {
        populateDataRepresentantsList();
        loadRepresentantForm();
        loadGeneralInformationByDocument();
    });
    $(document).on("click", "button.o_form_button_save", function() {
        populateDataRepresentantsList();
        loadRepresentantForm();
        loadGeneralInformationByDocument();
    });
    $(document).on("click", "button.o_form_button_cancel", function() {
        populateDataRepresentantsList();
        loadRepresentantForm();
        loadGeneralInformationByDocument();
    });
    
    var mainInterval = setInterval(function() {
        $(document).ready(function() {
            setInterval(function() {
                if(String($(".fiscal-name").text())=="")
                {
                  populateDataRepresentantsList();
                  loadRepresentantForm();
                  loadGeneralInformationByDocument();
                }
            },20);
           

            $(document).on("click", ".product_codes_back", function() {
                go_back_button_products_service_class();
            });
            $(document).on("click", ".selector_sunat_product_code", function() {
                var wrapper = document.createElement('div');
                wrapper.innerHTML = "<div class='sunat-row'><div class='segment-container'><h1>Segmento</h1><table id='sunat_segments'></table></div></div>" +
                    "<div class='sunat-row'><div class='families-container'><h4 id='segment-name-selected'></h4><table id='sunat_families'></table></div></div>" +
                    "<div class='sunat-row'><div class='classes-container'><h4 id='family-name-selected'></h4><table id='sunat_classes'></table></div></div>" +
                    "<div class='sunat-row'><div class='products-container'><h4 id='class-name-selected'></h4><table id='sunat_products'></table></div></div>";
                swal({
                    html: true,
                    title: "Clasificación productos / servicios",
                    content: wrapper,
                    type: "success",
                    showCancelButton: true,
                    cancelButtonText: "OK",
                    closeOnCancel: true
                });
                populate_segments()
                init_back_button_products_service_class();
            });

            $(document).on("click", "tr.set_segment", function() {
                $("#segment-name-selected").text($(this).attr("name"));
                $(".segment-container").hide();
                populate_families($(this).attr("code"))
                $(".families-container").fadeIn();

            });

            $(document).on("click", "tr.set_family", function() {
                $("#family-name-selected").text($(this).attr("name"));
                $(".families-container").hide();
                populate_classes($(this).attr("code"))
                $(".classes-container").fadeIn();
            });

            $(document).on("click", "tr.set_class", function() {
                $("#class-name-selected").text($(this).attr("name"));
                $(".classes-container").hide();
                populate_products($(this).attr("code"))
                $(".products-container").fadeIn();
            });

            $(document).on("click", "tr.set_product_classification", function() {
                $(this).attr("code")
                $(this).attr("name")
                $(".ItemClassificationCode").val($(this).attr("code") + " -- " + $(this).attr("name"));
                swal.close();
            });

            $(document).on("click", ".btn-representante-create", function() {
                if ($(".representantes-formu").length > 0) {
                    loadRepresentantForm();
                    $(".representantes-list").hide();
                    $(".representantes-form-container").fadeIn();
                    $(".btn-representante-save").attr("id_representant", "0");
                    $(".btn-representante-save").attr("id_company", session_info.company_id);
                    $(".input-on-edit").hide();
                }
            });

            if ($(".company-general-information").length > 0) {
                loadGeneralInformationByDocument();
            }
            
        });
        
        
        // Display QR Image in eDocs
        $(document).on("click", ".btn-emitir-edocs", function() {
            var invoice_id = $(".edocs_document_id").text();
            var data = { "params": { "invoice_id": invoice_id } }
            $.ajax({
                type: "POST",
                url: '/dianefact/edocs_submit_invoice',
                data: JSON.stringify(data),
                dataType: 'json',
                contentType: "application/json",
                async: false,
                success: function(response) {

                    if (typeof response.result.api_message === "undefined") {} else
                        $("span[name='api_message']").text(response.result.api_message);

                    if (typeof response.result.sunat_request_status === "undefined") {} else {

                        $(".status-requested-container .status-requested-element").hide();
                        displayRequestStatus(response.result.sunat_request_status);
                    }


                }
            });
        });

        $(document).on("click", ".btn-emitir-eguide", function() {
            var stock_picking_id = $(".stock_picking_id").text();
            var data = { "params": { "stock_picking_id": stock_picking_id } }
            $.ajax({
                type: "POST",
                url: '/dianefact/eguide_submit_single',
                data: JSON.stringify(data),
                dataType: 'json',
                contentType: "application/json",
                async: false,
                success: function(response) {

                    if (typeof response.result.api_message === "undefined") {} else
                        $("span[name='api_message']").text(response.result.api_message);

                    if (typeof response.result.sunat_request_status === "undefined") {} else {

                        $(".status-requested-container .status-requested-element").hide();
                        displayRequestStatus(response.result.sunat_request_status);
                    }


                }
            });
        });

        $(document).on("click", ".btn-representante-back", function() {

            if ($(".representantes-form-container").length > 0) {
                $(".representantes-form-container").hide();
                $(".representantes-list").fadeIn();
                $(".input-on-edit").hide();
            }
        });

        $(document).on("click", ".btn-representante-save", function() {

            if ($(".representantes-form-container").length > 0) {
                var id_representant = $(this).attr("id_representant");
                var id_company = $(this).attr("id_company");
                var doc_type = $("#doc_type").val();
                var doc_number = $("#doc_number").val();
                var name = $("#name").val();
                var position = $("#position").val();
                var address = $("#address").val();
                if (doc_number == "" || name == "" || position == "" || address == "") {
                    swal({
                        title: "Campos Incompletos",
                        text: "El número de documento, nombre y dirección del representante son requeridos.",
                        type: "warning",
                        showCancelButton: true,
                        cancelButtonText: "OK",
                        closeOnCancel: true
                    });
                    return;
                }
                var data = { "params": { "id_company": id_company, "id_representant": id_representant, "doc_type": doc_type, "doc_number": doc_number, "name": name, "position": position, "address": address } }
                $.ajax({
                    type: "POST",
                    url: '/sunatefact/save_representants',
                    data: JSON.stringify(data),
                    dataType: 'json',
                    contentType: "application/json",
                    async: false,
                    success: function(response) {
                        if (response.result == false) {
                            swal({
                                title: "Representante Duplicado",
                                text: "Existe representante con la misma información",
                                type: "warning",
                                showCancelButton: true,
                                cancelButtonText: "OK",
                                closeOnCancel: true
                            });
                        } else {
                            swal({
                                title: "Representante Guardado",
                                text: "",
                                type: "success",
                                showCancelButton: true,
                                cancelButtonText: "OK",
                                closeOnCancel: true
                            });
                            populateDataRepresentantsList();
                            $(".representantes-form-container").hide();
                            $(".representantes-list").fadeIn();
                        }
                    }
                });
            }
        })

        $(document).on("click", ".btn-representante-edit", function() {
            loadRepresentantForm()
            var data = [];
            data["representant_id"] = $(this).attr("representant_id");
            var rowContainer = $(".row-representant-" + data["representant_id"]);
            data["doc_type_num"] = rowContainer.find(".td-doc_type_num").val();
            data["doc_type"] = rowContainer.find(".td-doc_type").text();
            data["doc_number"] = rowContainer.find(".td-doc_number").text();
            data["name"] = rowContainer.find(".td-name").text();
            data["position"] = rowContainer.find(".td-position").text();
            data["address"] = rowContainer.find(".td-address").text();
            data["date_added"] = rowContainer.find(".td-date-created").val();


            $("#doc_type").val(data["doc_type_num"]);
            $("#doc_number").val(data["doc_number"]);
            $("#name").val(data["name"]);
            $("#position").val(data["position"]);
            $("#address").val(data["address"]);
            $("#date_added").val(data["date_added"]);
            $(".btn-representante-save").attr("id_representant", data["representant_id"]);
            $(".representantes-list").hide();
            $(".representantes-form-container").fadeIn();
            $(".input-on-edit").fadeIn();

        });
        $(document).on("click", ".btn-representante-remove", function() {
            swal({
                    title: "¿Esta seguro?",
                    text: "No se podrá recueprar una vez se haya eliminado",
                    icon: "warning",
                    buttons: true,
                    dangerMode: true,
                })
                .then((willDelete) => {
                    if (willDelete) {
                        var id_representant = $(this).attr("representant_id");
                        var data = { "params": { "id_representant": id_representant } }
                        $.ajax({
                            type: "POST",
                            url: '/sunatefact/remove_representant',
                            data: JSON.stringify(data),
                            dataType: 'json',
                            contentType: "application/json",
                            async: false,
                            success: function(response) {
                                populateDataRepresentantsList();
                                $(".representantes-form-container").hide();
                                $(".representantes-list").fadeIn();
                            }
                        });
                    }
                });
        });



        populateDataRepresentantsList();
        clearInterval(mainInterval);
    }, mainIntervalTime);
});

function populateDataRepresentantsList() {
    if($(".representantes-list").length>0)
    {
    var docTypes = {}
    docTypes["1"] = "DNI";
    docTypes["6"] = "RUC";
    docTypes["7"] = "Pasaporte";
    var data = { "params": {} }
    $.ajax({
        type: "POST",
        url: '/sunatefact/populate_representants_list',
        data: JSON.stringify(data),
        dataType: 'json',
        contentType: "application/json",
        async: false,
        success: function(response) {
            var representants = response.result;
            var representants_rows_container = $(".representantes-list").find(".table").find("tbody");
            representants_rows_container.html("");
            if (representants.length > 0) {
                representants.forEach(function(representant) {
                    var row = '<tr class="row-representant-' + representant.id + '"><td class="td-doc_type"><input type="hidden" class="td-doc_type_num" value="' + representant.doc_type + '"/>' + docTypes[representant.doc_type] + '</td><td  class="td-doc_number">' + representant.doc_number + '</td><td class="td-name">' + representant.name + '</td><td class="td-position">' + representant.position + '</td><td class="td-address">' + representant.address + '</td><td><div class="btn-actions"><div class="btn-custom-sunat btn-representante-edit btn-smaller" representant_id="' + representant.id + '"><i class="fa fa-edit"></i></div><div class="btn-custom-sunat btn-representante-remove btn-smaller btn-red" representant_id="' + representant.id + '"><i class="fa fa-trash"></i></div><input type="hidden" class="td-date-created" value="' + representant.date_added + '"/></div></td></tr>';
                    representants_rows_container.append(row);
                });
            } else {
                var row = '<tr><td colspan="6">Compañia sin representante legal</td></tr>';
                representants_rows_container.append(row);
            }

        }
    });
}
}

function loadRepresentantForm() {
    var form = '<div class="field-box">';
    form += '<label for="doc_type">Tipo de Documento</label>';
    form += '<div><select id="doc_type"><option value="1">DNI</option><option value="6">RUC</option><option value="7">Pasaporte</option></select></div>';
    form += '</div>';

    form += '<div class="field-box">';
    form += '<label for="doc_number">Número de Documento</label>';
    form += '<div><input id="doc_number" type="text"/></div>';
    form += '</div>';

    form += '<div class="field-box">';
    form += '<label for="name">Nombre</label>';
    form += '<div><input id="name" type="text"/></div>';
    form += '</div>';

    form += '<div class="field-box">';
    form += '<label for="position">Cargo</label>';
    form += '<div><input id="position" type="text"/></div>';
    form += '</div>';

    form += '<div class="field-box">';
    form += '<label for="address">Dirección</label>';
    form += '<div><input id="address" type="text"/></div>';
    form += '</div>';

    form += '<div class="field-box">';
    form += '<label class="input-on-edit"  for="date_added">Fecha desde</label>';
    form += '<div><input class="input-on-edit" id="date_added" type="text" disabled="disabled"/></div>';
    form += '</div>';

    $(".representantes-formu").html(form)
}

function loadGeneralInformationByDocument() {
    if($(".company-general-information").length>0)
    {
    var documentNumber = $("span[name=vat]").val();
    var documentType = $("span[name=sunat_tipo_documento]").val();
    
    //alert("1 " + documentType)
    $(".o_field_char").each(function(index, item) {
        if (item.getAttribute("name") == "vat") {
            documentNumber = $(item).text();
        }
        if (item.getAttribute("name") == "sunat_tipo_documento") {
            documentType = $(item).text();
            alert("2 " + documentType)
        }
    });
    
    $(".o_field_widget").each(function(index, item) {
        if (item.getAttribute("name") == "sunat_tipo_documento") {
            documentType = $(item).text();
            if (documentType == "RUC")
                documentType = "6"
            if (documentType == "DNI")
                documentType = "1"
            if (documentType == "Carnet extrangeria")
                documentType = "4"
            if (documentType == "Pasaporte")
                documentType = "7"
            if (documentType == "CED. DIPLOMATICA DE IDENTIDAD")
                documentType = "A"
            if (documentType == "DOC.IDENT.PAIS.RESIDENCIA-NO.D")
                documentType = "B"
            if (documentType == "Tax Identification Number - TIN – Doc Trib PP.NN")
                documentType = "C"
            if (documentType == "Identification Number - IN – Doc Trib PP. JJ")
                documentType = "D"
                //alert("2 " + documentType)
        }
    });  

    if (parseInt(documentNumber) < 0) {
        var documentNumber = $(".company_vat").val();
    }
    if (parseInt(documentType) < 0) {
        documentType = $(".document-type").val();
        //alert("3 " + documentType)
    }
    if (parseInt(documentNumber) > 0)
    {

    }
    else
    {
        documentType = $('select[name="sunat_tipo_documento"]').val();
        documentType = String(documentType).trim()
        documentType = documentType.replace('"',"")
        documentType = documentType.replace('"',"")
        if (documentType == "RUC")
            documentType = "6"
        if (documentType == "DNI")
            documentType = "1"
        if (documentType == "Carnet extrangeria")
            documentType = "4"
        if (documentType == "Pasaporte")
            documentType = "7"
        if (documentType == "CED. DIPLOMATICA DE IDENTIDAD")
            documentType = "A"
        if (documentType == "DOC.IDENT.PAIS.RESIDENCIA-NO.D")
            documentType = "B"
        if (documentType == "Tax Identification Number - TIN – Doc Trib PP.NN")
            documentType = "C"
        if (documentType == "Identification Number - IN – Doc Trib PP. JJ")
            documentType = "D"
        documentNumber  = $("input[name='vat']").val();
    }
    
    if (parseInt(documentNumber) > 0) {
        var data = { "params": { "doc_num": documentNumber, "doc_type": documentType } }
        $.ajax({
            type: "POST",
            url: '/sunatefact/get_ruc',
            data: JSON.stringify(data),
            dataType: 'json',
            contentType: "application/json",
            async: false,
            success: function(response) {
                console.log(response)
                response = response.result;
                console.log(response)
                if (response.status == "FAIL") {
                    //loadGeneralInformationByDocument();
                } else if (response.status == "OK") {
                    var generalInformationHTML = '<div class="field-box">';
                    generalInformationHTML += '<label for="legal_name">Nombre legal</label>';
                    generalInformationHTML += '<div>';
                    generalInformationHTML += '<div class="fiscal-name">' + response.name + '</div>';
                    generalInformationHTML += '</div>';
                    generalInformationHTML += '</div>';

                    generalInformationHTML += '<div class="field-box">';
                    generalInformationHTML += '<label for="nombre_comercial">Nombre comercial</label>';
                    generalInformationHTML += '<div>';
                    generalInformationHTML += '<div>' + response.nombre_comercial + '</div>';
                    generalInformationHTML += '</div>';
                    generalInformationHTML += '</div>';

                    generalInformationHTML += '<div class="field-box">';
                    generalInformationHTML += '<label for="tipo_contribuyente">Tipo contribuyente</label>';
                    generalInformationHTML += '<div>';
                    generalInformationHTML += '<div>' + response.tipo_contribuyente + '</div>';
                    generalInformationHTML += '</div>';
                    generalInformationHTML += '</div>';

                    generalInformationHTML += '<div class="field-box">';
                    generalInformationHTML += '<label for="sistema_emision_comprobante">Sistema de emisión</label>';
                    generalInformationHTML += '<div>';
                    generalInformationHTML += '<div>' + response.sistema_emision_comprobante + '</div>';
                    generalInformationHTML += '</div>';
                    generalInformationHTML += '</div>';

                    generalInformationHTML += '<div class="field-box">';
                    generalInformationHTML += '<label for="sistema_contabilidad">Sistema de contabilidad</label>';
                    generalInformationHTML += '<div>';
                    generalInformationHTML += '<div>' + response.sistema_contabilidad + '</div>';
                    generalInformationHTML += '</div>';
                    generalInformationHTML += '</div>';

                    generalInformationHTML += '<div class="field-box">';
                    generalInformationHTML += '<label for="estado_contribuyente">Estado del contribuyente</label>';
                    generalInformationHTML += '<div>';
                    generalInformationHTML += '<div>' + response.estado_contribuyente + '</div>';
                    generalInformationHTML += '</div>';
                    generalInformationHTML += '</div>';

                    generalInformationHTML += '<div class="field-box">';
                    generalInformationHTML += '<label for="condicion_contribuyente">Condición del contribuyente</label>';
                    generalInformationHTML += '<div>';
                    generalInformationHTML += '<div>' + response.condicion_contribuyente + '</div>';
                    generalInformationHTML += '</div>';
                    generalInformationHTML += '</div>';

                    generalInformationHTML += '<div class="field-box">';
                    generalInformationHTML += '<label for="address">Domicilio</label>';
                    generalInformationHTML += '<div>';
                    generalInformationHTML += '<div>' + response.address + "</br>" + response.departamento + "</br>" + response.provincia + "</br>" + response.distrito + "</br>" + response.ubigeo + '</div>';
                    generalInformationHTML += '</div>';
                    generalInformationHTML += '</div>';

                    // got in old service
                    //generalInformationHTML += '<div class="field-box">';
                    //generalInformationHTML += '<label for="actividad_economica">Actividad económica</label>';
                    //generalInformationHTML += '<div>';
                    //var activities = response.actividad_economica
                    //if (response.actividad_economica.length > 0) {
                    //    for (i = 0; i < activities.length; i++) {
                    //        generalInformationHTML += '<div>' + activities[i] + '</div>';
                    //    }
                    //}
                    //generalInformationHTML += '</div>';
                    //generalInformationHTML += '</div>';

                    $(".company-general-information-container").html(generalInformationHTML);
                } else {
                    swal({
                        title: "(RUC) Identificación Tributaria",
                        text: response.status,
                        type: "warning",
                        showCancelButton: true,
                        cancelButtonText: "OK",
                        closeOnCancel: true
                    });
                }

            }
        });
    } else {

        swal({
            title: "(RUC) Identificación Tributaria",
            text: "Debe establecer la identificación tributaria.",
            type: "warning",
            showCancelButton: true,
            cancelButtonText: "OK",
            closeOnCancel: true
        });
    }
}
}

function displayRequestStatus(dian_request_status) {
    if (dian_request_status == "FAIL") {
        $(".status-requested-container .fail").fadeIn();
    } else if (dian_request_status == "OK") {
        $(".status-requested-container .ok").fadeIn();
    } else {
        $(".status-requested-container .not_requested").fadeIn();
    }
}

function populate_segments() {
    $(".product_codes_back").hide();
    $(".product_codes_back").attr("state", "start");
    //populate segments
    var data = {
        "params": {
            'segment_code': ""
        }
    }
    $.ajax({
        type: "POST",
        url: '/sunatefact/get_segments',
        data: JSON.stringify(data),
        dataType: 'json',
        contentType: "application/json",
        async: false,
        success: function(response) {
            if (typeof response.result !== undefined) {
                // $("select[name='families']").html("");
                var segments = response.result;
                $("table#sunat_segments").html("");
                segments.forEach(function(item) {
                    $("table#sunat_segments").append("<tr class='set_segment' name='" + item[1] + "' code='" + item[0] + "'> <td><b><small>" + item[0] + "  </small></b></td>" + "<td>" + item[1] + "</td>" + "</tr>");
                });
            }
        }
    });
}

function populate_families(segment_code) {
    $(".product_codes_back").fadeIn();
    $(".product_codes_back").attr("state", "1");
    var data = {
        "params": {
            'segment_code': segment_code.replace(/"([^"]+(?="))"/g, '$1')
        }
    }
    $.ajax({
        type: "POST",
        url: '/sunatefact/get_families',
        data: JSON.stringify(data),
        dataType: 'json',
        contentType: "application/json",
        async: false,
        success: function(response) {
            if (typeof response.result !== undefined) {
                // $("select[name='families']").html("");
                var families = response.result;
                $("table#sunat_families").html("");
                families.forEach(function(item) {
                    $("table#sunat_families").append("<tr class='set_family' name='" + item[1] + "' code='" + item[0] + "'> <td><b><small>" + item[0] + "  </small></b></td>" + "<td>" + item[1] + "</td>" + "</tr>");
                });
            }
        }
    });
}

function populate_classes(family_code) {
    $(".product_codes_back").fadeIn();
    $(".product_codes_back").attr("state", "2");
    var data = {
        "params": {
            'family_code': family_code.replace(/"([^"]+(?="))"/g, '$1')
        }
    }
    $.ajax({
        type: "POST",
        url: '/sunatefact/get_clases',
        data: JSON.stringify(data),
        dataType: 'json',
        contentType: "application/json",
        async: false,
        success: function(response) {
            if (typeof response.result !== undefined) {
                var clases = response.result;
                $("table#sunat_classes").html("");
                clases.forEach(function(item) {
                    $("table#sunat_classes").append("<tr class='set_class' name='" + item[1] + "' code='" + item[0] + "'> <td><b><small>" + item[0] + "  </small></b></td>" + "<td>" + item[1] + "</td>" + "</tr>");

                });
            }
        }
    });
}

function populate_products(class_code) {
    $(".product_codes_back").fadeIn();
    $(".product_codes_back").attr("state", "3");
    var data = {
        "params": {
            'class_code': class_code.replace(/"([^"]+(?="))"/g, '$1')
        }
    }
    $.ajax({
        type: "POST",
        url: '/sunatefact/get_products',
        data: JSON.stringify(data),
        dataType: 'json',
        contentType: "application/json",
        async: false,
        success: function(response) {
            if (typeof response.result !== undefined) {
                var clases = response.result;
                $("table#sunat_products").html("");
                clases.forEach(function(item) {
                    $("table#sunat_products").append("<tr class='set_product_classification' name='" + item[1] + "' code='" + item[0] + "'> <td><b><small>" + item[0] + "  </small></b></td>" + "<td>" + item[1] + "</td>" + "</tr>");
                });
            }
        }
    });
}

function init_back_button_products_service_class() {
    $(".swal-button-container").append('<button class="swal-button swal-button--cancel product_codes_back" state="start">Atrás</button>');
}

function go_back_button_products_service_class() {
    var state = $(".product_codes_back").attr("state");
    if (state == "start") {
        $(".product_codes_back").hide();
        $(".product_codes_back").attr("state", "start");
    }
    if (state == "1") {
        $(".product_codes_back").hide();
        $(".families-container").hide();
        $(".segment-container").fadeIn();
        $(".product_codes_back").attr("state", "start");
    }
    if (state == "2") {
        $(".classes-container").hide();
        $(".families-container").fadeIn();
        $(".product_codes_back").fadeIn();
        $(".product_codes_back").attr("state", "1");
    }
    if (state == "3") {
        $(".product_codes_back").fadeIn();
        $(".products-container").hide();
        $(".classes-container").fadeIn();
        $(".product_codes_back").attr("state", "2");
    }
}
