
window.onload = function(){
    numeric_only_event($(".ship-quantity-box"))
    float_values_allowance_for_input($("#shipment-order-shipping-price"))
}

$(".add-shipment-info").click(function(){
    let validation_result= validate_one_tick_n_get_data($(this))
    if (!validation_result[0]){
        return null
    }
    let location = validation_result[1]
    let po_if= validation_result[2]
    add_datepicker()
    if (validation_result[5]){
        open_shipment_modal(validation_result[5],location,po_if,1)
        return null
    }
    open_fresh_shipment_modal(validation_result)
})

$(".add-pl-invoice").click(function(){
    let validation_result= validate_one_tick_n_get_data($(this))
    let validated = validate_tickboxes_for_plpi($(this))
    if (!validation_result[0] || !validated){
        return null
    }
    if (validation_result[5]==null){
        $("#yes-shipment-confirm-pli").attr("data-location",validation_result[1])
        $("#no-shipment-confirm-pli").attr("data-location",validation_result[1])
        $("#shipment-confirmation_pli").modal('show')
        return null
    }
    create_pl_n_invoice(validation_result[1])
})


$(".s-tag-current-shipment").click(function(){ 
    open_shipment_modal($(this).attr("data-ship_data"),$(this).attr("data-location"),$(this).attr("data-poif"))
})
$(".s-tag-sent-shipment").click(function(){ 
    open_shipment_modal($(this).attr("data-ship_data"),$(this).attr("data-location"),$(this).attr("data-poif"))
})
$("#yes-shipment-confirm-pli").click(function(){
    $(".add-shipment-info[data-location|='"+$(this).attr("data-location")+"']").trigger("click")
    $(this).removeAttr("data-location")
})

$("#no-shipment-confirm-pli").click(function(){
    let location = $(this).attr("data-location")
    $(this).removeAttr("data-location")
    create_pl_n_invoice(location)
})

$(".cancel-dispatch").click(function(){
    let validation_result= validate_one_tick_n_get_data($(this))
    if (!validation_result[0]){
        return null
    }
    frappe.call({
        method: 'erpnext.modehero.production.cancelDispatch',
        args: {
            po:validation_result[2],
            soi:validation_result[4]
        },
        callback: function (r) {
            if (r) {
                if (r.message['status'] == "ok") {
                    response_message('Successfull', 'Order cancelled successfully', 'green')
                    clear_inputs()
                    window.location.reload()
                    return null;
                }
                clear_inputs()
                response_message('Unsuccessfull','Order cancelled unsuccessfully !', 'red')
                window.location.reload()
                return null
            }
            response_message('Unsuccessfull', 'Order cancelled unsuccessfully !', 'red')
        }
    });
})

$("#shipment-order-modal").on("hidden.bs.modal", function () {
    $("#create-shipment-order input").removeAttr("disabled")
    $("#create-shipment-order")[0].reset()
    $("#shipment-order-document-div").removeAttr("hidden")
    $("#shipment-order-save").removeAttr("hidden")
    $("#shipment-order-file").removeAttr("hidden",true).removeAttr("href")
    $(this).removeAttr("data-shipment_name").removeAttr("data-location").removeAttr("data-sales_order_item").removeAttr("data-dispatch_name")
})

function create_pl_n_invoice(location){
    let data = collect_data_for_plpi(location)
    frappe.call({
        method: 'erpnext.modehero.production.generateMultiplePLInvoice',
        args: {
            data:data,
        },
        callback: function (r) {
            if (r) {
                if (r.message['status'] == "ok") {
                    response_message('Successfull', 'PL + Invoice created successfully', 'green')
                    clear_inputs()
                    window.location.reload()
                    return null;
                }
                clear_inputs()
                response_message('Unsuccessfull', r.message['message'], 'red')
                window.location.reload()
                return null
            }
            response_message('Unsuccessfull', 'PL + Invoice created unsuccessfully', 'red')
        }
    });
}


function open_fresh_shipment_modal(data){
    $("#shipment-order-if").empty().append("<option value='"+data[2]+"'>"+data[2]+"</option>")
    let modal_element = $("#shipment-order-modal")
    modal_element.attr("data-location",location)
    if (data[4]!=null)  modal_element.attr("data-sales_order_item",data[4]) 
    $("#shipment-order-file").prop("hidden",true)
    if (data[3].hasClass("sent-tick")){
        modal_element.attr("data-dispatch_name",data[3].attr("data-dispatch"))
    }
    modal_element.modal('show')
}


function validate_tickboxes_for_plpi(element){
    let location = $(element).attr("data-location")
    let selected_amt = $("input.not-sent-tick:checkbox[data-location|='"+location+"']:checked").length
    if (selected_amt==0){
        return false
    }
    let any_error = false
    $("input.not-sent-tick:checkbox[data-location|='"+location+"']:checked").each(function(){
        if (!validate_ship_quantity($(this))){
            any_error = true
            return false
        }
    })
    if (any_error){
        response_message('Unsuccessfull', 'Invalid inputs !', 'red')
        return false
    }
    return true
}

function validate_one_tick_n_get_data(element){
    let location = $(element).attr("data-location")
    let selected_amt = $("input:checkbox[data-location|='"+location+"']:checked").length
    if (selected_amt==0){
        return [false]
    }
    if (selected_amt>1){
        response_message('Unsuccessfull', 'Multiple selection are not allowed !', 'red')
        return [false]
    }    
    let tick_box_element = $("input:checkbox[data-location|='"+location+"']:checked").first()
    let po_if = tick_box_element.attr("data-if")
    let sales_order_item = (tick_box_element.attr("data-sales_order_item")) ? tick_box_element.attr("data-sales_order_item"):null
    let shipment_order = (tick_box_element.attr("data-ship_data")) ? tick_box_element.attr("data-ship_data"):null
    return [true,location,po_if,tick_box_element,sales_order_item,shipment_order]
}

function open_shipment_modal(data,location,po_if,is_editable){
    data = JSON.parse(data.replace(/'/g, '"'))
    set_modal_data(data,location,po_if)
    $("#shipment-order-modal").modal('show')
}

function hide_elements(){
    $("#create-shipment-order input").prop("disabled", true)
    $("#shipment-order-document-div").prop("hidden", true)
    $("#shipment-order-save").prop("hidden", true)
}

function set_modal_data(data,location,po_if){
    $("#shipment-order-modal").attr("data-location",location)
    $("#shipment-order-modal").attr("data-shipment_name",data.name)
    $("#shipment-order-if").empty().append("<option value='"+po_if+"'>"+po_if+"</option>")
    $("#shipment-order-ca-company").val(data.carrier_company)
    $("#shipment-order-shipping-price").val(data.shipping_price)
    $("#shipment-order-tracking-number").val(data.tracking_number)
    $("#shipment-order-tracking-link").val(data.html_tracking_link)
    $("#shipment-order-shipping-date").attr( "value",data.shipping_date)
    $("#shipment-order-expected-date").attr( "value",data.expected_delivery_date)
    if (data.shipping_document!=""){
        $("#shipment-order-file").attr("href",data.shipping_document)
    }
    else{
        $("#shipment-order-file").prop("hidden",true)
    }
}

function validate_ship_quantity(tick_box_element){
    let validated = true
    tick_box_element.parent().parent().children(".ship-quantity-boxs").each(function(){
        if ($(this).children(":input.ship-quantity-box").first().val().trim().length==0){
            validated = false
            return false
        }
    })
    return validated
}

function collect_data_for_plpi(location){
    let result_list = []
    $("input.not-sent-tick:checkbox[data-location|='"+location+"']:checked").each(function(){
        let current_shipment_name = null
        if ($(this).attr("data-ship_name")){
            current_shipment_name = $(this).attr("data-ship_name")
        }
        let temp_obj = {
            "sales_order_item":  ($(this).attr("data-sales_order_item")) ? $(this).attr("data-sales_order_item") : null ,
            "po_if":$(this).attr("data-if"),
            "shipment_order":current_shipment_name,
            "size_qty":{}
        }
        $(this).parent().parent().children(".ship-quantity-boxs").each(function(){
            temp_obj.size_qty[$(this).children(":input.ship-quantity-box").first().attr("data-size")] = $(this).children(":input.ship-quantity-box").first().val()
        })
        result_list.push(temp_obj)
    })
    return result_list
}

function response_message(title, message, color) {
    frappe.msgprint({
        title: __(title),
        indicator: color,
        message: __(message)
    });
}

function float_values_allowance_for_input(element){
    element.keypress(function(event) {
        if (((event.which != 46 || (event.which == 46 && $(this).val() == '')) ||
                $(this).val().indexOf('.') != -1) && (event.which < 48 || event.which > 57)) {
            event.preventDefault();
        }
    }).on('paste', function(event) {
        event.preventDefault();
    })
}

function numeric_only_event(element){
    element.keypress(function(e) {
        if (isNaN(String.fromCharCode(e.which)) || e.which == 32) e.preventDefault();
    }).on('paste', function(event) {
        event.preventDefault();
    });
}

function add_datepicker(){
    $("#shipment-order-shipping-date").datepicker({
            autoclose: true,
            todayBtn: true,
            format: 'mm/dd/yyyy',
            calendarWeeks: true,
            keyboardNav: false,
            todayHighlight: true
        });
    $("#shipment-order-expected-date").datepicker({
            autoclose: true,
            todayBtn: true,
            format: 'mm/dd/yyyy',
            calendarWeeks: true,
            keyboardNav: false,
            todayHighlight: true
        });
}