/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ImageField } from '@web/views/fields/image/image_field';
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ImageUsersWebcamDialog } from "./image_users_webcam_dialog"

patch(ImageField.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    onUsersWebcam(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        var self = this;
        if (window.location.protocol == 'https:') {
            self.dialog.add(ImageUsersWebcamDialog, {
                uploadWebcamUserImage: (data) => this.uploadWebcamUserImage(data),
            });
        }else{
            self.notification.add(_t("WEBCAM MAY ONLY WORKS WITH HTTPS CONNECTIONS. So your Odoo instance must be configured in https mode."), {
                type: 'danger',
            });
        }
    },

    async uploadWebcamUserImage({ data }) {
        if (data){
            data = data.split(',')[1];
            return this.props.record.update({ [this.props.name]: data || false });
        }
    }

});
