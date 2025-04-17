/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { Component,useRef,useState,useEffect } from "@odoo/owl";

export class FaIconsDialogBits extends Component {
    setup() {
        this.state = useState({
            'iconsList':this.props.iconsList,
            'SelectedIcon':false
        }) 
    } 
    onSelectIcon(e,icon){ 
        this.state.SelectedIcon = icon;
    } 
    onSearchInput(e) {
        var self = this
        if(e.target.value){
            this.state.iconsList = this.props.iconsList.filter(icon => icon.toLowerCase().includes(e.target.value.toLowerCase()));
        }
    }
    async _onSelectIcon(e){
        let icon = '';
        try {
            if(this.props.is_mid){
                icon = this.state.SelectedIcon ? this.state.SelectedIcon : '';
            }else{
                icon = this.state.SelectedIcon ? 'fa-'+this.state.SelectedIcon : '';
            }
            
            await this.props.confirm(icon); 
        } catch (e) {
            this.props.close();
        }
        this.props.close();
    }
}
FaIconsDialogBits.template = "IconDialogBits";
FaIconsDialogBits.props = {
    close: Function,
    confirm: { type: Function, optional: true },
    iconsList: { type: Object, optional: true },
    is_mid:{type:Boolean,optional:true}
}
FaIconsDialogBits.components = { Dialog };