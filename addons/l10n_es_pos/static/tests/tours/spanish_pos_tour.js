/** @odoo-module */

import * as ErrorPopup from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as PartnerListScreen from "@point_of_sale/../tests/tours/helpers/PartnerListScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as Utils from "@point_of_sale/../tests/tours/helpers/utils";
import { registry } from "@web/core/registry";
import { checkSimplifiedInvoiceNumber, pay } from "./helpers/receipt_helpers";

const SIMPLIFIED_INVOICE_LIMIT = 1000;

registry.category("web_tour.tours").add("spanish_pos_tour", {
    test: true,
    steps: () => [
        ...ProductScreen.confirmOpeningPopup(),

        ...ProductScreen.addOrderline("Desk Pad", "1"),
        ...pay(),
        ...checkSimplifiedInvoiceNumber("0001"),
        ...ReceiptScreen.clickNextOrder(),

        ...ProductScreen.addOrderline("Desk Pad", "1", SIMPLIFIED_INVOICE_LIMIT - 1),
        ...pay(),
        ...checkSimplifiedInvoiceNumber("0002"),
        ...ReceiptScreen.clickNextOrder(),

        ...ProductScreen.addOrderline("Desk Pad", "1", SIMPLIFIED_INVOICE_LIMIT + 1),
        ...pay(),
        ...ErrorPopup.isShown(),
        ...ErrorPopup.clickConfirm(),

        ...PaymentScreen.clickInvoiceButton(),
        ...PaymentScreen.clickValidate(),
        {
            content: "verify that the pos requires the selection of a partner",
            trigger: `div.popup.popup-confirm .modal-header:contains('Please select the Customer') ~ footer div.button.confirm`,
        },

        ...PartnerListScreen.clickPartner(""),

        ...PaymentScreen.isInvoiceOptionSelected(),
        ...PaymentScreen.clickValidate(),
        {
            content:
                "verify that the simplified invoice number does not appear on the receipt, because this order is invoiced, so it does not have a simplified invoice number",
            trigger: ".receipt-screen:not(:has(.simplified-invoice-number))",
            isCheck: true,
        },
        ...ReceiptScreen.clickNextOrder(),

        ...ProductScreen.addOrderline("Desk Pad", "1"),
        ...pay(),
        ...checkSimplifiedInvoiceNumber("0003"),

        ...ReceiptScreen.clickNextOrder(),
        ...ProductScreen.addOrderline("Desk Pad", "1"),
        ...ProductScreen.clickPayButton(),
        ...PaymentScreen.clickPaymentMethod("Customer Account"),
        ...PaymentScreen.clickValidate(),
        {
            content: "verify that the pos requires the selection of a partner",
            trigger: `div.popup.popup-confirm .modal-header:contains('Customer Required')`,
        },
    ],
});

registry.category("web_tour.tours").add("l10n_es_pos_settle_account_due", {
    test: true,
    steps: () =>
        [
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickPartnerButton(),
            PartnerListScreen.clickPartnerDetailsButton("Partner Test 1"),
            {
                trigger: `.button:contains("Settle due accounts")`,
            },
            Utils.selectButton("Bank"),
            PaymentScreen.clickValidate(),
            Chrome.confirmPopup(),
            ReceiptScreen.isShown(),
        ].flat(),
});
