odoo.define('module.SunatEinvoicing', function(require) {
    "use strict";
    var rpc = require('web.rpc');

    $(document).ready(function() {
            var flagLoaded = false;
            var mainIntervalTime = 3800;
            var intervalId = setInterval(function () {
                $("div.div_state").fadeIn();
            if($("div.div_district").length>0)
            {
                var province_id = $("select[name='province_id']").val()
                if(province_id==null)
                {
                    var country_id = $("select[name='country_id']").val();
                    populate_location(country_id, 0, 0, 0);                    
                    clearInterval(intervalId);
                }
                
            }                
        
        }, 0);
        $("#country_id option:contains(Perú)").attr('selected', 'selected');
        //  setInterval(function() {
        $(document).on("blur", ".div_vat input", function() {
            setClientDetails()
        })
        $(document).on("change", "#sunat_tipo_documento", function() {
            setClientDetails()
        });
        $(document).on("blur", "input[name='zip']", function() {
            var zip = $("input[name='zip']").val();
            var ubigeo = $("input[name='ubigeo']").val();
            if (toString(zip) != "") {
                var ubigeo = $("input[name='ubigeo']").val(zip);
            }
        });

        // }, mainIntervalTime);

        $(document).on("change", "select[name='state_id']", function () {
            var country_id = $("select[name='country_id']").val();
            var state_id = ($("select[name='state_id']").val()!=null)? $("select[name='state_id']").val() : 0
            var province_id = ($("select[name='province_id']").val()!=null) ? $("select[name='province_id']").val() : 0
            var district_id = ($("select[name='district_id']").val()!=null) ? $("select[name='district_id']").val() : 0
            populate_location(country_id, state_id, province_id, district_id);
        });
        $(document).on("change", "select[name='province_id']", function () {
            var country_id = $("select[name='country_id']").val();
            var state_id = ($("select[name='state_id']").val()!=null)? $("select[name='state_id']").val() : 0
            var province_id = ($("select[name='province_id']").val()!=null) ? $("select[name='province_id']").val() : 0
            var district_id = ($("select[name='district_id']").val()!=null) ? $("select[name='district_id']").val() : 0
            populate_location(country_id, state_id, province_id, district_id);
        });
        $(document).on("change", "select[name='district_id']", function () {
            var country_id = $("select[name='country_id']").val();
            var state_id = ($("select[name='state_id']").val()!=null)? $("select[name='state_id']").val() : 0
            var province_id = ($("select[name='province_id']").val()!=null) ? $("select[name='province_id']").val() : 0
            var district_id = ($("select[name='district_id']").val()!=null) ? $("select[name='district_id']").val() : 0
            populate_location(country_id, state_id, province_id, district_id);
        });
        $(document).on("change", "select[name='country_id']", function () {
            var country_id = $("select[name='country_id']").val();
            var state_id = ($("select[name='state_id']").val()!=null)? $("select[name='state_id']").val() : 0
            var province_id = ($("select[name='province_id']").val()!=null) ? $("select[name='province_id']").val() : 0
            var district_id = ($("select[name='district_id']").val()!=null) ? $("select[name='district_id']").val() : 0
            populate_location(country_id, state_id, province_id, district_id);
        });
        $(document).on("change", "select[name='district_id']", function () {               
            var district_id = $("select[name='district_id']").val()
            var district_code = $('option:selected', $("select[name='district_id']")).attr('code');
            //alert(district_id+" -- "+district_code)
            $("input[name='zip']").val(district_code);
            $("input[name='ubigeo']").val(district_code);
        });
    });

    function setClientDetails() {
        var documentType = $("#sunat_tipo_documento").val()
        if (documentType == "6" || documentType == "1") {
            var documentNumber = $("input[name=vat]").val();
            if (documentNumber != "") {
                var data = { "params": { "doc_num": documentNumber, "doc_type": documentType } }
                $.ajax({
                    type: "POST",
                    url: '/sunatefact/get_ruc',
                    data: JSON.stringify(data),
                    dataType: 'json',
                    contentType: "application/json",
                    async: false,
                    success: function(response) {
                        if (response.result.status == "OK") {
                            var name = response.result.name
                            if (parseInt(documentType) == 6) {
                                $("input[name=name]").val(response.result.name);
                                $("input[name=company_name]").val(response.result.nombre_comercial);
                                $("input[name=street]").val(response.result.address);
                                $("input[name=city]").val(response.result.provincia);
                                $("input[name=zip]").val(response.result.ubigeo);
                                $("input[name=ubigeo]").val(response.result.ubigeo);
                                $("select[name=state_id] option:contains(" + response.result.provincia + ")").attr('selected', 'selected');
                                set_location(response.result.departamento, response.result.provincia, response.result.distrito, response.result.ubigeo)
                            } else if (parseInt(documentType) == 1) {
                                $(".client-name").val(response.result.name);
                            }
                            $("input[name=name]").val(response.result.name);
                            //$(".client-address-street").val(response.result.address);
                            //$(".client-address-city").val(rsesponse.result.city);
                            swal("El documento es válido", "", "success");
                            $("#country_id option:contains(Perú)").attr('selected', 'selected');
                        } else {
                            swal(response.result.status, "", "warning");
                        }
                    }
                });
            }

        }
    }

    function set_partner_location(id)
    {
        var data = { "params": { "id":id } }
        
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

    function set_location(state, province, district, ubigeo)
    {
        const capitalize = (s) => {
            if (typeof s !== 'string') return ''
            return s.charAt(0).toUpperCase() + s.slice(1)
        }
        var country_id = $("select[name='country_id']").val();
        var data = { "params": { "country_id":country_id, "state": state, "province": province, "district": district, "ubigeo": ubigeo } }
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
})