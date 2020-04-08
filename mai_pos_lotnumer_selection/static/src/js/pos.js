odoo.define('mai_pos_lotnumer_selection.mai_pos_lotnumer_selection', function(require){
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var PopupWidget = require('point_of_sale.popups');
    var QWeb = core.qweb;

    var PacklotlineCollection2 = Backbone.Collection.extend({
        model: models.Packlotline,
        initialize: function(models, options) {
            this.order_line = options.order_line;
        },

        get_empty_model: function(){
            return this.findWhere({'lot_name': null});
        },

        remove_empty_model: function(){
            this.remove(this.where({'lot_name': null}));
        },

        get_valid_lots: function(){
            return this.filter(function(model){
                return model.get('lot_name');
            });
        },

        set_quantity_by_lot: function() {
            if (this.order_line.product.tracking == 'serial' || this.order_line.product.tracking == 'lot') {
                var valid_lots = this.get_valid_lots();
                this.order_line.set_quantity(valid_lots.length);
            }
        }
    });

    models.load_models({
        model: 'stock.production.lot',
        fields: ['id','name','product_id','total_qty','life_date'],
        domain: function(self){ 
            var from = moment(new Date()).subtract(self.config.lot_expire_days,'d').format('YYYY-MM-DD')+" 00:00:00";
            if(self.config.allow_pos_lot){
                return [['create_date','>=',from]];
            } 
            else{
                return [['id','=',0]];
            } 
        },
        loaded: function(self,list_lot_num){
            self.list_lot_num = list_lot_num;
        },
    });
    var OrderlineSuper = models.Orderline;
    models.Orderline = models.Orderline.extend({
        set_product_lot: function(product){
            this.has_product_lot = product.tracking !== 'none' && this.pos.config.use_existing_lots;
            this.pack_lot_lines  = this.has_product_lot && new PacklotlineCollection2(null, {'order_line': this});
        },
        export_for_printing: function(){
            var pack_lot_ids = [];
            if (this.has_product_lot){
                this.pack_lot_lines.each(_.bind( function(item) {
                    return pack_lot_ids.push(item.export_as_JSON());
                }, this));
            }
            var data = OrderlineSuper.prototype.export_for_printing.apply(this, arguments);
            data.pack_lot_ids = pack_lot_ids;
            return data;
        },

        get_order_line_lot:function(){
            var pack_lot_ids = [];
            if (this.has_product_lot){
                this.pack_lot_lines.each(_.bind( function(item) {
                    return pack_lot_ids.push(item.export_as_JSON());
                }, this));
            }
            return pack_lot_ids;
        },
        get_required_number_of_lots: function(){
            var lots_required = 1;

            if (this.product.tracking == 'serial' || this.product.tracking == 'lot') {
                lots_required = this.quantity;
            }

            return lots_required;
    },


    });
    screens.PaymentScreenWidget.include({

        order_is_valid: function(force_validation) {
            var self = this;
            
            var order = this.pos.get_order();
            order.orderlines.each(_.bind( function(item) {
                if(item.pack_lot_lines){
                item.pack_lot_lines.each(_.bind(function(lot_item){
                var lot_list = self.pos.list_lot_num;
                for(var i=0;i<lot_list.length;i++){
                    if(lot_list[i].name == lot_item.attributes['lot_name']){
                        lot_list[i].total_qty -= 1;                       
                    }
                }
            },this));
            }
            },this));
            return this._super(force_validation)
            }
    });

var PackLotLinePopupWidget = PopupWidget.extend({
    template: 'PackLotLinePopupWidget',
    events: _.extend({}, PopupWidget.prototype.events, {
        'click .remove-lot': 'remove_lot',
        'keydown': 'add_lot',
        'blur .packlot-line-input': 'lose_input_focus'
    }),

        show: function(options){
            var self = this;
            var product_lot = [];
            var lot_list = self.pos.list_lot_num;
            for(var i=0;i<lot_list.length;i++){
                if(lot_list[i].product_id[0] == options.pack_lot_lines.order_line.product.id){
                    product_lot.push(lot_list[i]);
                }
            }
            options.qstr = "";
            options.product_lot = product_lot;
            this._super(options);
            this.focus();
        },

        renderElement:function(){
            this._super();
            var self = this;
            $.fn.setCursorToTextEnd = function() {
                $initialVal = this.val();
                this.val($initialVal + ' ');
                this.val($initialVal);
                };
            $(".search_lot").focus();
            $(".search_lot").setCursorToTextEnd();
            
            $(".add_lot_number").click(function(){
                var lot_count = $(this).closest("tr").find("input").val();
                for(var i=0;i<lot_count;i++){
                    var lot = $(this).data("lot");
                    var input_box;
                    $('.packlot-line-input').each(function(index, el){
                            input_box = $(el)
                    });
                    if(input_box != undefined){
                        input_box.val(lot);
                        var pack_lot_lines = self.options.pack_lot_lines,
                            $input = input_box,
                            cid = $input.attr('cid'),
                            lot_name = $input.val();

                        var lot_model = pack_lot_lines.get({cid: cid});
                        lot_model.set_lot_name(lot_name);
                        if(!pack_lot_lines.get_empty_model()){
                            var new_lot_model = lot_model.add();
                            self.focus_model = new_lot_model;
                        }
                        pack_lot_lines.set_quantity_by_lot();
                        self.renderElement();
                        self.focus();
                    }
                }
            });

            $(".search_lot").keyup(function(){
                self.options.qstr = $(this).val();
                var lot_list = self.pos.list_lot_num;
                var product_lot = [];
                for(var i=0;i<lot_list.length;i++){
                    if(lot_list[i].product_id[0] == self.options.pack_lot_lines.order_line.product.id && lot_list[i].name.toLowerCase().search($(this).val().toLowerCase()) > -1){
                        product_lot.push(lot_list[i]);
                    }
                }
                self.options.product_lot = product_lot;
                self.renderElement();

            });
        },

    click_confirm: function(){
        var pack_lot_lines = this.options.pack_lot_lines;
        this.$('.packlot-line-input').each(function(index, el){
            var cid = $(el).attr('cid'),
                lot_name = $(el).val();
            var pack_line = pack_lot_lines.get({cid: cid});
            pack_line.set_lot_name(lot_name);
        });
        pack_lot_lines.remove_empty_model();
        pack_lot_lines.set_quantity_by_lot();
        this.options.order.save_to_db();
        this.options.order_line.trigger('change', this.options.order_line);
        this.gui.close_popup();
    },

    add_lot: function(ev) {
        if (ev.keyCode === $.ui.keyCode.ENTER && this.options.order_line.product.tracking == 'serial'){
            var pack_lot_lines = this.options.pack_lot_lines,
                $input = $(ev.target),
                cid = $input.attr('cid'),
                lot_name = $input.val();

            var lot_model = pack_lot_lines.get({cid: cid});
            lot_model.set_lot_name(lot_name);  // First set current model then add new one
            if(!pack_lot_lines.get_empty_model()){
                var new_lot_model = lot_model.add();
                this.focus_model = new_lot_model;
            }
            pack_lot_lines.set_quantity_by_lot();
            this.renderElement();
            this.focus();
        }
    },

    remove_lot: function(ev){
        var pack_lot_lines = this.options.pack_lot_lines,
            $input = $(ev.target).prev(),
            cid = $input.attr('cid');
        var lot_model = pack_lot_lines.get({cid: cid});
        lot_model.remove();
        pack_lot_lines.set_quantity_by_lot();
        this.renderElement();
    },

    lose_input_focus: function(ev){
        var $input = $(ev.target),
            cid = $input.attr('cid');
        var lot_model = this.options.pack_lot_lines.get({cid: cid});
        lot_model.set_lot_name($input.val());
    },

    focus: function(){
        this.$("input[autofocus]").focus();
        this.focus_model = false;   // after focus clear focus_model on widget
    }
});
    gui.define_popup({name:'packlotline', widget:PackLotLinePopupWidget});
});
