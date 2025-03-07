/** @odoo-module */

import { selectCell, setCellContent } from "@spreadsheet/../tests/utils/commands";
import { registries, constants } from "@odoo/o-spreadsheet";
import { getAccountingData } from "../accounting_test_data";
import {
    createModelWithDataSource,
    waitForDataSourcesLoaded,
} from "@spreadsheet/../tests/utils/model";
import { registry } from "@web/core/registry";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";

const { cellMenuRegistry } = registries;
const { DEFAULT_LOCALE } = constants;

let serverData;

function beforeEach() {
    serverData = getAccountingData();
}

QUnit.module("spreadsheet_account > Accounting Drill down", { beforeEach }, () => {
    QUnit.test("Create drill down domain", async (assert) => {
        const drillDownAction = {
            type: "ir.actions.act_window",
            res_model: "account.move.line",
            view_mode: "list",
            views: [[false, "list"]],
            target: "current",
            domain: [["account_id", "in", [1, 2]]],
            name: "my awesome action",
        };
        const fakeActionService = {
            name: "action",
            start() {
                return {
                    async doAction(action, options) {
                        assert.step("drill down action");
                        assert.deepEqual(action, drillDownAction);
                        assert.equal(options, undefined);
                        return true;
                    },
                };
            },
        };
        registry.category("services").add("action", fakeActionService, { force: true });

        const model = await createModelWithDataSource({
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_move_line_action") {
                    assert.deepEqual(args.args, [
                        {
                            codes: ["100"],
                            company_id: null,
                            include_unposted: false,
                            date_range: {
                                range_type: "year",
                                year: 2020,
                            },
                        },
                    ]);
                    return drillDownAction;
                }
            },
        });
        const env = model.config.custom.env;
        env.model = model;
        setCellContent(model, "A1", `=ODOO.BALANCE("100", 2020)`);
        setCellContent(model, "A2", `=ODOO.BALANCE("100", 0)`);
        setCellContent(model, "A3", `=ODOO.BALANCE("100", 2020, , , FALSE)`);
        setCellContent(model, "A4", `=ODOO.BALANCE("100", 2020, , , )`);
        // Does not affect non formula cells
        setCellContent(model, "A5", `5`);
        await waitForDataSourcesLoaded(model);
        selectCell(model, "A1");
        const root = cellMenuRegistry
            .getMenuItems()
            .find((item) => item.id === "move_lines_see_records");
        assert.equal(root.isVisible(env), true);
        await root.execute(env);
        assert.verifySteps(["drill down action"]);
        selectCell(model, "A2");
        assert.equal(root.isVisible(env), false);
        selectCell(model, "A3");
        assert.equal(root.isVisible(env), true);
        await root.execute(env);
        assert.verifySteps(["drill down action"]);
        selectCell(model, "A4");
        assert.equal(root.isVisible(env), true);
        await root.execute(env);
        assert.verifySteps(["drill down action"]);
        selectCell(model, "A5");
        assert.equal(root.isVisible(env), false);
    });

    QUnit.test("Create drill down domain when month date is a reference", async (assert) => {
        const actionService = {
            start() {
                return {
                    doAction(args) {},
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });
        const model = await createModelWithDataSource({
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_move_line_action") {
                    assert.step("spreadsheet_move_line_action");
                    assert.deepEqual(args.args, [
                        {
                            codes: ["100"],
                            company_id: null,
                            include_unposted: false,
                            date_range: {
                                month: 2,
                                range_type: "month",
                                year: 2024,
                            },
                        },
                    ]);
                    return {};
                }
            },
        });
        const env = model.config.custom.env;
        env.model = model;
        setCellContent(model, "A1", "02/2024");
        setCellContent(model, "A2", '=ODOO.BALANCE("100", A1)');
        await waitForDataSourcesLoaded(model);
        selectCell(model, "A2");
        await doMenuAction(cellMenuRegistry, ["move_lines_see_records"], env);
        assert.verifySteps(["spreadsheet_move_line_action"]);
    });

    QUnit.test("Create drill down domain when date uses a non-standard locale", async (assert) => {
        const actionService = {
            start() {
                return {
                    doAction(args) {},
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });
        const model = await createModelWithDataSource({
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_move_line_action") {
                    assert.step("spreadsheet_move_line_action");
                    assert.deepEqual(args.args, [
                        {
                            codes: ["100"],
                            company_id: null,
                            include_unposted: false,
                            date_range: {
                                range_type: "day",
                                year: 2002,
                                month: 2,
                                day: 1,
                            },
                        },
                    ]);
                    return {};
                }
            },
        });
        const env = model.config.custom.env;
        env.model = model;
        const myLocale = { ...DEFAULT_LOCALE, dateFormat: "d/mmm/yyyy" };
        model.dispatch("UPDATE_LOCALE", { locale: myLocale });
        setCellContent(model, "A1", '=ODOO.BALANCE("100", DATE(2002, 2, 1))');
        await waitForDataSourcesLoaded(model);
        await doMenuAction(cellMenuRegistry, ["move_lines_see_records"], env);
        assert.verifySteps(["spreadsheet_move_line_action"]);
    });
});
