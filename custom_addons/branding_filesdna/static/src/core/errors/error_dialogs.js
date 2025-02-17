/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ErrorDialog, ClientErrorDialog, NetworkErrorDialog, RPCErrorDialog, WarningDialog, RedirectWarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";

// Patch ErrorDialog
patch(ErrorDialog.prototype, {
    setup() {
        this._super();
    },
    title: _t("Filesdna Error"),
});

// Patch ClientErrorDialog
patch(ClientErrorDialog.prototype, {
    title: _t("Filesdna Client Error"),
});

// Patch NetworkErrorDialog
patch(NetworkErrorDialog.prototype, {
    title: _t("Filesdna Network Error"),
});

// Patch RPCErrorDialog
patch(RPCErrorDialog.prototype, {
    inferTitle() {
        if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
            this.title = odooExceptionTitleMap.get(this.props.exceptionName).toString();
            return;
        }
        if (!this.props.type) {
            return;
        }
        switch (this.props.type) {
            case "server":
                this.title = _t("Filesdna Server Error");
                break;
            case "script":
                this.title = _t("Filesdna Client Error");
                break;
            case "network":
                this.title = _t("Filesdna Network Error");
                break;
        }
    },
});

// Patch WarningDialog
patch(WarningDialog.prototype, {
    inferTitle() {
        if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
            return odooExceptionTitleMap.get(this.props.exceptionName).toString();
        }
        return this.props.title || _t("Filesdna Warning");
    },
});

// Patch RedirectWarningDialog
patch(RedirectWarningDialog.prototype, {
    setup() {
        this._super();
        this.title = _t("Filesdna Warning");
    },
});
