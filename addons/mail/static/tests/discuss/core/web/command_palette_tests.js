/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { commandService } from "@web/core/commands/command_service";
import { registry } from "@web/core/registry";
import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

const serviceRegistry = registry.category("services");
const commandSetupRegistry = registry.category("command_setup");

QUnit.module("command palette", {
    async beforeEach() {
        serviceRegistry.add("command", commandService);
        registry
            .category("command_categories")
            .add("default", { label: "default" })
            .add("discuss_mentioned", { namespace: "@", name: "Mentions" }, { sequence: 10 })
            .add("discuss_recent", { namespace: "#", name: "Recent" }, { sequence: 10 });
    },
});

QUnit.test("open the chatWindow of a user from the command palette", async () => {
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    advanceTime(commandSetupRegistry.get("@").debounceDelay);
    await contains(".o_command", { count: 2 });
    await click(".o_command.focused", { text: "Mitchell Admin" });
    await contains(".o-mail-ChatWindow", { text: "Mitchell Admin" });
});

QUnit.test("open the chatWindow of a channel from the command palette", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        name: "general",
        channel_member_ids: [
            Command.create({
                partner_id: pyEnv.currentPartnerId,
                last_interest_dt: "2021-01-02 10:00:00", // same last interest to sort by id
            }),
        ],
    });
    pyEnv["discuss.channel"].create({
        name: "project",
        channel_member_ids: [
            Command.create({
                partner_id: pyEnv.currentPartnerId,
                last_interest_dt: "2021-01-02 10:00:00", // same last interest to sort by id
            }),
        ],
    });
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "#");
    advanceTime(commandSetupRegistry.get("#").debounceDelay);
    await contains(".o_command", { count: 2 });
    await contains(".o_command", { text: "project", before: [".o_command", { text: "general" }] });
    await contains(".o_command.focused");
    await click(".o_command.focused", { text: "project" });
    await contains(".o-mail-ChatWindow", { text: "project" });
});

QUnit.test("Channel mentions in the command palette of Discuss app with @", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    const messageId = pyEnv["mail.message"].create({
        author_id: partnerId,
        model: "discuss.channel",
        res_id: channelId,
        body: "@Mitchell Admin",
        needaction: true,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@", { replace: true });
    advanceTime(commandSetupRegistry.get("@").debounceDelay);
    await contains(".o_command_palette .o_command_category", {
        contains: [
            ["span.fw-bold", { text: "Mentions" }],
            [".o_command.focused .o_command_name", { text: "Mitchell Admin and Mario" }],
        ],
    });
    await contains(".o_command_palette .o_command_category", {
        contains: [[".o_command_name", { text: "Mitchell Admin" }]],
    });
    await click(".o_command.focused");
    await contains(".o-mail-ChatWindow", { text: "Mitchell Admin and Mario" });
});

QUnit.test("Max 3 most recent channels in command palette of Discuss app with #", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "channel_1" });
    pyEnv["discuss.channel"].create({ name: "channel_2" });
    pyEnv["discuss.channel"].create({ name: "channel_3" });
    pyEnv["discuss.channel"].create({ name: "channel_4" });
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "#", { replace: true });
    advanceTime(commandSetupRegistry.get("#").debounceDelay);
    await contains(".o_command_palette .o_command_category", {
        contains: [
            ["span.fw-bold", { text: "Recent" }],
            [".o_command", { count: 3 }],
        ],
    });
});

QUnit.test("only partners with dedicated users will be displayed in command palette", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "test user" });
    pyEnv["discuss.channel"].create({
        name: "TestChanel",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { advanceTime } = await start({ hasTimeControl: true });
    triggerHotkey("control+k");
    await insertText(".o_command_palette_search input", "@");
    advanceTime(commandSetupRegistry.get("@").debounceDelay);
    await contains(".o_command_name", { text: "Mitchell Admin" });
    await contains(".o_command_name", { text: "OdooBot" });
    await contains(".o_command_name", { text: "test user", count: 0 });
});
