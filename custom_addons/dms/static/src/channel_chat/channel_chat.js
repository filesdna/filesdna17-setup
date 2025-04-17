/** @odoo-module */

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { WarningDialog } from "@web/core/errors/error_dialogs";

export class ChannelChat extends Component {
    setup() {
        this.threadService = useService("mail.thread");
        this.discussCoreCommonService = useService("discuss.core.common");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");

        this.state = useState({
            channel_id: null,
            channel_name: null,
            isVisible: true, // Initially the widget is visible
        });

        // Handle visibility based on the `is_section` prop
        if (this.props.is_section) {
            this.state.isVisible = false;  // Hide widget if is_section is true
        }
    }

    checkPermission() {
        return this.props.record.data['request_access'] || false;
    }

    async openChat() {
        if (!this.checkPermission()) {
            this.dialogService.add(WarningDialog, {
                title: _t("Permission Denied"),
                message: _t("You don't have permission to access this, please close!"),
            });
            return;
        }

        const { record } = this.props;
        const model = record.resModel;
        let channel = record.data['channel_id'];
        let recordName = record.data['name'];
        console.log("recordName:",recordName)
        if (model === 'itrack.assignment') {
            recordName = record.data['user_id'][1] || recordName;
            recordName = 'Private Chat for ' + recordName;
        } else {
            recordName = 'Public Chat for ' + recordName;
        }

        if (this.state.channel_id) {
            channel = [this.state.channel_id, this.state.channel_name];
        }

        if (!channel) {
            try {
                const data = await this.orm.call("discuss.channel", "channel_create", [recordName, null]);
                this.state.channel_id = data.id;
                this.state.channel_name = recordName;

                await this.orm.call(model, "refresh_channel", [[record.resId], data.id, true]);
                const channelThread = this.discussCoreCommonService.createChannelThread(data);
                this.threadService.open(channelThread);
            } catch (error) {
                console.error("Error creating or refreshing channel:", error);
            }
        } else {
            try {
                await this.orm.call(model, "refresh_channel", [[record.resId], channel[0], false]);
                this.threadService.joinChannel(channel[0], channel[1]);
            } catch (error) {
                console.error("Error joining channel:", error);
            }
        }
    }
}

ChannelChat.props = {
    ...standardWidgetProps,
    hideComponent: { type: Boolean, optional: true },
    showButton: { type: String, optional: true },
    buttonName: { type: String, optional: true },
    is_section: { type: Boolean, optional: true, default: false },  // Define is_section as a boolean
    record: { type: Object, optional: true },
};

ChannelChat.template = "pds_document_track_eat.ChannelChat";

export const channelChat = {
    component: ChannelChat,
    extractProps: ({ attrs }) => ({
        showButton: attrs.show_button,
        buttonName: attrs.button_name,
        hideComponent: Boolean(attrs.hide_component),
        is_section: Boolean(attrs.is_section),  // Ensure is_section is passed correctly
        record: attrs.record, // Pass the record object as a prop to the component
    }),
};

registry.category("view_widgets").add("channel_chat", channelChat);

