/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { Component,useState } from "@odoo/owl"; 

export class CopyEmbadeCodeDialog extends Component { 
    _onCopycode(embade_code){
        var res = {
            'ecode':embade_code, 
        };
        this.props.confirm(res);
        this.props.close();
    }
    onClickCancel() {
        this.props.close();
    }
}
CopyEmbadeCodeDialog.template = "CopyEmbadeCodeDialog";
CopyEmbadeCodeDialog.props = {
    close: Function,
    title: { type: String, optional: true },
    confirm: { type: Function, optional: true },
    embade_code: { type: String, optional: true },
}
CopyEmbadeCodeDialog.components = { Dialog };