/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { AccordionItem } from "@web/core/dropdown/accordion_item"; 
const { Component, useState } = owl;
const cogMenuRegistry = registry.category("cogMenu");
const { onWillStart } = owl;

// import { rpc } from "@web/core/network/rpc";
/**
 * 'Add to board' menu
 *
 * Component consisiting of a toggle button, a text input and an 'Add' button.
 * The first button is simply used to toggle the component and will determine
 * whether the other elements should be rendered.
 * The input will be given the name (or title) of the view that will be added.
 * Finally, the last button will send the name as well as some of the action
 * properties to the server to add the current view (and its context) to the
 * user's dashboard.
 * This component is only available in actions of type 'ir.actions.act_window'.
 * @extends Component
 */
export class AddToBoardMenuBits extends Component {
    setup() {
        this.notification = useService("notification");
         
        this.state = useState({ 
            name: this.env.config.getDisplayName(), 
            dashboards: [], 
            selected_dashboard:false
        });

        onWillStart(async () => {
            const dashboards = await rpc("/get/dashboard/list",{});
            this.state.dashboards = dashboards.dashboards.map((ele) =>
              Object.assign(ele, { isSelected: false })
            );
            this.state.selected_dashboard = dashboards['dashboards'][0].id;
          });
        useAutofocus();
    }

    toggleSelected(ev) {
        var did = parseInt(ev.currentTarget.value);
        this.state.selected_dashboard = did;
        // this.state.dashboards = this.state.dashboards.map((ele) => {
        //   if (ele.id == did) ele.isSelected = !ele.isSelected;
        //   return ele;
        // });
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async addToBoardMenuBits(ev) {
        ev.preventDefault();
        const { domain, globalContext } = this.env.searchModel;
        const { context, groupBys, orderBy } = this.env.searchModel.getPreFavoriteValues();
        const comparison = this.env.searchModel.comparison;
        const contextToSave = {
            ...Object.fromEntries(
                Object.entries(globalContext).filter(
                    (entry) => !entry[0].startsWith("search_default_")
                )
            ),
            ...context,
            orderedBy: orderBy,
            group_by: groupBys,
            dashboard_merge_domains_contexts: false,
        };
        if (comparison) {
            contextToSave.comparison = comparison;
        }
        const result = await rpc("/set/dashboard/action/view", {
            data: {
                action_id: this.env.config.actionId || false,
                context_to_save: JSON.stringify(contextToSave),
                domain: JSON.stringify(domain),
                name: this.state.name,
                view_mode: this.env.config.viewType,
            },
            did: this.state.selected_dashboard
        });
        if (result) {
            this.notification.add(
                _t("Please refresh your browser for the changes to take effect."),
                {
                    title: sprintf(_t(`"%s" added to dashboard`), this.state.name),
                    type: "warning",
                }
            );
        } else {
            this.notification.add(_t("Could not add filter to dashboard"), {
                type: "danger",
            });
        }
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * @param {KeyboardEvent} ev
     */
    onInputKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.addToBoardMenuBits();
        }
    }
}

AddToBoardMenuBits.template = "AddToBoardBits";
AddToBoardMenuBits.components = { AccordionItem };

export const addToBoardMenuBitsItem = {
    Component: AddToBoardMenuBits,
    groupNumber: 4,
    isDisplayed: ({ config }) => {
        const { actionType, actionId, viewType } = config;
        return actionType === "ir.actions.act_window" && actionId && viewType !== "form";
    },
};

cogMenuRegistry.add("add-to-board-bits", addToBoardMenuBitsItem, { sequence: 10 });
