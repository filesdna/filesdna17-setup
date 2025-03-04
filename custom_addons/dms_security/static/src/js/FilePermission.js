/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class NotificationLoop extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.record_id = this.props.action.params.record_id;
        this.message_id = this.props.action.params.message_id;
        this.message = useState({ text: "Please make sure you are opening the Mobile app" });
        this.attempts = useState({ count: 31 });
        this.securityType = useState({ type: null,
            tag : null,
            text : null
         });
        this.detect_type()
    }
    
    async detect_type(){
        const result = await this.rpc('/user/fcm/check_notification_status', { record_id: this.record_id });
        this.securityType.type = result.security_type
    }

    async startLoop() {
        const updateProgress = () => {
            const progressBar = document.getElementById("progressBar");
            if (progressBar) {
                progressBar.value = this.attempts.count;
            }
        };

        const checkStatus = async () => {
            const result = await this.rpc('/user/fcm/check_notification_status', { record_id: this.record_id });

            this.attempts.count--;
            this.securityType.type = result.security_type;

            if (result.security_type === "nfc") {
                this.message.text = `Pass your Card on your phone to open this file`;
            } else if (result.security_type === "ma") {
                this.message.text = `Press allow on your phone to open this file`;
            } else if (result.security_type === "fp") {
                this.message.text = `Biometric login : Scan your fingerprint`;
            }

            await this.orm.call("message.wizard", "write", [[this.message_id], { message: this.message.text }]);
            console.log('notification result',result.notification_status)
            if (result.notification_status === "delivered") {
                this.action.doAction({
                    type: "ir.actions.act_window",
                    name: _t("DMS File"),
                    res_model: "dms.file",
                    views: [[false, 'form']],
                    res_id: this.record_id,
                    target: "current",
                });
            await this.orm.call("dms.file", "write", [[this.record_id], { notification_status: "pending" }]);
            } else if (this.attempts.count > 0) {
                setTimeout(checkStatus, 1000);
            } else {
                this.message.text = "Failed to detect, Please try again";
            }
        };

        checkStatus();
    }

    tryAgain() {
        this.attempts.count = 31;
        this.message.text = "Please make sure your FilesDNA Mobile app is open";
    }

    async startProcess() {
        const result = await this.rpc('/user/fcm/check_notification_status', { record_id: this.record_id });
        this.attempts.count = 30;
        this.securityType.type = result.security_type;
        if (result.security_type === "nfc") {
            this.securityType.tag = "nfc_dms";
            this.securityType.text = "Mobile NFC";
            this.message.text = "Pass your Card to open this file";
        } else if (result.security_type === "ma") {
            this.securityType.tag  = "ma_dms";
            this.securityType.text  = "Mobile Verification";
            this.message.text = `You have to allow it from your mobile to get access to this file`;
        } else if (result.security_type === "fp") {
            this.securityType.tag  = "fp_dms";
            this.securityType.text  = "Mobile FingerPrint";
            this.message.text = `Scan your fingerprint to get access to this file`;
        }
        this.orm.call('dms.file', 'fcm_method', [this.record_id,this.securityType.tag, 'File Security'], {})
            .then((result) => {
                this.startLoop();
            });
  
    }

}



NotificationLoop.template = "dms_security.NotificationLoop";
registry.category("actions").add("notification_loop", NotificationLoop);
