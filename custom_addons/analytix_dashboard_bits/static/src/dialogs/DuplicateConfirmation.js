/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { Component,useState } from "@odoo/owl"; 

export class DuplicateConfirmation extends Component {
    setup() {
        this.dashbId = this.props.dashboards[0].id;
    }   
    async _onSelectDashboard(e){
        var dashId = parseInt(e.currentTarget.value);
        this.dashbId = dashId;  
    }
    _onSelectMove(action){
        var res = {
            'action':action,
            'dashboard_id':this.dashbId,
            'record_id':this.props.record_id
        };
        this.props.confirm(res);
        this.props.close();
    }
}
DuplicateConfirmation.template = "DuplicateConfirmation";
DuplicateConfirmation.props = {
    title: { type: String, optional: true },
    close: { type: Function, optional: true },
    confirm: { type: Function, optional: true },
    dashboards: { type: Object, optional: true },
    record_id:{type:Number,optional:true},
}
DuplicateConfirmation.components = { Dialog };