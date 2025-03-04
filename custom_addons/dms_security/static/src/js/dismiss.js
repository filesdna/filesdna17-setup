/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";

// overide the dismiss function to reload the page when closing the authuntication wizard

async function dismiss() {
    if(this.__owl__.props.actionProps){
        if(this.__owl__.props.actionProps.resModel == 'dms.directory.authenticator'){
            location.reload()}
        }
            else if (this.data.dismiss) {
                await this.data.dismiss();
            }
            return this.data.close();
    }
    Dialog.prototype.dismiss = dismiss;



