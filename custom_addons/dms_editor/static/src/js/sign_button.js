/** @odoo-module */

import { FormRenderer } from '@web/views/form/form_renderer';
import { useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { onMounted, onPatched, useEnv , onWillStart} = owl;

patch(FormRenderer.prototype, {
    setup(...args) {
        super.setup(...args);
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.file  = useState({ 
            extension: null, 
            id: null,
            active_model : null,
            owner_lock : null,
        });
        
        onWillStart(this.onWillStart);
        onPatched(this._renderSignButton.bind(this));
        onMounted(this._renderSignButton.bind(this));                
    },

    async onWillStart() {
        var record_id = this.props.record.evalContext.active_id
        this.file.active_model = this.props.record.evalContext.active_model
        const file_id = await this.orm.call("dms.file", "search_read", [[['id', '=',record_id ]], ['extension','owner_lock']], {});
        if (file_id[0]) {
            
            this.file.extension = file_id[0].extension;
            this.file.id = file_id[0].id;
            this.file.owner_lock = file_id[0].owner_lock;
        }
        
    },
    
    _renderSignButton(){
        if (this.file.extension === 'pdf' & this.file.active_model === 'dms.file' & this.file.owner_lock === false){
            const $signbutton = $('<div>');
            $signbutton.addClass("sign_print_report");
            $signbutton.append($('<button>').addClass("btn btn-primary").append($('<i class="fa fa-file-signatire"/>')));
            $signbutton.on('click', this._clickSignButton.bind(this));
            const $sheet = $('.o_form_sheet');
            if (this.props.record.resId){
                $sheet.append($signbutton);
            }            
        }
    },

    async _clickSignButton(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;
        this.orm.call('dms.file', 'action_edit', [this.file.id], {})
        .then((result) => {
            window.location.href = result.url
        });
    },

    


})

export default FormRenderer;
