/** @odoo-module **/

import { SearchModel } from "@web/search/search_model";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { useGetDomainTreeDescription } from "@web/core/domain_selector/utils";
const { DateTime } = luxon;
import {
    constructDateDomain,
    DEFAULT_INTERVAL,
    getComparisonOptions,
    getIntervalOptions,
    getPeriodOptions,
    rankInterval,
    yearSelected,
} from "@web/search/utils/dates";

// Override the setup function to assign the necessary services and the action needed in _fetchCategories
function setup(services) {
    const { field: fieldService, name: nameService, orm, user, view } = services;

    // Assign services
    this.orm = orm;
    this.action = useService("action");
    this.fieldService = fieldService;
    this.userService = user;
    this.viewService = view;

    // Domain tree description
    this.getDomainTreeDescription = useGetDomainTreeDescription(fieldService, nameService);

    // Used to manage search items related to date/datetime fields
    this.referenceMoment = DateTime.local();
    this.comparisonOptions = getComparisonOptions();
    this.intervalOptions = getIntervalOptions();
    this.optionGenerators = getPeriodOptions(this.referenceMoment);
}

SearchModel.prototype.setup = setup;

// Override the _fetchCategories function to pop up the authentication wizard if the directory has a security level
async function _fetchCategories(categories) {
    // Check if the resModel is 'dms.file' and has a search panel domain
    if (this.resModel === 'dms.file' && this._getSearchPanelDomain().ast.value.length > 0) {
        const directoryId = this._getSearchPanelDomain().ast.value[0].value[2].value;

        const response = await this.orm.call(this.resModel, "get_directory_for_panel", [directoryId]);

        if (response) {
            // Trigger authentication wizard if the directory requires security
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: _t('Two Factor Authentication'),
                target: 'new',
                res_model: 'dms.directory.authenticator',
                views: [[false, 'form']],
            });
        }
    }

    const filterDomain = this._getFilterDomain();
    const searchDomain = this.searchDomain;
    // Fetch categories asynchronously
    await Promise.all(
        categories.map(async (category) => {
            console.log(this._getCategoryDomain(category.id),'Search Domain')
            const result = await this.orm.call(
                this.resModel,
                "search_panel_select_range",
                [category.fieldName],
                {
                    category_domain: this._getCategoryDomain(category.id),
                    context: this.globalContext,
                    enable_counters: category.enableCounters,
                    expand: category.expand,
                    filter_domain: filterDomain,
                    hierarchize: category.hierarchize,
                    limit: category.limit,
                    search_domain: searchDomain,
                }
            );
            this._createCategoryTree(category.id, result);
        })
    );
}

SearchModel.prototype._fetchCategories = _fetchCategories;
