$(function() {
  if("{{packOrder.confirmation_doc}}"=='None'){
    $('#conf_del').hide()
  }else{
    $('#conf_del').show()
  }
  if("{{packOrder.profoma}}"=='None'){
    $('#profoma_del').hide()
  }else{
    $('#profoma_del').show()
  }
  if("{{packOrder.invoice}}"=='None'){
    $('#invoice_del').hide()
  }else{
    $('#invoice_del').show()
  }
});



$(".display-file-selector").click(function () {
  $(this).next().trigger("click");
});

$("#proofSubmit").click(function () {
  $('.proof').show()
  checkFileUpload("paymentProof").then((res) =>
    frappe.call({
      method: "erpnext.modehero.package.submit_payment_proof",
      args: {
        data: {
          order: "{{frappe.form_dict.order}}",
          payment_proof: res,
          comment: $("#proofComment").val(),
          confirmation_reminder:$.trim($("#conf_reminder").text()),
          proforma_reminder:$.trim($("#prof_reminder").text()),
          payment_reminder:$.trim($("#paym_reminder").text()),
          shipment_reminder:$.trim($("#shipment_reminder").text()),
          reception_reminder:$.trim($("#recep_reminder").text())
        },
      },
      callback: function (r) {
        $('.proof').hide()
        if (!r.exc) {
          console.log(r);
          frappe.msgprint({
            title: __("Notification"),
            indicator: "green",
            message: __(
              "Packaging Order " +
                "{{packOrder.name}}'s" +
                " details updated successfully"
            ),
          });
        }
      },
    })
  );
});

$("#vendorSubmit").click(function () {
  let files = ["confirmation_doc", "profoma", "invoice"];
  $('.vendor').show()

  Promise.all(
    files.map((f) => {
      return checkFileUpload(f);
    })
  )
    .then((files) => {
      console.log(files);
      submitVendorSummary(files);
    })
    .catch((e) => {
      frappe.throw(e);
    });
});

function checkFileUpload(componentId) {
  return new Promise((resolve, reject) => {
    let file = $(`#${componentId}`).prop("files")[0];
    switch (componentId) {
      case "paymentProof":
        if (!file) {
          if ("{{packOrder.payment_proof}}" == null) {
            console.error("payment proof must upload");
          } else {
            filename = "{{packOrder.payment_proof}}";
            resolve(filename);
          }
        } else {
          uploadFile(componentId).then((res) => resolve(res));
        }

        break;
      case "confirmation_doc":
        if (!file) {
          if ("{{packOrder.confirmation_doc}}" == null) {
            console.error("confirmation doc must upload");
          } else {
            filename = "{{packOrder.confirmation_doc}}";
            resolve(filename);
          }
        } else {
          uploadFile(componentId).then((res) => resolve(res));
        }
        break;
      case "profoma":
        if (!file) {
          if ("{{packOrder.profoma}}" == null) {
            console.error("profoma must upload");
          } else {
            filename = "{{packOrder.profoma}}";
            resolve(filename);
          }
        } else {
          uploadFile(componentId).then((res) => resolve(res));
        }

        break;
      case "invoice":
        if (!file) {
          if ("{{packOrder.invoice}}" == null) {
            console.error("invoice must upload");
          } else {
            filename = "{{packOrder.invoice}}";
            resolve(filename);
          }
        } else {
          uploadFile(componentId).then((res) => resolve(res));
        }

        break;
    }
  });
}

function submitVendorSummary(files) {
  frappe.call({
    method: "erpnext.modehero.package.submit_pack_vendor_summary_info",
    args: {
      data: {
        order: "{{frappe.form_dict.order}}",
        ex_work_date: $("#exWorkDate").val(),
        confirmation_doc: files[0],
        profoma: files[1],
        invoice: files[2],
        carrier: $("#carrier").val(),
        tracking_number: $("#tracking_number").val(),
        shipment_date: $("#shipmentDate").val(),
        expected_date: $("#expectedDate").val(),
        shipping_price: $("#shipping_price").val(),
        html_tracking_link: $("#html_tracking_link").val(),
        production_comment: $("#comment").val(),
      },
    },
    callback: function (r) {
      $('.vendor').hide()
      console.log(r)
      if (!r.exc) {
        console.log(r);
        frappe.msgprint({
          title: __("Notification"),
          indicator: "green",
          message: __(
            "Packaging order " +
              "{{packOrder.name}}" +
              " summary created successfully"
          ),
        });
        location.reload()
      } else {
        frappe.msgprint({
          title: __("Notification"),
          indicator: "red",
          message: __(
            "Packaging order " +
              "{{packOrder.name}}" +
              " summary created Failed"
          ),
        });
      }
    },
  });
}

function uploadFile(componentId) {
  return new Promise((resolve, reject) => {
    let file = $(`#${componentId}`).prop("files")[0];
    if (file.size / 1024 / 1024 > 5) {
      reject("Please upload file less than 5mb");
    }
    var reader = new FileReader();
    reader.readAsDataURL(file);
    console.log(file, reader, reader.result);
    reader.onload = function () {
      frappe.call({
        method: "frappe.handler.uploadfile",
        // method: 'erpnext.modehero.sales_order.upload_test',
        args: {
          filename: file.name,
          attached_to_doctype: "Production Order",
          attached_to_field: componentId,
          is_private: true,
          filedata: reader.result,
          from_form: true,
        },
        callback: function (r) {
          if (!r.exc) {
            console.log(r);
            $(`#${componentId}-label`).html(r.message.file_url);
            resolve(r.message.file_url);
          }
        },
      });
    };
  });
}

$("#paymentProof").change(function () {
  $("#payment_proof-label").html($(this).prop("files")[0].name);
});

$("#confirmation_doc").change(function () {
  $("#confirmation_doc-label").html($(this).prop("files")[0].name);
});

$("#profoma").change(function () {
  $("#profoma-label").html($(this).prop("files")[0].name);
});

$("#invoice").change(function () {
  $("#invoice-label").html($(this).prop("files")[0].name);
});


$('#pdf_doc').click(function () {
    
  let page=$('#doc').html()
  render_pdf(page)
})

function render_pdf(html) {
  var formData = new FormData();

//Push the HTML content into an element
  formData.append("html",html);
  // if (opts.orientation) {
// 	formData.append("orientation", opts.orientation);
// }
var blob = new Blob([], { type: "text/xml"});
formData.append("blob", blob);

var xhr = new XMLHttpRequest();
$(".row").css("opacity",0.5);
xhr.open("POST", '/api/method/frappe.utils.print_format.report_to_pdf');
xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);
xhr.responseType = "arraybuffer";

xhr.onload = function(success) {
  if (this.status === 200) {
    $(".row").css("opacity",1);
    var blob = new Blob([success.currentTarget.response], {type: "application/pdf"});
          var objectUrl = URL.createObjectURL(blob);
          window.open(objectUrl);
          // target=`<a href="${objectUrl}">${objectUrl}</a>`
          // $('#order_doc').html(target)

    
    //Open report in a new window
    // window.open(objectUrl);
  }
  else{
    frappe.msgprint({
      title: __("Notification"),
      indicator: "red",
      message: __(
        "Not Permitted"
      ),
    });
    $(".row").css("opacity",1);
  }
  };
  
  xhr.send(formData);
}


$('#conf_del').click(function (){
  deleteFile('confirmation_doc')
})

$('#profoma_del').click(function (){
  deleteFile('profoma')
})
$('#invoice_del').click(function (){
  deleteFile('invoice')
})

function deleteFile(file_type){
  frappe.call({
    method: "erpnext.modehero.package.deleteDoc",
    args: {
      data: {
        order: "{{frappe.form_dict.order}}",
        doc_type:file_type
      },
    },
    callback: function (r) {
      if (!r.exc) {
        console.log(r);
        frappe.msgprint({
          title: __("Notification"),
          indicator: "green",
          message: __(
            file_type+" successfully deleted"
          )
        });
        location.reload()
      }else{
        frappe.msgprint({
          title: __("Notification"),
          indicator: "red",
          message: __(r.message)
        });
      }
    },
  });
}
  
  

