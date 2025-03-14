/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";
import { makeTestEnv } from "../../helpers/mock_env";
import {
    click,
    getFixture,
    patchWithCleanup,
    mount,
    nextTick,
    makeDeferred,
    editInput,
    getNodesTextContent,
} from "../../helpers/utils";
import {
    pagerNext,
    switchView,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/search/helpers";
import { session } from "@web/session";
import {
    createWebClient,
    doAction,
    getActionManagerServerData,
    loadState,
    setupWebClientRegistries,
} from "./../helpers";
import { errorService } from "@web/core/errors/error_service";

import { Component, onMounted, xml } from "@odoo/owl";

function getBreadCrumbTexts(target) {
    return getNodesTextContent(target.querySelectorAll(".breadcrumb-item, .o_breadcrumb .active"));
}

let serverData;
let target;

const actionRegistry = registry.category("actions");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Load State");

    QUnit.test("action loading", async (assert) => {
        assert.expect(2);
        const webClient = await createWebClient({ serverData });
        await loadState(webClient, { action: 1001 });
        assert.containsOnce(target, ".test_client_action");
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App1");
    });

    QUnit.test("menu loading", async (assert) => {
        assert.expect(2);
        const webClient = await createWebClient({ serverData });
        await loadState(webClient, { menu_id: 2 });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
    });

    QUnit.test("action and menu loading", async (assert) => {
        assert.expect(3);
        const webClient = await createWebClient({ serverData });
        await loadState(webClient, {
            action: 1001,
            menu_id: 2,
        });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 1"
        );
        assert.strictEqual(target.querySelector(".o_menu_brand").textContent, "App2");
        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: 1001,
            menu_id: 2,
        });
    });

    QUnit.test("initial loading with action id", async (assert) => {
        assert.expect(4);
        const hash = "#action=1001";
        Object.assign(browser.location, { hash });
        setupWebClientRegistries();

        const mockRPC = (route) => assert.step(route);
        const env = await makeTestEnv({ serverData, mockRPC });

        assert.verifySteps(["/web/action/load", "/web/webclient/load_menus"]);

        await mount(WebClient, getFixture(), { env });

        assert.verifySteps([]);
    });

    QUnit.test("initial loading with action tag", async (assert) => {
        assert.expect(3);
        const hash = "#action=__test__client__action__";
        Object.assign(browser.location, { hash });
        setupWebClientRegistries();

        const mockRPC = (route) => assert.step(route);
        const env = await makeTestEnv({ serverData, mockRPC });

        assert.verifySteps(["/web/webclient/load_menus"]);

        await mount(WebClient, getFixture(), { env });

        assert.verifySteps([]);
    });

    QUnit.test("fallback on home action if no action found", async (assert) => {
        assert.expect(2);
        patchWithCleanup(session, { home_action_id: 1001 });

        await createWebClient({ serverData });
        await nextTick(); // wait for the navbar to be updated
        await nextTick(); // wait for the action to be displayed

        assert.containsOnce(target, ".test_client_action");
        assert.strictEqual(target.querySelector(".o_menu_brand").innerText, "App1");
    });

    QUnit.test("correctly sends additional context", async (assert) => {
        assert.expect(1);
        const hash = "#action=1001&active_id=4&active_ids=4,8";
        Object.assign(browser.location, { hash });
        function mockRPC(route, params) {
            if (route === "/web/action/load") {
                assert.deepEqual(params, {
                    action_id: 1001,
                    additional_context: {
                        active_id: 4,
                        active_ids: [4, 8],
                    },
                });
            }
        }
        await createWebClient({ serverData, mockRPC });
    });

    QUnit.test("supports action as xmlId", async (assert) => {
        assert.expect(2);
        const webClient = await createWebClient({ serverData });
        await loadState(webClient, {
            action: "wowl.client_action",
        });
        assert.strictEqual(
            target.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_xmlId"
        );
        assert.containsNone(target, ".o_menu_brand");
    });

    QUnit.test("supports opening action in dialog", async (assert) => {
        assert.expect(3);
        serverData.actions["wowl.client_action"].target = "new";
        const webClient = await createWebClient({ serverData });
        await loadState(webClient, {
            action: "wowl.client_action",
        });
        assert.containsOnce(target, ".test_client_action");
        assert.containsOnce(target, ".modal .test_client_action");
        assert.containsNone(target, ".o_menu_brand");
    });

    QUnit.test("should not crash on invalid state", async function (assert) {
        assert.expect(3);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await loadState(webClient, {
            res_model: "partner",
        });
        assert.strictEqual($(target).text(), "", "should display nothing");
        assert.verifySteps(["/web/webclient/load_menus"]);
    });

    QUnit.test("properly load client actions", async function (assert) {
        assert.expect(3);
        class ClientAction extends Component {}
        ClientAction.template = xml`<div class="o_client_action_test">Hello World</div>`;
        actionRegistry.add("HelloWorldTest", ClientAction);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        webClient.env.bus.trigger("test:hashchange", {
            action: "HelloWorldTest",
        });
        await new Promise((r) => setTimeout(r)); // real "hashchange" event is triggered after a setTimeout [1]
        // [1] https://github.com/odoo/odoo/blob/1882d8f89f760bd1ff8a2bf0ae798939402647a3/addons/web/static/tests/setup.js#L52
        await nextTick();
        await nextTick();
        assert.strictEqual(
            $(target).find(".o_client_action_test").text(),
            "Hello World",
            "should have correctly rendered the client action"
        );
        assert.verifySteps(["/web/webclient/load_menus"]);
    });

    QUnit.test("properly load act window actions", async function (assert) {
        assert.expect(7);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        webClient.env.bus.trigger("test:hashchange", {
            action: 1,
        });
        await new Promise((r) => setTimeout(r)); // real "hashchange" event is triggered after a setTimeout [1]
        await nextTick();
        await nextTick();
        assert.containsOnce(target, ".o_control_panel");
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    QUnit.test("properly load records", async function (assert) {
        assert.expect(6);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        webClient.env.bus.trigger("test:hashchange", {
            id: 2,
            model: "partner",
        });
        await new Promise((r) => setTimeout(r)); // real "hashchange" event is triggered after a setTimeout [1]
        await nextTick();
        await nextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Second record"]);
        assert.verifySteps(["/web/webclient/load_menus", "get_views", "web_read"]);
    });

    QUnit.test("properly load records with existing first APP", async function (assert) {
        assert.expect(7);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        // simulate a real scenario with a first app (e.g. Discuss), to ensure that we don't
        // fallback on that first app when only a model and res_id are given in the url
        serverData.menus = {
            root: { id: "root", children: [1, 2], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "menu_1" },
            2: { id: 2, children: [], name: "App2", appID: 2, actionID: 1002, xmlid: "menu_2" },
        };
        const hash = "#id=2&model=partner";
        Object.assign(browser.location, { hash });
        await createWebClient({ serverData, mockRPC });

        await nextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Second record"]);
        assert.containsNone(target, ".o_menu_brand");
        assert.verifySteps(["/web/webclient/load_menus", "get_views", "web_read"]);
    });

    QUnit.test("properly load default record", async function (assert) {
        assert.expect(6);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        webClient.env.bus.trigger("test:hashchange", {
            action: 3,
            id: "",
            model: "partner",
            view_type: "form",
        });
        await new Promise((r) => setTimeout(r)); // real "hashchange" event is triggered after a setTimeout [1]
        await nextTick();
        await nextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "onchange",
        ]);
    });

    QUnit.test("load requested view for act window actions", async function (assert) {
        assert.expect(7);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        webClient.env.bus.trigger("test:hashchange", {
            action: 3,
            view_type: "kanban",
        });
        await new Promise((r) => setTimeout(r)); // real "hashchange" event is triggered after a setTimeout [1]
        await nextTick();
        await nextTick();
        assert.containsNone(target, ".o_list_view");
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    QUnit.test(
        "lazy load multi record view if mono record one is requested",
        async function (assert) {
            assert.expect(11);
            const mockRPC = async function (route, { method, kwargs }) {
                if (method === "unity_read") {
                    assert.step(`unity_read ${kwargs.method}`);
                } else {
                    assert.step(method || route);
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            webClient.env.bus.trigger("test:hashchange", {
                action: 3,
                id: 2,
                view_type: "form",
            });
            await nextTick();
            await nextTick();
            assert.containsNone(target, ".o_list_view");
            assert.containsOnce(target, ".o_form_view");
            assert.deepEqual(getBreadCrumbTexts(target), ["Partners", "Second record"]);
            // go back to List
            await click(target.querySelector(".o_control_panel .breadcrumb a"));
            assert.containsOnce(target, ".o_list_view");
            assert.containsNone(target, ".o_form_view");
            assert.verifySteps([
                "/web/webclient/load_menus",
                "/web/action/load",
                "get_views",
                "web_read",
                "web_search_read",
            ]);
        }
    );

    QUnit.test("lazy load multi record view with previous action", async function (assert) {
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 4);
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 4"]);
        await doAction(webClient, 3, {
            props: { resId: 2 },
            viewType: "form",
        });
        assert.deepEqual(getBreadCrumbTexts(target), [
            "Partners Action 4",
            "Partners",
            "Second record",
        ]);
        // go back to List
        await click(target.querySelector(".o_control_panel .breadcrumb .o_back_button a"));
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 4", "Partners"]);
    });

    QUnit.test(
        "lazy loaded multi record view with failing mono record one",
        async function (assert) {
            assert.expect(3);
            const mockRPC = async function (route, { method, kwargs }) {
                if (method === "web_read") {
                    return Promise.reject();
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await loadState(webClient, {
                action: 3,
                id: 2,
                view_type: "form",
            });
            assert.containsNone(target, ".o_form_view");
            assert.containsNone(target, ".o_list_view");
            await doAction(webClient, 1);
            assert.containsOnce(target, ".o_kanban_view");
        }
    );

    QUnit.test("change the viewType of the current action", async function (assert) {
        assert.expect(13);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        // switch to kanban view
        webClient.env.bus.trigger("test:hashchange", {
            action: 3,
            view_type: "kanban",
        });
        await new Promise((r) => setTimeout(r)); // real "hashchange" event is triggered after a setTimeout [1]
        await nextTick();
        await nextTick();
        assert.containsNone(target, ".o_list_view");
        assert.containsOnce(target, ".o_kanban_view");
        // switch to form view, open record 4
        webClient.env.bus.trigger("test:hashchange", {
            action: 3,
            id: 4,
            view_type: "form",
        });
        await new Promise((r) => setTimeout(r)); // real "hashchange" event is triggered after a setTimeout [1]
        await nextTick();
        await nextTick();
        assert.containsNone(target, ".o_kanban_view");
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners", "Fourth record"]);
        // verify steps to ensure that the whole action hasn't been re-executed
        // (if it would have been, /web/action/load and get_views would appear
        // several times)
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "web_search_read",
            "web_read",
        ]);
    });

    QUnit.test("change the id of the current action", async function (assert) {
        assert.expect(11);
        const mockRPC = async function (route, { method }) {
            assert.step(method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        // execute action 3 and open the first record in a form view
        await doAction(webClient, 3);
        await click(target.querySelector(".o_list_view .o_data_cell"));
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners", "First record"]);
        // switch to record 4
        webClient.env.bus.trigger("test:hashchange", {
            action: 3,
            id: 4,
            view_type: "form",
        });
        await new Promise((r) => setTimeout(r)); // real "hashchange" event is triggered after a setTimeout [1]
        await nextTick();
        await nextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners", "Fourth record"]);
        // verify steps to ensure that the whole action hasn't been re-executed
        // (if it would have been, /web/action/load and get_views would appear
        // twice)
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "web_read",
            "web_read",
        ]);
    });

    QUnit.test("should push the correct state at the right time", async function (assert) {
        // formerly "should not push a loaded state"
        assert.expect(7);
        const pushState = browser.history.pushState;
        patchWithCleanup(browser, {
            history: Object.assign({}, browser.history, {
                pushState() {
                    pushState(...arguments);
                    assert.step("push_state");
                },
            }),
        });
        const webClient = await createWebClient({ serverData });
        let currentHash = webClient.env.services.router.current.hash;
        assert.deepEqual(currentHash, {});
        await loadState(webClient, { action: 3 });
        currentHash = webClient.env.services.router.current.hash;
        assert.deepEqual(currentHash, {
            action: 3,
            model: "partner",
            view_type: "list",
        });
        assert.verifySteps(["push_state"], "should have pushed the final state");
        await click(target.querySelector("tr .o_data_cell"));
        await nextTick();
        currentHash = webClient.env.services.router.current.hash;
        assert.deepEqual(currentHash, {
            action: 3,
            id: 1,
            model: "partner",
            view_type: "form",
        });
        assert.verifySteps(["push_state"], "should push the state of it changes afterwards");
    });

    QUnit.test("load a window action without id (in a multi-record view)", async function (assert) {
        assert.expect(14);
        patchWithCleanup(browser.sessionStorage, {
            getItem(k) {
                assert.step(`getItem session ${k}`);
                return super.getItem(k);
            },
            setItem(k, v) {
                assert.step(`setItem session ${k}`);
                return super.setItem(k, v);
            },
        });
        const mockRPC = async (route, { method, kwargs }) => {
            assert.step(method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 4);
        assert.containsOnce(target, ".o_kanban_view", "should display a kanban view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 4"]);
        await loadState(webClient, {
            model: "partner",
            view_type: "list",
        });
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 4"]);
        assert.containsNone(target, ".o_kanban_view", "should no longer display a kanban view");
        assert.containsOnce(target, ".o_list_view", "should display a list view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "setItem session current_action",
            "getItem session current_action",
            "web_search_read",
            "setItem session current_action",
        ]);
    });

    QUnit.test("load state supports being given menu_id alone", async function (assert) {
        assert.expect(7);
        serverData.menus[666] = {
            id: 666,
            children: [],
            name: "App1",
            appID: 1,
            actionID: 1,
        };
        const mockRPC = async function (route) {
            assert.step(route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await loadState(webClient, { menu_id: 666 });
        assert.containsOnce(target, ".o_kanban_view", "should display a kanban view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 1"]);
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/web_search_read",
        ]);
    });

    QUnit.test("load state supports #home", async function (assert) {
        assert.expect(6);
        serverData.menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1 },
        };
        const webClient = await createWebClient({ serverData });
        await nextTick();
        assert.containsOnce(target, ".o_kanban_view"); // action 1 (default app)
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 1"]);
        await loadState(webClient, { action: 3 });
        assert.containsOnce(target, ".o_list_view"); // action 3
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners"]);
        await loadState(webClient, { home: 1 });
        assert.containsOnce(target, ".o_kanban_view"); // action 1 (default app)
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 1"]);
    });

    QUnit.test("load state supports #home as initial state", async function (assert) {
        assert.expect(7);
        serverData.menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1 },
        };
        const hash = "#home=1";
        Object.assign(browser.location, { hash });
        const mockRPC = async function (route) {
            assert.step(route);
        };
        await createWebClient({ serverData, mockRPC });
        await nextTick();
        assert.containsOnce(target, ".o_kanban_view", "should display a kanban view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partners Action 1"]);
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/web_search_read",
        ]);
    });

    QUnit.test("load state: in a form view, remove the id from the state", async function (assert) {
        assert.expect(11);
        serverData.actions[999] = {
            id: 999,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [666, "form"],
            ],
        };
        const mockRPC = async (route) => {
            assert.step(route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 999, { viewType: "form", props: { resId: 2 } });
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partner", "Second record"]);
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/web_read",
        ]);
        await loadState(webClient, {
            action: 999,
            view_type: "form",
            id: "",
        });
        assert.verifySteps(["/web/dataset/call_kw/partner/onchange"]);
        assert.containsOnce(target, ".o_form_view .o_form_editable");
        assert.deepEqual(getBreadCrumbTexts(target), ["Partner", "New"]);
    });

    QUnit.test("state with integer active_ids should not crash", async function (assert) {
        assert.expect(2);

        const mockRPC = async (route, args) => {
            if (route === "/web/action/run") {
                assert.strictEqual(args.action_id, 2);
                assert.deepEqual(args.context.active_ids, [3]);
                return new Promise(() => {});
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await loadState(webClient, {
            action: 2,
            active_ids: 3,
        });
    });

    QUnit.test(
        "url form view type switch from list or kanban doesn't timeout",
        async function (assert) {
            assert.expect(3);
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 3);
            assert.containsOnce(target, ".o_list_view", "should now display the list view");

            await switchView(target, "kanban");
            assert.containsOnce(target, ".o_kanban_view", "should now display the kanban view");

            const hash = webClient.env.services.router.current.hash;
            hash.view_type = "form";
            await loadState(webClient.env, hash);
            assert.containsOnce(
                target,
                ".o_form_view .o_form_editable",
                "should now display the form view in edit mode"
            );
        }
    );

    QUnit.test(
        "charge a form view via url, then switch to view list, the search view is correctly initialized",
        async function (assert) {
            assert.expect(2);

            serverData.views = {
                ...serverData.views,
                "partner,false,search": `
                    <search>
                        <filter name="filter" string="Filter" domain="[('foo', '=', 'yop')]"/>
                    </search>
                `,
            };

            const webClient = await createWebClient({ serverData });

            await loadState(webClient.env, {
                action: 3,
                model: "partner",
                view_type: "form",
            });

            await click(target.querySelector(".o_control_panel .breadcrumb-item"));

            assert.containsN(target, ".o_list_view .o_data_row", 5);

            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "Filter");

            assert.containsN(target, ".o_list_view .o_data_row", 1);
        }
    );

    QUnit.test("should not crash while commiting changes", async (assert) => {
        serverData.views["partner,false,form"] = `<form><field name="display_name" /></form>`;
        const webClient = await createWebClient({ serverData });
        await doAction(
            webClient,
            {
                type: "ir.actions.act_window",
                id: 1337,
                res_id: 1,
                res_model: "partner",
                views: [[false, "form"]],
            },
            { props: { resIds: [1, 2] } }
        );
        assert.deepEqual(getBreadCrumbTexts(target), ["First record"]);
        await pagerNext(target);
        assert.deepEqual(getBreadCrumbTexts(target), ["Second record"]);
        await editInput(target, "[name=display_name] input", "new name");

        // without saving we now make a loadState which should commit changes
        await loadState(webClient, { action: 1337, id: 1, model: "partner", view_type: "form" });
        assert.deepEqual(getBreadCrumbTexts(target), ["First record"]);

        // loadState again just to check if changes were commited
        await loadState(webClient, { action: 1337, id: 2, model: "partner", view_type: "form" });
        assert.deepEqual(getBreadCrumbTexts(target), ["new name"]);
    });

    QUnit.test("initial action crashes", async (assert) => {
        assert.expect(8);
        assert.expectErrors();

        browser.location.hash = "#action=__test__client__action__&menu_id=1";
        const ClientAction = registry.category("actions").get("__test__client__action__");
        class Override extends ClientAction {
            setup() {
                super.setup();
                assert.step("clientAction setup");
                throw new Error("my error");
            }
        }
        registry.category("actions").add("__test__client__action__", Override, { force: true });

        registry.category("services").add("error", errorService);

        const webClient = await createWebClient({ serverData });
        assert.verifySteps(["clientAction setup"]);
        await nextTick();
        assert.expectErrors(["my error"]);
        assert.containsOnce(target, ".o_error_dialog");
        await click(target, ".modal-header .btn-close");
        assert.containsNone(target, ".o_error_dialog");
        await click(target, "nav .o_navbar_apps_menu .dropdown-toggle ");
        assert.containsN(target, ".dropdown-item.o_app", 3);
        assert.containsNone(target, ".o_menu_brand");
        assert.strictEqual(target.querySelector(".o_action_manager").innerHTML, "");
        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "__test__client__action__",
            menu_id: 1,
        });
    });

    QUnit.test("concurrent hashchange during action mounting -- 1", async (assert) => {
        const hashchangeDef = makeDeferred();
        class MyAction extends Component {
            setup() {
                onMounted(() => {
                    assert.step("myAction mounted");
                    browser.addEventListener("hashchange", () => {
                        hashchangeDef.resolve();
                    });
                    browser.location.hash = "#action=__test__client__action__&menu_id=1";
                });
            }
        }
        MyAction.template = xml`<div class="not-here" />`;
        registry.category("actions").add("myAction", MyAction);

        browser.location.hash = "#action=myAction";

        const webClient = await createWebClient({ serverData });
        assert.verifySteps([]);
        await nextTick();
        assert.verifySteps(["myAction mounted"]);
        assert.containsOnce(target, ".not-here");

        // hashchange event isn't trigerred synchronously, so we have to wait for it
        await hashchangeDef;
        await nextTick();
        assert.containsNone(target, ".not-here");
        assert.containsNone(target, ".test_client_action");
        await nextTick();
        assert.containsNone(target, ".not-here");
        assert.containsOnce(target, ".test_client_action");

        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "__test__client__action__",
            menu_id: 1,
        });
    });

    QUnit.test("concurrent hashchange during action mounting -- 2", async (assert) => {
        assert.expect(6);

        const baseURL = new URL(browser.location.href).toString();

        class MyAction extends Component {
            setup() {
                onMounted(() => {
                    assert.step("myAction mounted");
                    const newURL = baseURL + "#action=__test__client__action__&menu_id=1";
                    // immediate triggering
                    window.dispatchEvent(new HashChangeEvent("hashchange", { newURL }));
                });
            }
        }
        MyAction.template = xml`<div class="not-here" />`;
        registry.category("actions").add("myAction", MyAction);

        browser.location.hash = "#action=myAction";
        const webClient = await createWebClient({ serverData });
        assert.verifySteps([]);
        await nextTick();
        assert.verifySteps(["myAction mounted"]);

        await nextTick();
        await nextTick();
        assert.containsNone(target, ".not-here");
        assert.containsOnce(target, ".test_client_action");

        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "__test__client__action__",
            menu_id: 1,
        });
    });

    QUnit.test(
        "'no content helper' is markuped when action is retrieved from session storage",
        async function (assert) {
            // for the no content helper to show, we empty the data
            serverData.models.partner.records = [];
            serverData.actions[4].help = "<p>Some nice help</p>";

            patchWithCleanup(browser.sessionStorage, {
                getItem(k) {
                    assert.step(`getItem session ${k}`);
                    return super.getItem(k);
                },
            });

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, 4);
            assert.containsOnce(target, ".o_kanban_view", "should display a kanban view");

            assert.strictEqual(
                "Some nice help",
                target.querySelector(".o_nocontent_help").innerText
            );

            await loadState(webClient, {
                model: "partner",
                view_type: "list",
            });

            assert.containsNone(target, ".o_kanban_view", "should no longer display a kanban view");
            assert.containsOnce(target, ".o_list_view", "should display a list view");

            assert.strictEqual(
                "Some nice help",
                target.querySelector(".o_nocontent_help").innerText
            );

            assert.verifySteps(["getItem session current_action"]);
        }
    );
});
