frappe.ready(function () {
	// bind events here

	setTimeout(() => {
		frappe.call({
			method: 'erpnext.modehero.user.get_brand',
			args: {
				user: frappe.session.user
			},
			callback: function (r) {
				if (!r.exc) {
					console.log(r.message)
					frappe.web_form.set_value('brand_name', r.message)
					frappe.web_form.set_df_property('brand_name', 'hidden', true);
				}
			}
		});
	}, 500);
})