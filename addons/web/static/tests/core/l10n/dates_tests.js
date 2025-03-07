/** @odoo-module **/

import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
    formatDateTime,
    parseDate,
    parseDateTime,
    serializeDate,
    serializeDateTime,
    strftimeToLuxonFormat,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { defaultLocalization } from "../../helpers/mock_services";
import { patchDate, patchTimeZone, patchWithCleanup } from "../../helpers/utils";

const { DateTime, Settings } = luxon;

const formats = {
    date: "%d.%m/%Y",
    time: "%H:%M:%S",
};
const dateFormat = strftimeToLuxonFormat(formats.date);
const timeFormat = strftimeToLuxonFormat(formats.time);

function runTestSet(assert, testSet, fn) {
    for (const [input, expected] of testSet.entries()) {
        let res;
        try {
            res = fn(input);
        } catch {
            // continue
        }
        assert.deepEqual(res, expected, `"${input}" is parsed as expected.`);
    }
}

QUnit.module("utils", {}, () => {
    QUnit.module("dates");

    QUnit.test("formatDate/formatDateTime specs", async (assert) => {
        patchWithCleanup(localization, {
            dateFormat: "MM/dd/yyyy",
            dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
        });
        patchTimeZone(60);
        patchDate(2009, 4, 4, 12, 34, 56);

        const utc = DateTime.utc(); // 2009-05-04T11:34:56.000Z
        const local = DateTime.local(); // 2009-05-04T12:34:56.000+01:00
        const minus13FromLocalTZ = local.setZone("UTC-12"); // 2009-05-03T23:34:56.000-12:00

        // For dates, regardless of the input timezone, outputs only the date
        assert.strictEqual(formatDate(utc), "05/04/2009");
        assert.strictEqual(formatDate(local), "05/04/2009");
        assert.strictEqual(formatDate(minus13FromLocalTZ), "05/03/2009");

        // For datetimes, input timezone is taken into account, outputs in local timezone
        assert.strictEqual(formatDateTime(utc), "05/04/2009 12:34:56");
        assert.strictEqual(formatDateTime(local), "05/04/2009 12:34:56");
        assert.strictEqual(formatDateTime(minus13FromLocalTZ), "05/04/2009 12:34:56");
    });

    QUnit.test("formatDate/formatDateTime specs, at midnight", async (assert) => {
        patchWithCleanup(localization, {
            dateFormat: "MM/dd/yyyy",
            dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
        });
        patchTimeZone(60);
        patchDate(2009, 4, 4, 0, 0, 0);

        const utc = DateTime.utc(); // 2009-05-03T23:00:00.000Z
        const local = DateTime.local(); // 2009-05-04T00:00:00.000+01:00
        const minus13FromLocalTZ = local.setZone("UTC-12"); // 2009-05-03T11:00:00.000-12:00

        // For dates, regardless of the input timezone, outputs only the date
        assert.strictEqual(formatDate(utc), "05/03/2009");
        assert.strictEqual(formatDate(local), "05/04/2009");
        assert.strictEqual(formatDate(minus13FromLocalTZ), "05/03/2009");

        // For datetimes, input timezone is taken into account, outputs in local timezone
        assert.strictEqual(formatDateTime(utc), "05/04/2009 00:00:00");
        assert.strictEqual(formatDateTime(local), "05/04/2009 00:00:00");
        assert.strictEqual(formatDateTime(minus13FromLocalTZ), "05/04/2009 00:00:00");
    });

    QUnit.test("parseDate(Time) outputs DateTime objects in local TZ", async (assert) => {
        patchWithCleanup(localization, defaultLocalization);

        patchTimeZone(60);
        assert.equal(parseDate("01/13/2019").toISO(), "2019-01-13T00:00:00.000+01:00");
        assert.equal(parseDateTime("01/13/2019 10:05:45").toISO(), "2019-01-13T10:05:45.000+01:00");

        patchTimeZone(330);
        assert.equal(parseDate("01/13/2019").toISO(), "2019-01-13T00:00:00.000+05:30");
        assert.equal(parseDateTime("01/13/2019 10:05:45").toISO(), "2019-01-13T10:05:45.000+05:30");

        patchTimeZone(-660);
        assert.equal(parseDate("01/13/2019").toISO(), "2019-01-13T00:00:00.000-11:00");
        assert.equal(parseDateTime("01/13/2019 10:05:45").toISO(), "2019-01-13T10:05:45.000-11:00");
    });

    QUnit.test("parseDate with different numbering system", async (assert) => {
        patchWithCleanup(localization, {
            dateFormat: "dd MMM, yyyy",
            dateTimeFormat: "dd MMM, yyyy hh:mm:ss",
            timeFormat: "hh:mm:ss",
        });

        patchWithCleanup(Settings, { defaultNumberingSystem: "arab", defaultLocale: "ar" });

        assert.equal(parseDate("٠١ فبراير, ٢٠٢٣").toISO(), "2023-02-01T00:00:00.000+01:00");
    });

    QUnit.test("parseDateTime", async (assert) => {
        patchWithCleanup(localization, { ...defaultLocalization });

        assert.throws(
            function () {
                parseDateTime("13/01/2019 12:00:00");
            },
            /is not a correct/,
            "Wrongly formated dates should be invalid"
        );
        assert.throws(
            function () {
                parseDateTime("01/01/0999 12:00:00");
            },
            /is not a correct/,
            "Dates before 1000 should be invalid"
        );
        assert.throws(
            function () {
                parseDateTime("01/01/10000 12:00:00");
            },
            /is not a correct/,
            "Dates after 9999 should be invalid"
        );
        assert.throws(function () {
            parseDateTime("invalid value");
        }, /is not a correct/);

        const expected = "2019-01-13T10:05:45.000+01:00";
        let dateStr = "01/13/2019 10:05:45";
        assert.equal(parseDateTime(dateStr).toISO(), expected, "Date with leading 0");
        dateStr = "1/13/2019 10:5:45";
        assert.equal(parseDateTime(dateStr).toISO(), expected, "Date without leading 0");
    });

    QUnit.test("parseDateTime (norwegian locale)", async (assert) => {
        const dateFormat = strftimeToLuxonFormat("%d. %b %Y");
        const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
        patchWithCleanup(localization, {
            dateFormat,
            timeFormat,
            dateTimeFormat: `${dateFormat} ${timeFormat}`,
        });

        // Before WOWL we were using MomentJS.
        // Now it has been replaced by luxon.js, we cannot declare customized locales.
        // In legacy web, parseDateTime tests were originally defining custom locales
        // for english and norwegian.
        // Here, we simply use the vanilla Intl support to switch locale.
        const originalLocale = Settings.defaultLocale;
        Settings.defaultLocale = "no"; // Norwegian

        const dateStr = "16. des 2019 10:05:45";
        const expected = "2019-12-16T10:05:45.000+01:00";
        assert.equal(parseDateTime(dateStr).toISO(), expected, "Day/month inverted + month i18n");

        Settings.defaultLocale = originalLocale;
    });

    QUnit.test("parseDate", async (assert) => {
        patchWithCleanup(localization, defaultLocalization);

        let str = "07/21/2022";
        assert.strictEqual(parseDate(str).toISO(), "2022-07-21T00:00:00.000+01:00");

        str = "07/22/2022";
        assert.strictEqual(parseDate(str).toISO(), "2022-07-22T00:00:00.000+01:00");
    });

    QUnit.test("parseDate without separator", async (assert) => {
        const dateFormat = strftimeToLuxonFormat("%d.%m/%Y");
        const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
        patchWithCleanup(localization, {
            dateFormat,
            timeFormat,
            dateTimeFormat: `${dateFormat} ${timeFormat}`,
        });

        const testDateFormat = "dd.MM/yyyy";

        assert.throws(
            function () {
                parseDate("1137");
            },
            /is not a correct/,
            "Wrongly formated dates should be invalid"
        );
        assert.throws(
            function () {
                parseDate("1197");
            },
            /is not a correct/,
            "Wrongly formated dates should be invalid"
        );
        assert.throws(
            function () {
                parseDate("0131");
            },
            /is not a correct/,
            "Wrongly formated dates should be invalid"
        );
        assert.throws(
            function () {
                parseDate("970131");
            },
            /is not a correct/,
            "Wrongly formated dates should be invalid"
        );
        assert.equal(parseDate("2001").toFormat(testDateFormat), "20.01/" + DateTime.utc().year);
        assert.equal(parseDate("3101").toFormat(testDateFormat), "31.01/" + DateTime.utc().year);
        assert.equal(parseDate("31.01").toFormat(testDateFormat), "31.01/" + DateTime.utc().year);
        assert.equal(parseDate("310197").toFormat(testDateFormat), "31.01/1997");
        assert.equal(parseDate("310117").toFormat(testDateFormat), "31.01/2017");
        assert.equal(parseDate("31011985").toFormat(testDateFormat), "31.01/1985");
    });

    QUnit.test("parseDateTime without separator", async (assert) => {
        const dateFormat = strftimeToLuxonFormat("%d.%m/%Y");
        const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
        patchWithCleanup(localization, {
            dateFormat,
            timeFormat,
            dateTimeFormat: `${dateFormat} ${timeFormat}`,
        });

        const dateTimeFormat = "dd.MM/yyyy HH:mm/ss";
        assert.equal(parseDateTime("3101198508").toFormat(dateTimeFormat), "31.01/1985 08:00/00");
        assert.equal(parseDateTime("310119850833").toFormat(dateTimeFormat), "31.01/1985 08:33/00");
        assert.equal(
            parseDateTime("31/01/1985 08").toFormat(dateTimeFormat),
            "31.01/1985 08:00/00"
        );
    });

    QUnit.test("parseDateTime with escaped characters (eg. Basque locale)", async (assert) => {
        const dateFormat = strftimeToLuxonFormat("%a, %Y.eko %bren %da");
        const timeFormat = strftimeToLuxonFormat("%H:%M:%S");
        patchWithCleanup(localization, {
            dateFormat,
            timeFormat,
            dateTimeFormat: `${dateFormat} ${timeFormat}`,
        });

        const dateTimeFormat = `${dateFormat} ${timeFormat}`;
        assert.equal(dateTimeFormat, "ccc, yyyy.'e''k''o' MMM'r''e''n' dd'a' HH:mm:ss");
        assert.equal(
            parseDateTime("1985-01-31 08:30:00").toFormat(dateTimeFormat),
            "Thu, 1985.eko Janren 31a 08:30:00"
        );
    });

    QUnit.test("parse smart date input", async (assert) => {
        patchDate(2020, 0, 1, 0, 0, 0); // 2020-01-01 00:00:00

        const format = "yyyy-MM-dd HH:mm";
        // with parseDate
        assert.strictEqual(parseDate("+0").toFormat(format), "2020-01-01 00:00");
        assert.strictEqual(parseDate("-0").toFormat(format), "2020-01-01 00:00");
        assert.strictEqual(parseDate("+1d").toFormat(format), "2020-01-02 00:00");
        assert.strictEqual(parseDate("+2w").toFormat(format), "2020-01-15 00:00");
        assert.strictEqual(parseDate("+3m").toFormat(format), "2020-04-01 00:00");
        assert.strictEqual(parseDate("+4y").toFormat(format), "2024-01-01 00:00");
        assert.strictEqual(parseDate("+5").toFormat(format), "2020-01-06 00:00");
        assert.strictEqual(parseDate("-5").toFormat(format), "2019-12-27 00:00");
        assert.strictEqual(parseDate("-4y").toFormat(format), "2016-01-01 00:00");
        assert.strictEqual(parseDate("-3m").toFormat(format), "2019-10-01 00:00");
        assert.strictEqual(parseDate("-2w").toFormat(format), "2019-12-18 00:00");
        assert.strictEqual(parseDate("-1d").toFormat(format), "2019-12-31 00:00");
        // with parseDateTime
        assert.strictEqual(parseDateTime("+0").toFormat(format), "2020-01-01 00:00");
        assert.strictEqual(parseDateTime("-0").toFormat(format), "2020-01-01 00:00");
        assert.strictEqual(parseDateTime("+1d").toFormat(format), "2020-01-02 00:00");
        assert.strictEqual(parseDateTime("+2w").toFormat(format), "2020-01-15 00:00");
        assert.strictEqual(parseDateTime("+3m").toFormat(format), "2020-04-01 00:00");
        assert.strictEqual(parseDateTime("+4y").toFormat(format), "2024-01-01 00:00");
        assert.strictEqual(parseDateTime("+5").toFormat(format), "2020-01-06 00:00");
        assert.strictEqual(parseDateTime("-5").toFormat(format), "2019-12-27 00:00");
        assert.strictEqual(parseDateTime("-4y").toFormat(format), "2016-01-01 00:00");
        assert.strictEqual(parseDateTime("-3m").toFormat(format), "2019-10-01 00:00");
        assert.strictEqual(parseDateTime("-2w").toFormat(format), "2019-12-18 00:00");
        assert.strictEqual(parseDateTime("-1d").toFormat(format), "2019-12-31 00:00");
    });

    QUnit.test("parseDateTime ISO8601 Format", async (assert) => {
        patchWithCleanup(localization, defaultLocalization);
        patchTimeZone(60);
        assert.equal(
            parseDateTime("2017-05-15T12:00:00.000+06:00").toISO(),
            "2017-05-15T07:00:00.000+01:00"
        );
        // without the 'T' separator is not really ISO8601 compliant, but we still support it
        assert.equal(
            parseDateTime("2017-05-15 12:00:00.000+06:00").toISO(),
            "2017-05-15T07:00:00.000+01:00"
        );
    });

    QUnit.test("parseDateTime SQL Format", async (assert) => {
        patchWithCleanup(localization, defaultLocalization);

        let dateStr = "2017-05-15 09:12:34";
        let expected = "2017-05-15T09:12:34.000+01:00";
        assert.equal(parseDateTime(dateStr).toISO(), expected, "Date with SQL format");

        dateStr = "2017-05-08 09:12:34";
        expected = "2017-05-08T09:12:34.000+01:00";
        assert.equal(
            parseDateTime(dateStr).toISO(),
            expected,
            "Date SQL format, check date is not confused with month"
        );
    });

    QUnit.test("serializeDate", async (assert) => {
        const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
        assert.strictEqual(date.toFormat("yyyy-MM-dd"), "2022-02-21");
        assert.strictEqual(serializeDate(date), "2022-02-21");
    });

    QUnit.test("serializeDate, with DateTime.now()", async (assert) => {
        patchDate(2022, 1, 21, 16, 11, 42);
        const date = DateTime.now();
        assert.strictEqual(date.toFormat("yyyy-MM-dd"), "2022-02-21");
        assert.strictEqual(serializeDate(date), "2022-02-21");
    });

    QUnit.test("serializeDate, with DateTime.now(), midnight", async (assert) => {
        patchDate(2022, 1, 21, 0, 0, 0);
        const date = DateTime.now();
        assert.strictEqual(date.toFormat("yyyy-MM-dd"), "2022-02-21");
        assert.strictEqual(serializeDate(date), "2022-02-21");
    });

    QUnit.test("serializeDate with different numbering system", async (assert) => {
        patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
        const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
        assert.strictEqual(date.toFormat("yyyy-MM-dd"), "٢٠٢٢-٠٢-٢١");
        assert.strictEqual(serializeDate(date), "2022-02-21");
    });

    QUnit.test("serializeDateTime", async (assert) => {
        const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
        assert.strictEqual(date.toFormat("yyyy-MM-dd HH:mm:ss"), "2022-02-21 16:11:42");
        assert.strictEqual(serializeDateTime(date), "2022-02-21 16:11:42");
    });

    QUnit.test("serializeDateTime, with DateTime.now()", async (assert) => {
        patchDate(2022, 1, 21, 16, 11, 42);
        const date = DateTime.now();
        assert.strictEqual(date.toFormat("yyyy-MM-dd HH:mm:ss"), "2022-02-21 16:11:42");
        assert.strictEqual(
            serializeDateTime(date),
            "2022-02-21 15:11:42",
            "serializeDateTime should output an UTC converted string"
        );
    });

    QUnit.test("serializeDateTime, with DateTime.now(), midnight", async (assert) => {
        patchDate(2022, 1, 21, 0, 0, 0);
        const date = DateTime.now();
        assert.strictEqual(date.toFormat("yyyy-MM-dd HH:mm:ss"), "2022-02-21 00:00:00");
        assert.strictEqual(
            serializeDateTime(date),
            "2022-02-20 23:00:00",
            "serializeDateTime should output an UTC converted string"
        );
    });

    QUnit.test("serializeDateTime with different numbering system", async (assert) => {
        patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
        const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
        assert.strictEqual(date.toFormat("yyyy-MM-dd HH:mm:ss"), "٢٠٢٢-٠٢-٢١ ١٦:١١:٤٢");
        assert.strictEqual(serializeDateTime(date), "2022-02-21 16:11:42");
    });

    QUnit.test("deserializeDate", async (assert) => {
        const date = DateTime.local(2022, 2, 21);
        assert.strictEqual(
            DateTime.fromFormat("2022-02-21", "yyyy-MM-dd").toMillis(),
            date.toMillis()
        );
        assert.strictEqual(deserializeDate("2022-02-21").toMillis(), date.toMillis());
    });

    QUnit.test("deserializeDate with different numbering system", async (assert) => {
        patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
        const date = DateTime.local(2022, 2, 21);
        assert.strictEqual(
            DateTime.fromFormat("٢٠٢٢-٠٢-٢١", "yyyy-MM-dd").toMillis(),
            date.toMillis()
        );
        assert.strictEqual(deserializeDate("2022-02-21").toMillis(), date.toMillis());
    });

    QUnit.test("deserializeDateTime", async (assert) => {
        const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
        assert.strictEqual(
            DateTime.fromFormat("2022-02-21 16:11:42", "yyyy-MM-dd HH:mm:ss", {
                zone: "utc",
            }).toMillis(),
            date.toMillis()
        );
        assert.strictEqual(deserializeDateTime("2022-02-21 16:11:42").toMillis(), date.toMillis());
    });

    QUnit.test("deserializeDateTime with different numbering system", async (assert) => {
        patchWithCleanup(Settings, { defaultNumberingSystem: "arab" });
        const date = DateTime.utc(2022, 2, 21, 16, 11, 42);
        assert.strictEqual(
            DateTime.fromFormat("٢٠٢٢-٠٢-٢١ ١٦:١١:٤٢", "yyyy-MM-dd HH:mm:ss", {
                zone: "utc",
            }).toMillis(),
            date.toMillis()
        );
        assert.strictEqual(deserializeDateTime("2022-02-21 16:11:42").toMillis(), date.toMillis());
    });

    QUnit.test("parseDate with short notations", async (assert) => {
        assert.strictEqual(
            parseDate("20-10-20", { format: "yyyy-MM-dd" }).toISO(),
            "2020-10-20T00:00:00.000+01:00"
        );
        assert.strictEqual(
            parseDate("20/10/20", { format: "yyyy/MM/dd" }).toISO(),
            "2020-10-20T00:00:00.000+01:00"
        );
        assert.strictEqual(
            parseDate("10-20-20", { format: "MM-dd-yyyy" }).toISO(),
            "2020-10-20T00:00:00.000+01:00"
        );
        assert.strictEqual(
            parseDate("10-20-20", { format: "MM-yyyy-dd" }).toISO(),
            "2020-10-20T00:00:00.000+01:00"
        );
        assert.strictEqual(
            parseDate("1-20-2", { format: "MM-yyyy-dd" }).toISO(),
            "2020-01-02T00:00:00.000+01:00"
        );
        assert.strictEqual(
            parseDate("20/1/2", { format: "yyyy/MM/dd" }).toISO(),
            "2020-01-02T00:00:00.000+01:00"
        );
    });

    QUnit.test("parseDateTime with short notations", async (assert) => {
        assert.strictEqual(
            parseDateTime("20-10-20 8:5:3", { format: "yyyy-MM-dd hh:mm:ss" }).toISO(),
            "2020-10-20T08:05:03.000+01:00"
        );
    });

    QUnit.test("parseDate with textual month notation", async function (assert) {
        Object.assign(localization, {
            dateFormat: "MMM/dd/yyyy",
        });
        assert.strictEqual(parseDate("Jan/05/1997").toISO(), "1997-01-05T00:00:00.000+01:00");
        assert.strictEqual(
            parseDate("Jan/05/1997", { format: undefined }).toISO(),
            "1997-01-05T00:00:00.000+01:00"
        );
        assert.strictEqual(
            parseDate("Jan/05/1997", { format: "MMM/dd/yyyy" }).toISO(),
            "1997-01-05T00:00:00.000+01:00"
        );
    });

    QUnit.test("parseDate (various entries)", async (assert) => {
        patchDate(2020, 6, 15, 12, 30, 0);
        patchTimeZone(0);
        patchWithCleanup(localization, {
            dateFormat,
            timeFormat,
            dateTimeFormat: `${dateFormat} ${timeFormat}`,
        });

        /**
         * Type of testSet key: string
         * Type of testSet value: string | undefined
         */
        const testSet = new Map([
            ["10101010101010", undefined],
            ["1191111", "1191-04-21T00:00:00.000Z"], // day 111 of year 1191
            ["11911111", "1191-11-11T00:00:00.000Z"],
            ["3101", "2020-01-31T00:00:00.000Z"],
            ["310160", "2060-01-31T00:00:00.000Z"],
            ["311260", "2060-12-31T00:00:00.000Z"],

            ["310161", "1961-01-31T00:00:00.000Z"],
            ["310165", "1965-01-31T00:00:00.000Z"],
            ["310168", "1968-01-31T00:00:00.000Z"],
            ["311268", "1968-12-31T00:00:00.000Z"],

            ["310169", "1969-01-31T00:00:00.000Z"],
            ["310170", "1970-01-31T00:00:00.000Z"],
            ["310197", "1997-01-31T00:00:00.000Z"],
            ["310117", "2017-01-31T00:00:00.000Z"],
            ["31011985", "1985-01-31T00:00:00.000Z"],
            ["3101198508", undefined],
            ["310119850833", undefined],

            ["1137", undefined],
            ["1197", undefined],
            ["0131", undefined],
            ["0922", undefined],
            ["2020", undefined],

            ["199901", "1999-01-01T00:00:00.000Z"],
            ["30100210", "3010-02-10T00:00:00.000Z"],
            ["3010210", "3010-07-29T00:00:00.000Z"],

            ["970131", undefined],
            ["31.01", "2020-01-31T00:00:00.000Z"],
            ["31/01/1985 08", undefined],

            ["01121934", "1934-12-01T00:00:00.000Z"],
            ["011234", "2034-12-01T00:00:00.000Z"],
            ["011260", "2060-12-01T00:00:00.000Z"],
            ["2", "2020-07-02T00:00:00.000Z"],
            ["02", "2020-07-02T00:00:00.000Z"],
            ["20", "2020-07-20T00:00:00.000Z"],
            ["202", "2020-02-20T00:00:00.000Z"],
            ["2002", "2020-02-20T00:00:00.000Z"],
            ["0202", "2020-02-02T00:00:00.000Z"],
            ["02/02", "2020-02-02T00:00:00.000Z"],
            ["02/13", undefined],
            ["02/1313", undefined],
            ["09990101", undefined],
            ["19990101", "1999-01-01T00:00:00.000Z"],
            ["19990130", "1999-01-30T00:00:00.000Z"],
            ["19991230", "1999-12-30T00:00:00.000Z"],
            ["19993012", undefined],
            ["2016-200", "2016-07-18T00:00:00.000Z"],
            ["2016200", "2016-07-18T00:00:00.000Z"], // day 200 of year 2016
            ["2020-", undefined],
            ["2020-W2", undefined],
            ["2020W23", "2020-06-01T00:00:00.000Z"],
            ["2020-W02", "2020-01-06T00:00:00.000Z"],
            ["2020-W32", "2020-08-03T00:00:00.000Z"],
            ["2020-W32-3", "2020-08-05T00:00:00.000Z"],
            ["2016-W21-3", "2016-05-25T00:00:00.000Z"],
            ["2016W213", "2016-05-25T00:00:00.000Z"],
            ["2209", "2020-09-22T00:00:00.000Z"],
            ["22:09", "2020-09-22T00:00:00.000Z"],
            ["2012", "2020-12-20T00:00:00.000Z"],

            ["2016-01-03 09:24:15.123", "2016-01-03T00:00:00.000Z"],
            ["2016-01-03T09:24:15.123", "2016-01-03T00:00:00.000Z"],
            ["2016-01-03T09:24:15.123+06:00", "2016-01-03T00:00:00.000Z"],
            ["2016-01-03T09:24:15.123+16:00", "2016-01-02T00:00:00.000Z"],
            ["2016-01-03T09:24:15.123Z", "2016-01-03T00:00:00.000Z"],
            ["2016-W21-3T09:24:15.123", "2016-05-25T00:00:00.000Z"],
            ["2016-W21-3 09:24:15.123", undefined],

            ["2016-03-27T02:00:00.000+02:00", "2016-03-27T00:00:00.000Z"],
            ["2016-03-27T03:00:00.000+02:00", "2016-03-27T00:00:00.000Z"],
            ["2016-03-27T02:00:00.000", "2016-03-27T00:00:00.000Z"],
            ["2016-03-27T03:00:00.000", "2016-03-27T00:00:00.000Z"],
            ["2016-03-27T02:00:00.000Z", "2016-03-27T00:00:00.000Z"],
            ["2016-03-27T03:00:00.000Z", "2016-03-27T00:00:00.000Z"],

            ["09:22", undefined],
            ["2013", undefined],
            ["011261", "1961-12-01T00:00:00.000Z"],

            ["932-10-10", undefined], // year < 1000 are not supported
            ["1932-10-10", "1932-10-10T00:00:00.000Z"],
            ["2016-01-03 09:24:15.123+06:00", "2016-01-03T00:00:00.000Z"],
            ["2016-01-03 09:24:15.123+16:00", "2016-01-02T00:00:00.000Z"],
            ["2016-01-03 09:24:15.123Z", "2016-01-03T00:00:00.000Z"],
        ]);

        runTestSet(assert, testSet, (input) => parseDate(input).toISO());
    });

    QUnit.test("parseDateTime (various entries)", async (assert) => {
        patchDate(2020, 6, 15, 12, 30, 0);
        patchTimeZone(0);
        patchWithCleanup(localization, {
            dateFormat,
            timeFormat,
            dateTimeFormat: `${dateFormat} ${timeFormat}`,
        });

        /**
         * Type of testSet key: string
         * Type of testSet value: string | undefined
         */
        const testSet = new Map([
            ["10101010101010", "1010-10-10T10:10:10.000Z"],
            ["1191111", "1191-04-21T00:00:00.000Z"], // day 111 of year 1191
            ["11911111", "1191-11-11T00:00:00.000Z"],
            ["3101", "2020-01-31T00:00:00.000Z"],
            ["310160", "2060-01-31T00:00:00.000Z"],
            ["311260", "2060-12-31T00:00:00.000Z"],
            ["310161", "1961-01-31T00:00:00.000Z"],
            ["310165", "1965-01-31T00:00:00.000Z"],
            ["310168", "1968-01-31T00:00:00.000Z"],
            ["311268", "1968-12-31T00:00:00.000Z"],
            ["310169", "1969-01-31T00:00:00.000Z"],
            ["310170", "1970-01-31T00:00:00.000Z"],
            ["310197", "1997-01-31T00:00:00.000Z"],
            ["310117", "2017-01-31T00:00:00.000Z"],
            ["31011985", "1985-01-31T00:00:00.000Z"],
            ["3101198508", "1985-01-31T08:00:00.000Z"],
            ["310119850833", "1985-01-31T08:33:00.000Z"],
            ["1137", undefined],
            ["1197", undefined],
            ["0131", undefined],
            ["0922", undefined],
            ["2020", undefined],
            ["199901", "1999-01-01T00:00:00.000Z"],
            ["30100210", "3010-02-10T00:00:00.000Z"],
            ["3010210", "3010-07-29T00:00:00.000Z"],
            ["970131", undefined],
            ["31.01", "2020-01-31T00:00:00.000Z"],
            ["31/01/1985 08", "1985-01-31T08:00:00.000Z"],

            ["01121934", "1934-12-01T00:00:00.000Z"],
            ["011234", "2034-12-01T00:00:00.000Z"],
            ["011260", "2060-12-01T00:00:00.000Z"],
            ["2", "2020-07-02T00:00:00.000Z"],
            ["02", "2020-07-02T00:00:00.000Z"],
            ["20", "2020-07-20T00:00:00.000Z"],
            ["202", "2020-02-20T00:00:00.000Z"],
            ["2002", "2020-02-20T00:00:00.000Z"],
            ["0202", "2020-02-02T00:00:00.000Z"],
            ["02/02", "2020-02-02T00:00:00.000Z"],
            ["02/13", undefined],
            ["02/1313", undefined],
            ["09990101", undefined],
            ["19990101", "1999-01-01T00:00:00.000Z"],
            ["19990130", "1999-01-30T00:00:00.000Z"],
            ["19991230", "1999-12-30T00:00:00.000Z"],
            ["19993012", undefined],
            ["2016-200", "2016-07-18T00:00:00.000Z"],
            ["2016200", "2016-07-18T00:00:00.000Z"], // day 200 of year 2016
            ["2020-", undefined],
            ["2020-W2", undefined],
            ["2020W23", "2020-06-01T00:00:00.000Z"],
            ["2020-W02", "2020-01-06T00:00:00.000Z"],
            ["2020-W32", "2020-08-03T00:00:00.000Z"],
            ["2020-W32-3", "2020-08-05T00:00:00.000Z"],
            ["2016-W21-3", "2016-05-25T00:00:00.000Z"],
            ["2016W213", "2016-05-25T00:00:00.000Z"],
            ["2209", "2020-09-22T00:00:00.000Z"],
            ["22:09", "2020-09-22T00:00:00.000Z"],
            ["2012", "2020-12-20T00:00:00.000Z"],

            ["2016-01-03 09:24:15.123", "2016-01-03T09:24:15.123Z"],
            ["2016-01-03T09:24:15.123", "2016-01-03T09:24:15.123Z"],
            ["2016-01-03T09:24:15.123+06:00", "2016-01-03T03:24:15.123Z"],
            ["2016-01-03T09:24:15.123+16:00", "2016-01-02T17:24:15.123Z"],
            ["2016-01-03T09:24:15.123Z", "2016-01-03T09:24:15.123Z"],
            ["2016-W21-3T09:24:15.123", "2016-05-25T09:24:15.123Z"],
            ["2016-W21-3 09:24:15.123", undefined],

            ["2016-03-27T02:00:00.000+02:00", "2016-03-27T00:00:00.000Z"],
            ["2016-03-27T03:00:00.000+02:00", "2016-03-27T01:00:00.000Z"],
            ["2016-03-27T02:00:00.000", "2016-03-27T02:00:00.000Z"],
            ["2016-03-27T03:00:00.000", "2016-03-27T03:00:00.000Z"],
            ["2016-03-27T02:00:00.000Z", "2016-03-27T02:00:00.000Z"],
            ["2016-03-27T03:00:00.000Z", "2016-03-27T03:00:00.000Z"],

            ["09:22", undefined],
            ["2013", undefined],
            ["011261", "1961-12-01T00:00:00.000Z"],

            ["932-10-10", undefined],
            ["1932-10-10", "1932-10-10T00:00:00.000Z"],
            ["2016-01-03 09:24:15.123+06:00", "2016-01-03T03:24:15.123Z"],
            ["2016-01-03 09:24:15.123+16:00", "2016-01-02T17:24:15.123Z"],
            ["2016-01-03 09:24:15.123Z", "2016-01-03T09:24:15.123Z"],
        ]);

        runTestSet(assert, testSet, (input) => parseDateTime(input).toISO());
    });

    QUnit.test("parseDateTime: arab locale, latin numbering system as input", async (assert) => {
        const dateFormat = "dd MMM, yyyy";
        const timeFormat = "hh:mm:ss";

        patchWithCleanup(localization, {
            dateFormat,
            timeFormat,
            dateTimeFormat: `${dateFormat} ${timeFormat}`,
        });
        patchWithCleanup(Settings, {
            defaultLocale: "ar-001",
            defaultNumberingSystem: "arab",
        });

        // Check it works with arab
        assert.strictEqual(
            parseDateTime("١٥ يوليو, ٢٠٢٠ ١٢:٣٠:٤٣").toISO().split(".")[0],
            "2020-07-15T12:30:43"
        );

        // Check it also works with latin numbers
        assert.strictEqual(
            parseDateTime("15 07, 2020 12:30:43").toISO().split(".")[0],
            "2020-07-15T12:30:43"
        );
        assert.strictEqual(
            parseDateTime("22/01/2023").toISO().split(".")[0],
            "2023-01-22T00:00:00"
        );
        assert.strictEqual(
            parseDateTime("2023-01-22").toISO().split(".")[0],
            "2023-01-22T00:00:00"
        );
    });
});
