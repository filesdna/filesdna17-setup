/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('account_tax_group', {
    test: true,
    url: "/web",
    steps: () => [stepUtils.showAppsMenuItem(),
    {
        id: 'account_menu_click',
        content: "Go to Invoicing",
        trigger: '.o_app[data-menu-xmlid="account.menu_finance"]',
    },
    {
        content: "Go to Vendors",
        trigger: 'span:contains("Vendors")',
    },
    {
        content: "Go to Bills",
        trigger: 'a:contains("Bills")',
    },
    {
        extra_trigger: '.o_breadcrumb .text-truncate:contains("Bills")',
        content: "Create new bill",
        trigger: '.o_control_panel_main_buttons .d-none .o_list_button_add',
    },
    // Set a vendor
    {
        content: "Add vendor",
        trigger: 'div.o_field_widget.o_field_res_partner_many2one[name="partner_id"] div input',
        run: 'text Account Tax Group Partner',
    },
    {
        content: "Valid vendor",
        trigger: '.ui-menu-item a:contains("Account Tax Group Partner")',
    },
    // Add First product
    {
        content: "Add items",
        trigger: 'div[name="invoice_line_ids"] .o_field_x2many_list_row_add a:contains("Add a line")',
    },
    {
        content: "Select input",
        trigger: 'div[name="invoice_line_ids"] .o_selected_row .o_list_many2one[name="product_id"] input',
    },
    {
        content: "Type item",
        trigger: 'div[name="invoice_line_ids"] .o_selected_row .o_list_many2one[name="product_id"] input',
        run: "text Account Tax Group Product",
    },
    {
        content: "Valid item",
        trigger: '.ui-menu-item-wrapper:contains("Account Tax Group Product")',
    },
    // Save account.move
    {
        content: "Save the account move",
        trigger: '.o_form_button_save',
    },
    ...stepUtils.saveForm(),
    // Edit tax group amount
    {
        content: "Edit tax group amount",
        trigger: '.o_tax_group_edit',
    },
    {
        content: "Modify the input value",
        trigger: '.o_tax_group_edit_input input',
        run: function (actions) {
            $('.o_tax_group_edit_input input').val(200);
            $('.o_tax_group_edit_input input').select();
            $('.o_tax_group_edit_input input').blur();
        },
    },
    // Check new value for total (with modified tax_group_amount).
    {
        content: "Valid total amount",
        trigger: 'span[name="amount_total"]:contains("800")',
    },
    // Modify the quantity of the object
    {
        content: "Select item quantity",
        trigger: 'div[name="invoice_line_ids"] tbody tr.o_data_row .o_list_number[name="quantity"]',
    },
    {
        content: "Change item quantity",
        trigger: 'div[name="invoice_line_ids"] tbody tr.o_data_row .o_list_number[name="quantity"] input',
        run: 'text 2',
    },
    {
        content: "Valid the new value",
        trigger: 'div[name="invoice_line_ids"] tbody tr.o_data_row .o_list_number[name="quantity"] input',
        run: function (actions) {
            let keydownEvent = jQuery.Event('keydown');
            keydownEvent.key = "Enter";
            this.$anchor.trigger(keydownEvent);
        },
    },
    // Save form
    {
        content: "Save the account move",
        trigger: '.o_form_button_save',
    },
    ...stepUtils.saveForm(),
    // Check new tax group value
    {
        content: "Check new value of tax group",
        trigger: '.o_tax_group_amount_value:contains("120")',
    },
    {
        content: "Edit tax value",
        trigger: '.o_tax_group_edit_input input',
        run: 'text 2'
    },
    {
        content: "Check new value of total",
        trigger: '.oe_subtotal_footer_separator:contains("1,202")',
    },
    {
        content: "Discard changes",
        trigger: '.o_form_button_cancel',
    },
    {
        content: "Check tax value is reset",
        trigger: '.o_tax_group_amount_value:contains("120")',
        isCheck: true,
    },
]});
