/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class SettingsConfirmationDialog extends ConfirmationDialog {
    _stayHere() {
        if (this.props.stayHere) {
            this.props.stayHere();
        }
        this.props.close();
    }
}
SettingsConfirmationDialog.defaultProps = {
    title: _t("Unsaved changes"),
};
SettingsConfirmationDialog.template = "web.SettingsConfirmationDialog";
SettingsConfirmationDialog.props = {
    ...ConfirmationDialog.props,
    stayHere: { type: Function, optional: true },
};
