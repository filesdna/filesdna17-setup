/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { makeContext } from "@web/core/context";
import { session } from "@web/session";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

export const STATIC_ACTIONS_GROUP_NUMBER = 1;
export const ACTIONS_GROUP_NUMBER = 100;

/**
 * Action menus (or Action/Print bar, previously called 'Sidebar')
 *
 * The side bar is the group of dropdown menus located on the left side of the
 * control panel. Its role is to display a list of items depending on the view
 * type and selected records and to execute a set of actions on active records.
 * It is made out of 2 dropdown: Print and Action.
 *
 * @extends Component
 */
export class ActionMenus extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        onWillStart(async () => {
            this.actionItems = await this.getActionItems(this.props);
        });
        onWillUpdateProps(async (nextProps) => {
            this.actionItems = await this.getActionItems(nextProps);
        });
    }

    get printItems() {
        const printActions = this.props.items.print || [];
        return printActions.map((action) => ({
            action,
            description: action.name,
            key: action.id,
        }));
    }

    //---------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------

    async getActionItems(props) {
        return (props.items.action || []).map((action) => {
            if (action.callback) {
                return Object.assign(
                    { key: `action-${action.description}`, groupNumber: ACTIONS_GROUP_NUMBER },
                    action
                );
            } else {
                return {
                    action,
                    description: action.name,
                    key: action.id,
                    groupNumber: action.groupNumber || ACTIONS_GROUP_NUMBER,
                };
            }
        });
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    async executeAction(action) {
        let activeIds = this.props.getActiveIds();
        if (this.props.isDomainSelected) {
            activeIds = await this.orm.search(this.props.resModel, this.props.domain, {
                limit: session.active_ids_limit,
                context: this.props.context,
            });
        }
        const activeIdsContext = {
            active_id: activeIds[0],
            active_ids: activeIds,
            active_model: this.props.resModel,
        };
        if (this.props.domain) {
            // keep active_domain in context for backward compatibility
            // reasons, and to allow actions to bypass the active_ids_limit
            activeIdsContext.active_domain = this.props.domain;
        }
        const context = makeContext([this.props.context, activeIdsContext]);
        return this.actionService.doAction(action.id, {
            additionalContext: context,
            onClose: this.props.onActionExecuted,
        });
    }

    /**
     * Handler used to determine which way must be used to execute a selected
     * action: it will be either:
     * - a callback (function given by the view controller);
     * - an action ID (string);
     * - an URL (string).
     * @private
     * @param {Object} item
     */
    async onItemSelected(item) {
        if (!(await this.props.shouldExecuteAction(item))) {
            return;
        }
        if (item.callback) {
            item.callback([item]);
        } else if (item.action) {
            this.executeAction(item.action);
        } else if (item.url) {
            // Event has been prevented at its source: we need to redirect manually.
            browser.location = item.url;
        }
    }
}

ActionMenus.components = {
    Dropdown,
    DropdownItem,
};
ActionMenus.props = {
    getActiveIds: Function,
    context: Object,
    resModel: String,
    domain: { type: Array, optional: true },
    isDomainSelected: { type: Boolean, optional: true },
    items: {
        type: Object,
        shape: {
            action: { type: Array, optional: true },
            print: { type: Array, optional: true },
        },
    },
    onActionExecuted: { type: Function, optional: true },
    shouldExecuteAction: { type: Function, optional: true },
};
ActionMenus.defaultProps = {
    onActionExecuted: () => {},
    shouldExecuteAction: () => true,
};
ActionMenus.template = "web.ActionMenus";
