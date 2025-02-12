import frappe
import json
import ast
import datetime
from erpnext.modehero.stock import updateStock2, get_details_fabric_from_order, get_details_trimming_from_order, get_product_details_from_order, get_details_packaging_from_order,stockOut
from frappe.email.doctype.notification.notification import sendCustomEmail
free_size_name = "Free Size"
@frappe.whitelist()
def create_production_order(data):

# data:{
# 'product_category':'proto - Moynat'
# 'internal_ref':'xsc'
# 'product_name':'29'
# 'production_factory':'facto 2'
# 'quantity':[{'quantity': '4', 'size': 'A'}]
# 'fab_suppliers':{'0.485899247691032': {'fabric_con': '23', 'fabric_ref': '464864', 'fabric_status': 'To be sent later', 'fabric_supplier': 'Loro Piana'}, '0.8194292281842649': {'fabric_con': '23', 'fabric_ref': '223311', 'fabric_status': None, 'fabric_supplier': 'TEST RED'}}
# 'trim_suppliers':{'0.15179674763375983': {'trim_con': '22', 'trim_ref': 'wed', 'trim_status': 'On stock at factory', 'trim_supplier': 'dtrim'}}
# 'pack_suppliers':{'0.4848414809400162': {'pack_con': '34', 'pack_ref': 'PB 20', 'pack_status': 'To be sent later', 'pack_supplier': 'Packager1'}, '0.6865090500983441': {'pack_con': '31', 'pack_ref': 'adsf', 'pack_status': 'To be sent later', 'pack_supplier': 'Packager1'}, '0.9813391020556028': {'pack_con': '34', 'pack_ref': 'qqq', 'pack_status': 'To be sent later', 'pack_supplier': 'Packager1'}}
# 'comment':''
# }

    data = json.loads(data)
    user = frappe.get_doc('User', frappe.session.user)
    brand = user.brand_name

    json_fab_suppliers = data['fab_suppliers']
    json_trim_suppliers = data['trim_suppliers']
    json_pack_suppliers = data['pack_suppliers']
    
    fab_refs = []
    trim_refs = []
    pack_refs = []

    order_suppliers = []

    for key in json_fab_suppliers:
        if(json_fab_suppliers[key] != {}):
            if(json_fab_suppliers[key]['fabric_ref'] != None):
                fab_refs.append(json_fab_suppliers[key]['fabric_ref'])
                order_suppliers.append({
                    'supplier': json_fab_suppliers[key]['fabric_supplier'],
                    'supplier_group': 'Fabric',
                    'fabric_consumption': json_fab_suppliers[key]['fabric_con'],
                    'fabric_ref': json_fab_suppliers[key]['fabric_ref'],
                    'fabric_status': json_fab_suppliers[key]['fabric_status']
                })

    for key in json_trim_suppliers:
        if(json_trim_suppliers[key] != {}):
            if(json_trim_suppliers[key]['trim_ref'] != None):
                trim_refs.append(json_trim_suppliers[key]['trim_ref'])
                order_suppliers.append({
                    'supplier': json_trim_suppliers[key]['trim_supplier'],
                    'supplier_group': 'Trimming',
                    'trimming_consumption': json_trim_suppliers[key]['trim_con'],
                    'trimming_ref': json_trim_suppliers[key]['trim_ref'],
                    'trimming_status': json_trim_suppliers[key]['trim_status']

                })

    for key in json_pack_suppliers:
        if(json_pack_suppliers[key] != {}):
            if(json_pack_suppliers[key]['pack_ref'] != None):
                pack_refs.append(json_pack_suppliers[key]['pack_ref'])
                order_suppliers.append({
                    'supplier': json_pack_suppliers[key]['pack_supplier'],
                    'supplier_group': 'Packaging',
                    'packaging_consumption': json_pack_suppliers[key]['pack_con'],
                    'packaging_ref': json_pack_suppliers[key]['pack_ref'],
                    'packaging_status': json_pack_suppliers[key]['pack_status']
                })

    production_factory=frappe.get_doc("Production Factory",data['production_factory'])
    free_size_qty = data['free_size_qty'] if "free_size_qty" in data else None
    order = frappe.get_doc({
        'doctype': 'Production Order',
        'product_category': data['product_category'],
        'internal_ref': data['internal_ref'],
        'product_name': data['product_name'],
        'production_factory': data['production_factory'],
        'fac_country':production_factory.country,
        'final_destination':data['final_destination'],
        'destination_type':data['destination_type'], #if pos-->1, if destination-->0
        'quantity_per_size': data['quantity'],
        'suppliers': order_suppliers,
        'factory_email':production_factory.email_address,
        'comment': data['comment'],
        'free_size_qty':free_size_qty,
        'brand': brand
    })
    order.insert(ignore_permissions=True)

    order_quantities = get_order_quantities(order)
    # If there is a missvalue in any fabric/trimming/packaging consumption values, then no stock of all of three will not be reduced
    if order_quantities != None:
        try:
            existing_details = get_old_quantities_unitprice(
            order_quantities['fabric_quantities'], order_quantities['trimming_quantities'], order_quantities['packaging_quantities'])
            if existing_details['fabric_details']:
                for fabric_detail in existing_details['fabric_details']:
                    updateStock2(fabric_detail['stock_name'], fabric_detail['old_stock']-fabric_detail['fab_quantity'],
                                fabric_detail['old_stock'], "Production Fabric", fabric_detail['unit_price'],"fabric",None,order,"production")

            if existing_details['trimming_details']:
                for trimming_detail in existing_details['trimming_details']:
                        updateStock2(trimming_detail['stock_name'], trimming_detail['old_stock']-trimming_detail['trim_quantity'],
                                    trimming_detail['old_stock'], "Production Trimming", trimming_detail['unit_price'],"trimming",None,order,"production")
            if existing_details['packaging_details']:
                for packaging_detail in existing_details['packaging_details']:
                    updateStock2(packaging_detail['stock_name'], packaging_detail['old_stock']-packaging_detail['pack_quantity'],
                                packaging_detail['old_stock'], "Production Packaging", packaging_detail['unit_price'],"packaging",None,order,"production")

        except :
            print("Stocks not updated")

    # recipients=['sdhananjana14@gmail.com']
    # sender="Support <modetesth@gmail.com>" 
    # subject="Test Prod order"
    # message="This Ok"
    # frappe.sendmail(recipients,sender,subject,message)
    sendNotificationEmail(order)
       

    return {'status': 'ok', 'order': order}

def sendNotificationEmail(order):
    #send email to factory 
    notification=frappe.get_doc("Notification","Order Recieved")
    factory=frappe.get_doc("Production Factory",order.production_factory)
    templateData={}
    templateData['SNF']=factory.factory_name
    templateData['order_name']=order.name
    templateData['brand']=order.brand
    templateData['order_type']='production'
    templateData['recipient']=factory.email_address
    templateData['country']=factory.country
    templateData['dashboard_link']="/production-dashboard"
    templateData['isSubscribed']=(factory.is_official==1)
    templateData['notification']=notification

    if(factory.email_address != None):
        sendCustomEmail(templateData)
    

@frappe.whitelist()
def validate(order, isvalidate):
    order = frappe.get_doc('Production Order', order)
    if isvalidate == 'true':
        order.docstatus = 1
    else:
        order.docstatus = 1
        order.save()
        order.docstatus = 2
    order.save(ignore_permissions=True)
    frappe.db.commit()
    return order


@frappe.whitelist()
def set_finish(orderslist):
    orderslist = ast.literal_eval(orderslist)
    res_status = "ok"
    for order in orderslist:
        order = frappe.get_doc('Production Order', order)
        if (order):
            order.docstatus = 1
            order.save()
            stockUpdateAfterFinish(order)
        else:
            res_status = "no"
    frappe.db.commit()
    return {'status': res_status}


def stockUpdateAfterFinish(order):
    order_quantity = get_total_quantity(order)
    if (order_quantity == None):
        return
    existing_details = get_product_details_from_order(
        order, "production")
    if existing_details == None:
        return

    size_order = get_size_order(order)
    price = calculate_price(size_order)[
        order.product_name] + existing_details['old_value']
    total_quantity = int(order_quantity)+existing_details['old_stock']
    if existing_details["size_details"]==None:
        updateStock2(existing_details['stock_name'], total_quantity,
                 existing_details['old_stock'], "Production", price*1.0/total_quantity,"product",None,order,"production")
    else:
        updateStock2(existing_details['stock_name'], total_quantity,
                 existing_details['old_stock'], "Production", price*1.0/total_quantity,"product",{"old":existing_details["size_details"],"new_incoming":size_order[order.product_name]},order,"production")


@frappe.whitelist(allow_email_guest=True)
def submit_production_summary_info(data):
    data = json.loads(data)
    order = frappe.get_doc('Production Order', data['order'])
    order.expected_work_date = data['ex_work_date']
    order.confirmation_doc = data['confirmation_doc']
    order.profoma = data['profoma']
    order.invoice = data['invoice']
    order.carrier = data['carrier']
    order.tracking_number = data['tracking_number']
    order.shipment_date = data['shipment_date']
    order.price=data['price']
    order.production_comment = data['production_comment']
    if(order.profoma != 'None'):
        order.docstatus = 1
    order.save()
    if(data['shipment_date']!=None and data['shipment_date']!="") or (data['carrier']!=None and data['carrier']!="") or (data['tracking_number']!=None and data['tracking_number']!="") :
        stockUpdateAfterFinish(order)
    return order


def get_total_quantity(order):
    # this functio returns total quantity of the order collecting all size quantities
    total_quantity = 0
    try:
        if order.free_size_qty!=None:
            return int(order.free_size_qty)
        for size in order.quantity_per_size:
            if (size.quantity != None):
                total_quantity = total_quantity + int(size.quantity)
        return total_quantity
    except ValueError:
        return None

def get_order_quantities(order):
    # this function returns quantity details under fabric/trimming/packaging
    total_quantity = get_total_quantity(order)
    fabric_quantities = []
    trimming_quantities = []
    packaging_quantities = []
    if (total_quantity == 0):
        return None
    try:
        for supplier in order.suppliers:
            if(supplier.supplier_group == 'Fabric'):
                fabric_quantity={}
                fabric_quantity['supplier'] = supplier.supplier
                fabric_quantity['fabric_ref'] = supplier.fabric_ref
                fabric_quantity['quantity'] = total_quantity*int(supplier.fabric_consumption)

                fabric_quantities.append(fabric_quantity)
            elif(supplier.supplier_group == 'Trimming'):
                trimming_quantity={}
                trimming_quantity['supplier'] = supplier.supplier
                trimming_quantity['trimming_ref'] = supplier.trimming_ref
                trimming_quantity['quantity'] =total_quantity*int(supplier.trimming_consumption)
                trimming_quantities.append(trimming_quantity)
            elif(supplier.supplier_group == 'Packaging'):
                packaging_quantity={}
                packaging_quantity['supplier'] = supplier.supplier
                packaging_quantity['packaging_ref'] = supplier.packaging_ref
                packaging_quantity['quantity'] = total_quantity*int(supplier.packaging_consumption)
                packaging_quantities.append(packaging_quantity)
              

        return {'total_quantity': total_quantity, 'fabric_quantities': fabric_quantities, 'trimming_quantities': trimming_quantities, 'packaging_quantities': packaging_quantities}
    except:
        return None


def get_old_quantities_unitprice(fabric_quantities, trimming_quantities,packaging_quantities):
    # this function returns a dictionary of old quantity values and other details of fabric/trimming/packaging
    # data is gathered by functions in stock.py
    fabric_details = []
    trimming_details = []
    packaging_details = []

    for fab_quantity in fabric_quantities:
        order =frappe.get_doc({
            'doctype':'Item Supplier',
            'fabric_ref': fab_quantity['fabric_ref']
        })
        fabric_detail = get_details_fabric_from_order(order)
        fabric_detail['fab_quantity']=fab_quantity['quantity']
        fabric_details.append(fabric_detail)

    for trim_quantity in trimming_quantities:
        order =frappe.get_doc({
            'doctype':'Item Supplier',
            'trimming_ref': trim_quantity['trimming_ref']
        })
       
        trimming_detail = get_details_trimming_from_order(order, "production")
        trimming_detail['trim_quantity']=trim_quantity['quantity']
        trimming_details.append(trimming_detail)

    for pack_quantity in packaging_quantities:
        order =frappe.get_doc({
            'doctype':'Item Supplier',
            'packaging_ref': pack_quantity['packaging_ref']
        })
        packaging_detail = get_details_packaging_from_order(order, "production")
        if(packaging_detail== None):
            return None
        packaging_detail['pack_quantity']=pack_quantity['quantity']
        packaging_details.append(packaging_detail)

    return {'fabric_details': fabric_details, 'trimming_details': trimming_details, 'packaging_details': packaging_details}


def calculate_price(products):
    # request format,
    #  products = {'0001':{'XS':1,'S':2},'0002':{'M':3}}

    # response format
    # { '0001':233123,'0002':3424324, 'total':321321313}

    prices = {}
    perpiece = {}
    for p in products:
        prices[p] = 0
        for s in products[p]:
            qty = products[p][s]
            price = frappe.get_list('Prices for Quantity', filters={
                                    'parent': p, 'from': ['<=', qty], 'to': ['>=', qty]}, fields=['price'])
            if(len(price) > 0):
                prices[p] += price[0]['price']*float(qty)
                perpiece[p] = price[0]['price']

    total = 0
    for p in prices:
        total += float(prices[p])
    prices['total'] = total
    prices['perpiece'] = perpiece
    return prices


def get_size_order(order):
    # this returns a dictionary of size quantities with product name
    # output of this function can be used in calculate_price function
    size_order = {}
    size_order.update([(order.product_name, {})])
    if order.free_size_qty != None:
        size_order[order.product_name].update([("",order.free_size_qty)])
    else:
        for size in order.quantity_per_size:
            size_order[order.product_name].update(
                [(size.size, int(size.quantity))])
    return size_order


@frappe.whitelist()
def submitPaymentProof(data):
    data = json.loads(data)
    orderName=data['order']
    order=frappe.get_doc("Production Order",orderName)

    order.payment_proof=data['payment_proof']
    order.save()
    return order



@frappe.whitelist()
def createShipmentOrderForProduction(data):
    data = json.loads(data)
    user = frappe.get_doc('User', frappe.session.user)
    brand = user.brand_name
    if (len(data['tracking_number'].strip())==0 or len(data['internal_ref_prod_order'].strip())==0 ):
        return {"status":"error","message":"Incompleted data !"}
    shipmentOrder=frappe.get_doc({
        'doctype': 'Shipment Order',
        'tracking_number':data['tracking_number'],
        'carrier_company':data['carrier_company'],
        'shipping_date':data['shipping_date'],
        'expected_delivery_date':data['expected_delivery_date'],
        'shipping_price':data['shipping_price'],
        'html_tracking_link':data['html_tracking_link'],
        # internal_ref_prod_order shoul be None if that particular shipment is a another kind of shipment but product
        'internal_ref_prod_order':data['internal_ref_prod_order'],
        # Sales order item is none the production order is bulk order
        'sales_order_item':data["sales_order_item"],
        'shipping_document':data['shipping_document'],
        'brand':brand
    })
    order = shipmentOrder.insert()
    frappe.db.commit()
    return {"status":"ok","name":order.name}

# def size_quantity_validation_for_shipment(size_qty_obj,internal_ref_prod_order):

#     prod_order_list = frappe.get_all("Production Order",{"internal_ref":internal_ref_prod_order},["product_name"])
#     if len(prod_order_list)==0:
#         return False
#     stock_doc = frappe.get_doc("Sizing Scheme",frappe.get_doc("Item",prod_order_list[0].product_name).sizing)
#     count = 0
#     is_not_enogh = False
#     for size_req in size_qty_obj:
#         for real_sizing in stock_doc.sizing:
#             if size_req == real_sizing.size:
#                 count = count + 1
    
#     if (count!=len(size_qty_obj.keys())):
#         return False,"Error of data !"

#     return True,None

@frappe.whitelist()
def modifyShipmentOrderForProduction(data,shipment_order):
    data = json.loads(data)
    user = frappe.get_doc('User', frappe.session.user)
    brand = user.brand_name
    shipment_doc = check_shipment_validation_for_dispatch(shipment_order,brand)

    if shipment_doc==None or (len(data['tracking_number'].strip())==0 or len(data['internal_ref_prod_order'].strip())==0 ):
        return {"status":"error","message":"Incompleted data !"}
    shipment_doc.tracking_number = data['tracking_number']
    shipment_doc.carrier_company = data['carrier_company']
    shipment_doc.shipping_date = data['shipping_date']
    shipment_doc.expected_delivery_date = data['expected_delivery_date']
    shipment_doc.shipping_price = data['shipping_price']
    shipment_doc.html_tracking_link = data['html_tracking_link']
    if "shipping_document" in data:
        shipment_doc.shipping_document = data["shipping_document"]
    shipment_doc.save()
    frappe.db.commit()
    return {"status":"ok"}

def check_shipment_validation_for_dispatch(shipment_order,brand):
    shipments = frappe.get_all("Shipment Order",{"brand":brand,"name":shipment_order})
    if len(shipments)==0:
        return None
    return frappe.get_doc("Shipment Order",shipment_order)

@frappe.whitelist()
def cancelDispatch(po,soi):
    if soi!="null":
        frappe.db.set_value('Sales Order Item', soi, {
            'docstatus': 2,
        })
    else:
        frappe.db.set_value('Production Order', po, {
            'docstatus': 2,
        })
    frappe.db.commit()
    return {"status":"ok"}

@frappe.whitelist()
def createShipmentOrderForProductionDispatch(data,dispatch_name):
    data_dic = json.loads(data)
    user = frappe.get_doc('User', frappe.session.user)
    brand = user.brand_name
    dispatch_names = frappe.get_all("Dispatch Bulk Stock History",{"name":dispatch_name},["name"])
    if len(dispatch_names)!=1:
        return {"status":"error"}
    dispatch_doc = frappe.get_doc("Dispatch Bulk Stock History",dispatch_name)
    shipment_order_result = createShipmentOrderForProduction(data)
    if shipment_order_result["status"]!="ok":
        return {"status":"error"}
    dispatch_doc.shipment_order = shipment_order_result["name"]
    dispatch_doc.save()
    frappe.db.commit()
    return {"status":"ok"}

@frappe.whitelist()
def generateMultiplePLInvoice(data):
    # data = [ {
    #     "po_if": "23435434596a" , 
    #     "sales_order_item": "ea2d6f296a" ,
    #     "shipment_order": "11111" , 
    #     "size_qty": { "M":"9","S":"2"} 
    # } , { }, { } ] 
    data = data.replace("null", "None")
    data = ast.literal_eval(data)
    brand_doc = frappe.get_all("User", filters={ "name": frappe.session.user}, fields=["user_image", "address1", "name","brand_name","tax_id"])[0]
    expected_success = len(data)
    actual_success = 0
    for order in data:
        if order["po_if"]==None:
            continue
        doc_data = collect_doc_data(order,brand_doc)
        if doc_data["production_order"] == None or doc_data["client"] == None or doc_data["destination"] == None:
            continue
        size_qty_dic = order["size_qty"]
        is_completed = False
        try:
            for size in size_qty_dic:
                size_qty_dic[size] = int(size_qty_dic[size])
            size_qty_dic, is_completed = check_dispatch_order_situation(doc_data["production_order"],doc_data["sales_order_item"],size_qty_dic)
        except ValueError:
            continue
        if not is_quantity_enough(size_qty_dic,doc_data["production_order"].product_name) or all(x == 0 for x in size_qty_dic.values()) :
            continue
        doc_data["brand"] = brand_doc
        doc_data["size_qty"] = size_qty_dic
        try:
            pl = generate_dispatch_bulk_pl(doc_data)
            invoice = generate_dispatch_bulk_invoice(doc_data)
            modify_stocks_dispatch_bulk(pl.name,invoice.name,doc_data)
            if is_completed: complete_order(doc_data["production_order"],doc_data["sales_order_item"])
            actual_success = actual_success + 1
        except Exception:
            continue
    if actual_success==expected_success:
        return {"status":"ok"}
    else:
        return {"status":"error","message":"Only "+str(actual_success)+" PL and Invoices are created"}

def check_and_get_doc(doc_type,filter_params):
    if filter_params==None:
        return None
    doc_list = frappe.get_all(doc_type,filter_params,["name"])
    if len(doc_list)==0:
        return None
    return frappe.get_doc(doc_type,doc_list[0].name)

def collect_doc_data(order,brand_doc):
    sales_order_item_doc = None
    if order["sales_order_item"] != None:
        sales_order_item_doc = check_and_get_doc("Sales Order Item",{"name":order["sales_order_item"],"docstatus":1}) 
    shipment_order_doc = None
    if order["shipment_order"] != None:
        shipment_order_doc = check_and_get_doc("Shipment Order",{"name":order["shipment_order"],"brand":brand_doc.brand_name,"docstatus":0}) 
    production_order_doc = check_and_get_doc("Production Order",{"name":order["po_if"],"brand":brand_doc.brand_name,"docstatus":1})
    client_name = None
    client_doc = None
    destination_pos_doc = None
    if sales_order_item_doc!=None:
        destination_pos_doc = check_and_get_doc("Destination",{"name":sales_order_item_doc.item_destination})
        if destination_pos_doc!=None : client_name = destination_pos_doc.client_name
    elif production_order_doc!=None:
        if int(production_order_doc.destination_type)==1:
            destination_pos_doc = check_and_get_doc("Point Of Sales",{"name":production_order_doc.final_destination})
            if destination_pos_doc!=None : client_name = destination_pos_doc.parent_company
        elif int(production_order_doc.destination_type)==0:
            destination_pos_doc = check_and_get_doc("Destination",{"name":production_order_doc.final_destination})
            if destination_pos_doc!=None : client_name = destination_pos_doc.client_name
    if client_name!=None:
        client_doc = check_and_get_doc("Customer",{"name":client_name})
    return {
        "sales_order_item" : sales_order_item_doc,
        "production_order" : production_order_doc,
        "shipment_order"   : shipment_order_doc,
        "destination"      : destination_pos_doc,
        "client"           : client_doc   
        }

def is_quantity_enough(size_qty_dic,item_code):
    if size_qty_dic==None or item_code==None:
        return False
    stock_doc = check_and_get_doc("Stock",{"item_type":"product","product":item_code})
    if stock_doc==None:
        return False
    enough = True
    if len(stock_doc.product_stock_per_size)>0:
        for stock in stock_doc.product_stock_per_size:
            for size in size_qty_dic:
                if size==stock.size and  size_qty_dic[size]>int(stock.quantity):
                    enough = False
                    break
            if not enough :
                break
    elif free_size_name in size_qty_dic:
        if stock_doc.quantity<size_qty_dic[free_size_name]:
            enough = False
    else:
        enough = False
    return enough

def check_dispatch_order_situation(po,soi,size_qty):
    requested_quantity,history_list = get_requested_n_requested_qty(soi,po)
    stock_history_list = []
    for history_movement in history_list:
        stock_history = check_and_get_doc("Stock History",{"name":history_movement.stock_history})
        if stock_history!=None : 
            if len(stock_history.product_stock_history_per_size)>0:
                stock_history_list.append(stock_history.product_stock_history_per_size)
            else:
                stock_history_list.append([{"quantity":int(stock_history.quantity),"size":free_size_name}])
    for history in stock_history_list:
        for history_qps in history:
            for qps in requested_quantity:
                if qps['size']==history_qps.size:
                    qps['quantity']  = int(qps['quantity']) - int(history_qps.quantity)
                    if int(qps['quantity'])<0:qps['quantity'] = 0
                    break
    required_quantity = requested_quantity
    is_completed = True
    for size in size_qty:
        for sq in required_quantity:
            if size!=sq["size"]:
                continue
            if size_qty[size]<int(sq["quantity"]):
                is_completed=False
            else:
                size_qty[size] = int(sq["quantity"])
            break
        else:
            size_qty[size] = 0
    return size_qty,is_completed

def get_requested_n_requested_qty(soi,po):
    if po.free_size_qty!=None and soi!=None:
        filter_param = {"is_bulk":"0","sales_order":soi.name}
        requested_quantity = [{"quantity":int(po.free_size_qty),"size":free_size_name}]
    elif po.free_size_qty==None and soi!=None:
        filter_param = {"is_bulk":"0","sales_order":soi.name}
        requested_quantity = convert_obj_to_size_quantity_dic(frappe.get_all("Quantity Per Size",{"order_id":soi.name},["size","quantity"]))
    elif po.free_size_qty==None:
        filter_param = {"is_bulk":"1","bulk_order":po.name}
        requested_quantity = convert_obj_to_size_quantity_dic(po.quantity_per_size)
    else:
        filter_param = {"is_bulk":"1","bulk_order":po.name}
        requested_quantity = [{"quantity":int(po.free_size_qty),"size":free_size_name}]
    history_list = frappe.get_all("Dispatch Bulk Stock History",filter_param,["stock_history"])
    return requested_quantity,history_list

def convert_obj_to_size_quantity_dic(obj_list):
    result = []
    for obj in obj_list:
        result.append({"size":obj.size,"quantity":obj.quantity})
    return result
def generate_dispatch_bulk_pl(doc_data):
    pl_data = create_pl_data_dispatch_bulk(doc_data)
    # temp = frappe.get_all("Pdf Document", filters={"type": "Bulk Order Packing List"}, fields=["content", "type", "name"])
    temp = 'erpnext/www/doc-templates/documents/bilk_order_pl.html'
    # if len(temp)==0:
    #     return None
    generatedPl = frappe.render_template(temp, pl_data)
    invoice = frappe.get_doc({
        'doctype': 'Packing List',
        'content': generatedPl,
        'brand': doc_data["brand"].brand_name,
        'client':doc_data["client"].name
    })
    invoice.insert()
    frappe.db.commit()
    return invoice    

def generate_dispatch_bulk_invoice(doc_data):
    invoice_data = create_invocie_data_dispatch_bulk(doc_data)
    temp = frappe.get_all("Pdf Document", filters={"type": "Bulk Order Invoice"}, fields=["content", "type", "name"])
    if len(temp)==0:
        return None
    generatedInv = frappe.render_template(temp[0]['content'], invoice_data)
    invoice = frappe.get_doc({
        'doctype': 'Uniform Invoice',
        'content': generatedInv,
        'brand': doc_data["brand"].brand_name,
        'client':doc_data["client"].name
    })
    invoice.insert()
    frappe.db.commit()
    return invoice

def modify_stocks_dispatch_bulk(pl,inoice,doc_data):
    stock = frappe.get_all("Stock",{"item_type":"product","product":doc_data["production_order"].product_name},)[0]
    stock = frappe.get_doc("Stock",stock["name"])
    amount = 0
    quantity_array = []
    for size in doc_data["size_qty"]:
        quantity_array.append({"size":size,"quantity":doc_data["size_qty"][size]})
        amount = amount + int(doc_data["size_qty"][size])
    is_bulk = 1
    sales_order = None
    shipment = None 
    order_doc = None
    if doc_data["sales_order_item"]!=None: 
        is_bulk=0
        sales_order = doc_data["sales_order_item"].name
        order_doc = doc_data["sales_order_item"]
    else: 
        order_doc  = doc_data["production_order"]
    if doc_data["shipment_order"]!=None:
        shipment = doc_data["shipment_order"].name
    price,size_detail = get_updatestock2_params_for_dispatch(stock,quantity_array)
    stock_history = updateStock2(stock.name, stock.quantity-amount, stock.quantity, "dispatch", price, "dispatch", size_detail,order_doc,'dispatch-bulk')
    data = {
        "is_bulk":is_bulk,
        "stock_history":stock_history.name,
        "sales_order":sales_order,
        "production_order":doc_data["production_order"].name,
        "brand":doc_data["brand"].brand_name,
        "invoice":inoice,
        "packing_list":pl,
        "shipment_order":shipment
    }
    create_dispatch_bulk(data)

def create_dispatch_bulk(doc_data):
    dispatch_doc = {
        "doctype":"Dispatch Bulk Stock History",
        "is_bulk":doc_data["is_bulk"],
        "stock_history":doc_data["stock_history"],
        "sales_order":doc_data["sales_order"],
        "bulk_order":doc_data["production_order"],
        "shipment_order": doc_data["shipment_order"],
        "brand":doc_data["brand"],
        "invoice":doc_data["invoice"],
        "packing_list":doc_data["packing_list"]
    }
    doc = frappe.get_doc(dispatch_doc)
    doc.insert()
    frappe.db.commit()
    return doc

def complete_order(po,soi):
    if soi!=None:
        frappe.db.set_value('Sales Order Item', soi.name, {
            'docstatus': 3,
        })
    else:
        frappe.db.set_value('Production Order', po.name, {
            'docstatus': 3,
        })
    frappe.db.commit()

def create_pl_data_dispatch_bulk(doc_data):
    template_data={}
    size_qty_dic = doc_data["size_qty"]
    brand = doc_data["brand"]
    destination = doc_data["destination"]
    client = doc_data["client"]  
    production_order = doc_data["production_order"]
    shipment_order = doc_data["shipment_order"]
    sales_order_item = doc_data["sales_order_item"]
    template_data["brand_logo"] = brand.user_image     
    template_data["brand_address"] = ""
    if brand.address1 != None: template_data["brand_address"] = doc_data["brand"]
    template_data["creation"] = datetime.datetime.now()
    template_data["client_name"] = client.customer_name
    template_data["client_address"] = doc_data["client"]
    template_data["destination"] = get_address(destination)
    item_doc = check_and_get_doc("Item",{"name":production_order.product_name})
    order_details = {}
    if item_doc!=None:
        order_details[production_order.product_name] = {"product_name":item_doc.item_name}
    else:
        order_details[production_order.product_name] = {"product_name":""}
    order_details[production_order.product_name]["internal_ref"],order_details[production_order.product_name]["order"] = if_order_for_template_from_order( sales_order_item,production_order )
    order_details[production_order.product_name]["size_qty"] = size_qty_dic
    template_data["order_details"] = order_details
    return template_data

def create_invocie_data_dispatch_bulk(doc_data):
    template_data={}
    size_qty_dic = doc_data["size_qty"]
    brand = doc_data["brand"]
    destination = doc_data["destination"]
    client = doc_data["client"]  
    production_order = doc_data["production_order"]
    shipment_order = doc_data["shipment_order"]
    sales_order_item = doc_data["sales_order_item"]
    template_data["brand_address"] = ""
    if brand.address1 != None: template_data["brand_address"] = brand.address1
    template_data["creation"] = datetime.datetime.now()
    template_data["client_name"] = client.customer_name
    template_data["client_address"] = doc_data["client"]
    template_data["destination"] = get_address(destination)
    item_doc = check_and_get_doc("Item",{"name":production_order.product_name})
    order_details = {}
    if item_doc!=None:
        order_details[production_order.product_name] = {"product_name":item_doc.item_name}
    else:
        order_details[production_order.product_name] = {"product_name":""}
    order_details[production_order.product_name]["order_list"] = []
    order_details[production_order.product_name]["order_list"].append(get_order_data_for_invoice(sales_order_item,production_order,size_qty_dic))

    template_data["order_details"] = order_details
    template_data["total_cost"] = order_details[production_order.product_name]["order_list"][0]["total"]
    template_data["shipment_cost"] = 0
    if shipment_order!=None:
        template_data["shipment_cost"] = shipment_order.shipping_price
    template_data["totalAmount"] = float(template_data["shipment_cost"]) + float(template_data["total_cost"])
    template_data["vat_rate"] = 1
    if brand.tax_id==None: pass 
    elif is_number(brand.tax_id): template_data["vat_rate"] = float(brand.tax_id)
    template_data["totalCost"] = template_data["totalAmount"]
    template_data["vatAmount"] = template_data["vat_rate"] * template_data["totalAmount"] / 100
    template_data["totalPay"] = template_data["vatAmount"] + template_data["totalAmount"]

    return template_data

def get_address(obj):
    address = ""
    if obj.address_line_1 != None:
        address = address +obj.address_line_1 + " , "
    if obj.address_line_2 != None:
        address = address +obj.address_line_2
    return address

def get_order_data_for_invoice(sales_order_item,production_order,size_qty_dic):
    order_data = {}
    order_data["internal_ref"],order_data["order"] = if_order_for_template_from_order( sales_order_item,production_order )
    total_price =  calculate_price({production_order.product_name:size_qty_dic})["total"]   
    quantity = 0
    for size in size_qty_dic:
        quantity = quantity + size_qty_dic[size]
    order_data["price_per_unit"] = float(total_price)/quantity
    order_data["quantity"] = quantity
    order_data["total"] = total_price
    return order_data

def if_order_for_template_from_order( sales_order_item,production_order ):
    i_f = ""
    order = ""
    if sales_order_item!=None:
        parent = check_and_get_doc("Sales Order",{"name":sales_order_item.parent})
        if parent!=None and parent.internal_ref!=None:
            i_f = parent.internal_ref
            order = parent.name
        elif parent!=None and parent.internal_ref==None:
            order = parent.name
    else:
        if production_order.internal_ref != None:
            i_f = production_order.internal_ref

        order = production_order.name
    return i_f,order

def is_number(string):
    try:
        float(string)
        return True
    except ValueError:
        return False

def get_updatestock2_params_for_dispatch(stock,quantity_array):
    p = {stock.parent:{}}
    size_details = None
    total_quantity = stock.quantity
    if len(stock.product_stock_per_size)==0 and quantity_array[0]["size"]==free_size_name:
        p[stock.parent][""] = int(quantity_array[0]["quantity"])
        total_quantity = total_quantity + int(quantity_array[0]["quantity"])
    else:
        for sizeqty in quantity_array:
            p[stock.parent][sizeqty["size"]] = int(sizeqty["quantity"])
            total_quantity = total_quantity + int(sizeqty["quantity"])
        size_details = {"old":stock.product_stock_per_size,"new_incoming":p[stock.parent]}
    total_price = calculate_price(p)[stock.parent] + int(stock.total_value)
    return float(total_price)/total_quantity,size_details
