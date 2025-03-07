/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getBorderWhite, DEFAULT_BG, getColor, hexToRGBA } from "@web/core/colors/colors";
import { formatFloat } from "@web/views/fields/formatters";
import { SEP } from "./graph_model";
import { sortBy } from "@web/core/utils/arrays";
import { loadBundle } from "@web/core/assets";
import { renderToString } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillUnmount, useEffect, useRef, onWillStart } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { cookie } from "@web/core/browser/cookie";

const NO_DATA = _t("No data");
const formatters = registry.category("formatters");

export const LINE_FILL_TRANSPARENCY = 0.4;

/**
 * @param {Object} chartArea
 * @returns {string}
 */
function getMaxWidth(chartArea) {
    const { left, right } = chartArea;
    return Math.floor((right - left) / 1.618) + "px";
}

/**
 * Used to avoid too long legend items.
 * @param {string} label
 * @returns {string} shortened version of the input label
 */
function shortenLabel(label) {
    // string returned could be wrong if a groupby value contain a " / "!
    const groups = label.toString().split(SEP);
    let shortLabel = groups.slice(0, 3).join(SEP);
    if (shortLabel.length > 30) {
        shortLabel = `${shortLabel.slice(0, 30)}...`;
    } else if (groups.length > 3) {
        shortLabel = `${shortLabel}${SEP}...`;
    }
    return shortLabel;
}

export class GraphRenderer extends Component {
    setup() {
        this.model = this.props.model;

        this.rootRef = useRef("root");
        this.canvasRef = useRef("canvas");
        this.containerRef = useRef("container");
        this.actionService = useService("action");

        this.chart = null;
        this.tooltip = null;
        this.legendTooltip = null;

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
        });

        useEffect(() => this.renderChart());
        onWillUnmount(this.onWillUnmount);
    }

    onWillUnmount() {
        if (this.chart) {
            this.chart.destroy();
        }
    }

    /**
     * This function aims to remove a suitable number of lines from the
     * tooltip in order to make it reasonably visible. A message indicating
     * the number of lines is added if necessary.
     * @param {HTMLElement} tooltip
     * @param {number} maxTooltipHeight this the max height in pixels of the tooltip
     */
    adjustTooltipHeight(tooltip, maxTooltipHeight) {
        const sizeOneLine = tooltip.querySelector("tbody tr").clientHeight;
        const tbodySize = tooltip.querySelector("tbody").clientHeight;
        const toKeep = Math.max(
            0,
            Math.floor((maxTooltipHeight - (tooltip.clientHeight - tbodySize)) / sizeOneLine) - 1
        );
        const lines = tooltip.querySelectorAll("tbody tr");
        const toRemove = lines.length - toKeep;
        if (toRemove > 0) {
            for (let index = toKeep; index < lines.length; ++index) {
                lines[index].remove();
            }
            const tr = document.createElement("tr");
            const td = document.createElement("td");
            tr.classList.add("o_show_more", "text-center", "fw-bold");
            td.setAttribute("colspan", "2");
            td.innerText = _t("...");
            tr.appendChild(td);
            tooltip.querySelector("tbody").appendChild(tr);
        }
    }

    /**
     * Creates a custom HTML tooltip.
     * @param {Object} data
     * @param {Object} metaData
     * @param {Object} context see chartjs documentation
     */
    customTooltip(data, metaData, context) {
        const tooltipModel = context.tooltip;
        const { measure, measures, disableLinking, mode } = metaData;
        this.containerRef.el.style.cursor = "";
        this.removeTooltips();
        if (tooltipModel.opacity === 0 || tooltipModel.dataPoints.length === 0) {
            return;
        }
        if (!disableLinking && mode !== "line") {
            this.containerRef.el.style.cursor = "pointer";
        }
        const chartAreaTop = this.chart.chartArea.top;
        const viewContentTop = this.containerRef.el.getBoundingClientRect().top;
        const innerHTML = renderToString("web.GraphRenderer.CustomTooltip", {
            maxWidth: getMaxWidth(this.chart.chartArea),
            measure: measures[measure].string,
            mode: this.model.metaData.mode,
            tooltipItems: this.getTooltipItems(data, metaData, tooltipModel),
        });
        const template = Object.assign(document.createElement("template"), { innerHTML });
        const tooltip = template.content.firstChild;
        this.containerRef.el.prepend(tooltip);

        let top;
        const tooltipHeight = tooltip.clientHeight;
        const minTopAllowed = Math.floor(chartAreaTop);
        const maxTopAllowed = Math.floor(window.innerHeight - (viewContentTop + tooltipHeight)) - 2;
        const y = Math.floor(tooltipModel.y);
        if (minTopAllowed <= maxTopAllowed) {
            // Here we know that the full tooltip can fit in the screen.
            // We put it in the position where Chart.js would put it
            // if two conditions are respected:
            //  1: the tooltip is not cut (because we know it is possible to not cut it)
            //  2: the tooltip does not hide the legend.
            // If it is not possible to use the Chart.js proposition (y)
            // we use the best approximated value.
            if (y <= maxTopAllowed) {
                if (y >= minTopAllowed) {
                    top = y;
                } else {
                    top = minTopAllowed;
                }
            } else {
                top = maxTopAllowed;
            }
        } else {
            // Here we know that we cannot satisfy condition 1 above,
            // so we position the tooltip at the minimal position and
            // cut it the minimum possible.
            top = minTopAllowed;
            const maxTooltipHeight = window.innerHeight - (viewContentTop + chartAreaTop) - 2;
            this.adjustTooltipHeight(tooltip, maxTooltipHeight);
        }
        this.fixTooltipLeftPosition(tooltip, tooltipModel.x);
        tooltip.style.top = Math.floor(top) + "px";

        this.tooltip = tooltip;
    }

    /**
     * Sets best left position of a tooltip approaching the proposal x.
     * @param {HTMLElement} tooltip
     * @param {number} x
     */
    fixTooltipLeftPosition(tooltip, x) {
        let left;
        const tooltipWidth = tooltip.clientWidth;
        const minLeftAllowed = Math.floor(this.chart.chartArea.left + 2);
        const maxLeftAllowed = Math.floor(this.chart.chartArea.right - tooltipWidth - 2);
        x = Math.floor(x);
        if (x < minLeftAllowed) {
            left = minLeftAllowed;
        } else if (x > maxLeftAllowed) {
            left = maxLeftAllowed;
        } else {
            left = x;
        }
        tooltip.style.left = `${left}px`;
    }

    /**
     * Used to format correctly the values in tooltip and y.
     * @param {number} value
     * @param {boolean} [allIntegers=true]
     * @returns {string}
     */
    formatValue(value, allIntegers = true, formatType = "") {
        const largeNumber = Math.abs(value) >= 1000;
        if (formatType) {
            return formatters.get(formatType)(value);
        }
        if (allIntegers && !largeNumber) {
            return String(value);
        }
        if (largeNumber) {
            return formatFloat(value, { humanReadable: true, decimals: 2, minDigits: 1 });
        }
        return formatFloat(value);
    }

    /**
     * Returns the bar chart data
     * @returns {Object}
     */
    getBarChartData() {
        // style data
        const { domains, stacked } = this.model.metaData;
        const { data, lineOverlayDataset } = this.model;
        for (let index = 0; index < data.datasets.length; ++index) {
            const dataset = data.datasets[index];
            // used when stacked
            if (stacked) {
                dataset.stack = domains[dataset.originIndex].description || "";
            }
            // set dataset color
            dataset.backgroundColor = getColor(index, cookie.get("color_scheme"));
        }
        if (lineOverlayDataset) {
            // Mutate the lineOverlayDataset to include the config on how it will be displayed.
            const color = cookie.get("color_scheme") === "dark" ? "ffffff" : "000000";
            Object.assign(lineOverlayDataset, {
                type: "line",
                order: -1,
                tension: 0,
                fill: false,
                borderWidth: 2,
                borderDash: [5, 4],
                borderColor: hexToRGBA(color, LINE_FILL_TRANSPARENCY),
                pointHitRadius: 5,
                pointRadius: 5,
                pointHoverRadius: 10,
                backgroundColor: hexToRGBA(color, LINE_FILL_TRANSPARENCY),
            });
            // We're not mutating the original datasets (`this.model.data.datasets`)
            // because some part of the code depends on it.
            return {
                ...data,
                datasets: [...data.datasets, lineOverlayDataset],
            };
        }

        return data;
    }

    /**
     * Returns the chart config.
     * @returns {Object}
     */
    getChartConfig() {
        const { mode } = this.model.metaData;
        let data;
        switch (mode) {
            case "bar":
                data = this.getBarChartData();
                break;
            case "line":
                data = this.getLineChartData();
                break;
            case "pie":
                data = this.getPieChartData();
        }
        const options = this.prepareOptions();
        return { data, options, type: mode };
    }

    /**
     * Returns an object used to style chart elements independently from
     * the datasets.
     * @returns {Object}
     */
    getElementOptions() {
        const { mode, stacked } = this.model.metaData;
        const elementOptions = {};
        if (mode === "bar") {
            elementOptions.bar = { borderWidth: 1 };
        } else if (mode === "line") {
            elementOptions.line = { fill: stacked, tension: 0 };
        }
        return elementOptions;
    }

    /**
     * @returns {Object}
     */
    getLegendOptions() {
        const { mode } = this.model.metaData;
        const data = this.model.data;
        const refLength = mode === "pie" ? data.labels.length : data.datasets.length;
        const legendOptions = {
            display: refLength <= 20,
            position: "top",
            onHover: this.onlegendHover.bind(this),
            onLeave: this.onLegendLeave.bind(this),
        };
        if (mode === "line") {
            legendOptions.onClick = this.onLegendClick.bind(this);
        }
        if (mode === "pie") {
            legendOptions.labels = {
                generateLabels: (chart) => {
                    return chart.data.labels.map((label, index) => {
                        const hidden = !chart.getDataVisibility(index);
                        const fullText = label;
                        const text = shortenLabel(fullText);
                        const fillStyle =
                            label === NO_DATA
                                ? DEFAULT_BG
                                : getColor(index, cookie.get("color_scheme"));
                        const fontColor =
                            cookie.get("color_scheme") === "dark"
                                ? getColor(15, cookie.get("color_scheme"))
                                : null;
                        return { text, fullText, fillStyle, hidden, index, fontColor };
                    });
                },
            };
        } else {
            const referenceColor = mode === "bar" ? "backgroundColor" : "borderColor";
            legendOptions.labels = {
                generateLabels: (chart) => {
                    const { data } = chart;
                    const labels = data.datasets.map((dataset, index) => {
                        return {
                            text: shortenLabel(dataset.label),
                            fullText: dataset.label,
                            fillStyle: dataset[referenceColor],
                            hidden: !chart.isDatasetVisible(index),
                            lineCap: dataset.borderCapStyle,
                            lineDash: dataset.borderDash,
                            lineDashOffset: dataset.borderDashOffset,
                            lineJoin: dataset.borderJoinStyle,
                            lineWidth: dataset.borderWidth,
                            strokeStyle: dataset[referenceColor],
                            pointStyle: dataset.pointStyle,
                            datasetIndex: index,
                            fontColor:
                                cookie.get("color_scheme") === "dark"
                                    ? getColor(15, cookie.get("color_scheme"))
                                    : null,
                        };
                    });
                    return labels;
                },
            };
        }
        return legendOptions;
    }

    /**
     * Returns line chart data.
     * @returns {Object}
     */
    getLineChartData() {
        const { groupBy, domains, stacked, cumulated } = this.model.metaData;
        const data = this.model.data;
        const color0 = getColor(0, cookie.get("color_scheme"));
        const color1 = getColor(1, cookie.get("color_scheme"));
        for (let index = 0; index < data.datasets.length; ++index) {
            const dataset = data.datasets[index];
            if (groupBy.length <= 1 && domains.length > 1) {
                if (dataset.originIndex === 0) {
                    dataset.fill = "origin";
                    dataset.backgroundColor = hexToRGBA(color0, LINE_FILL_TRANSPARENCY);
                    dataset.borderColor = color0;
                } else if (dataset.originIndex === 1) {
                    dataset.borderColor = color1;
                } else {
                    dataset.borderColor = getColor(index, cookie.get("color_scheme"));
                }
            } else {
                dataset.borderColor = getColor(index, cookie.get("color_scheme"));
            }
            if (cumulated) {
                let accumulator = dataset.cumulatedStart;
                dataset.data = dataset.data.map((value) => {
                    accumulator += value;
                    return accumulator;
                });
            }
            if (data.labels.length === 1) {
                // shift of the real value to right. This is done to
                // center the points in the chart. See data.labels below in
                // Chart parameters
                dataset.data.unshift(undefined);
                dataset.trueLabels.unshift(undefined);
                dataset.domains.unshift(undefined);
            }
            dataset.pointBackgroundColor = dataset.borderColor;
            dataset.pointBorderColor = "rgba(0,0,0,0.2)";
            if (stacked) {
                dataset.backgroundColor = hexToRGBA(dataset.borderColor, LINE_FILL_TRANSPARENCY);
            }
        }
        if (data.datasets.length === 1 && data.datasets[0].originIndex === 0) {
            const dataset = data.datasets[0];
            dataset.fill = "origin";
            dataset.backgroundColor = hexToRGBA(color0, LINE_FILL_TRANSPARENCY);
        }
        // center the points in the chart (without that code they are put
        // on the left and the graph seems empty)
        data.labels = data.labels.length > 1 ? data.labels : ["", ...data.labels, ""];

        return data;
    }

    /**
     * Returns pie chart data.
     * @returns {Object}
     */
    getPieChartData() {
        const { domains } = this.model.metaData;
        const data = this.model.data;
        // style/complete data
        // give same color to same groups from different origins
        const colors = data.labels.map((_, index) => getColor(index, cookie.get("color_scheme")));
        const borderColor = getBorderWhite(cookie.get("color_scheme"));
        for (const dataset of data.datasets) {
            dataset.backgroundColor = colors;
            dataset.borderColor = borderColor;
        }
        // make sure there is a zone associated with every origin
        const representedOriginIndexes = new Set(
            data.datasets.map((dataset) => dataset.originIndex)
        );
        let addNoDataToLegend = false;
        const fakeData = new Array(data.labels.length + 1);
        fakeData[data.labels.length] = 1;
        const fakeTrueLabels = new Array(data.labels.length + 1);
        fakeTrueLabels[data.labels.length] = NO_DATA;
        for (let index = 0; index < domains.length; ++index) {
            if (!representedOriginIndexes.has(index)) {
                data.datasets.push({
                    label: domains[index].description,
                    data: fakeData,
                    trueLabels: fakeTrueLabels,
                    backgroundColor: [...colors, DEFAULT_BG],
                    borderColor,
                });
                addNoDataToLegend = true;
            }
        }
        if (addNoDataToLegend) {
            data.labels.push(NO_DATA);
        }

        return data;
    }

    /**
     * Returns the options used to generate the chart axes.
     * @returns {Object}
     */
    getScaleOptions() {
        const labels = this.model.data.labels;
        const { allIntegers, fieldAttrs, fields, groupBy, measure, measures, mode, stacked } =
            this.model.metaData;
        if (mode === "pie") {
            return {};
        }
        const xAxe = {
            type: "category",
            title: {
                display: Boolean(groupBy.length),
                text: groupBy.length ? fields[groupBy[0].fieldName].string : "",
                color:
                    cookie.get("color_scheme") === "dark"
                        ? getColor(15, cookie.get("color_scheme"))
                        : null,
            },
            ticks: {
                callback: (val, index) => {
                    const value = labels[index];
                    return shortenLabel(value);
                },
                color:
                    cookie.get("color_scheme") === "dark"
                        ? getColor(15, cookie.get("color_scheme"))
                        : null,
            },
        };
        const yAxe = {
            type: "linear",
            title: {
                text: measures[measure].string,
                color:
                    cookie.get("color_scheme") === "dark"
                        ? getColor(15, cookie.get("color_scheme"))
                        : null,
            },
            ticks: {
                callback: (value) =>
                    this.formatValue(value, allIntegers, fieldAttrs[measure]?.widget),
                color:
                    cookie.get("color_scheme") === "dark"
                        ? getColor(15, cookie.get("color_scheme"))
                        : null,
            },
            suggestedMax: 0,
            suggestedMin: 0,
            stacked: mode === "line" && stacked ? stacked : undefined,
        };
        return { x: xAxe, y: yAxe };
    }

    /**
     * This function extracts the information from the data points in
     * tooltipModel.dataPoints (corresponding to datapoints over a given
     * label determined by the mouse position) that will be displayed in a
     * custom tooltip.
     * @param {Object} data
     * @param {Object} metaData
     * @param {Object} tooltipModel see chartjs documentation
     * @returns {Object[]}
     */
    getTooltipItems(data, metaData, tooltipModel) {
        const { allIntegers, domains, mode, groupBy, measure } = metaData;
        const sortedDataPoints = sortBy(tooltipModel.dataPoints, "raw", "desc");
        const items = [];
        for (const item of sortedDataPoints) {
            const index = item.dataIndex;
            // If `datasetIndex` is not found in the `datasets`, then it refers to the `lineOverlayDataset`.
            const dataset = data.datasets[item.datasetIndex] || this.model.lineOverlayDataset;
            let label = dataset.trueLabels[index];
            let value = dataset.data[index];
            const measureWidget = metaData.fieldAttrs[measure]?.widget;
            value = this.formatValue(value, allIntegers, measureWidget);
            let boxColor;
            let percentage;
            if (mode === "pie") {
                if (label === NO_DATA) {
                    value = this.formatValue(0, allIntegers, measureWidget);
                }
                if (domains.length > 1) {
                    label = `${dataset.label} / ${label}`;
                }
                boxColor = dataset.backgroundColor[index];
                const totalData = dataset.data.reduce((a, b) => a + b, 0);
                percentage = totalData && ((dataset.data[index] * 100) / totalData).toFixed(2);
            } else {
                if (groupBy.length > 1 || domains.length > 1) {
                    label = `${label} / ${dataset.label}`;
                }
                boxColor = mode === "bar" ? dataset.backgroundColor : dataset.borderColor;
            }
            items.push({ label, value, boxColor, percentage });
        }
        return items;
    }

    /**
     * Returns the options used to generate chart tooltips.
     * @returns {Object}
     */
    getTooltipOptions() {
        const { data, metaData } = this.model;
        const { mode } = metaData;
        const tooltipOptions = {
            enabled: false,
            external: this.customTooltip.bind(this, data, metaData),
        };
        if (mode === "line") {
            tooltipOptions.mode = "index";
            tooltipOptions.intersect = false;
        }
        return tooltipOptions;
    }

    /**
     * If a group has been clicked on, display a view of its records.
     * @param {MouseEvent} ev
     */
    onGraphClicked(ev) {
        const [activeElement] = this.chart.getElementsAtEventForMode(
            ev,
            "nearest",
            { intersect: true },
            false
        );
        if (!activeElement) {
            return;
        }
        const { datasetIndex, index } = activeElement;
        const { domains } = this.chart.data.datasets[datasetIndex];
        if (domains) {
            this.onGraphClickedFinal(domains[index]);
        }
    }

    /**
     * Overrides the default legend 'onClick' behaviour. This is done to
     * remove all existing tooltips right before updating the chart.
     * @param {Event} ev
     * @param {Object} legendItem
     */
    onLegendClick(ev, legendItem) {
        this.removeTooltips();
        // Default 'onClick' fallback. See web/static/lib/Chart/Chart.js#15138
        const index = legendItem.datasetIndex;
        const meta = this.chart.getDatasetMeta(index);
        meta.hidden = meta.hidden === null ? !this.chart.data.datasets[index].hidden : null;
        this.chart.update();
    }

    /**
     * If the text of a legend item has been shortened and the user mouse
     * hovers that item (actually the event type is mousemove), a tooltip
     * with the item full text is displayed.
     * @param {Event} ev
     * @param {Object} legendItem
     */
    onlegendHover(ev, legendItem) {
        ev = ev.native;
        this.canvasRef.el.style.cursor = "pointer";
        /**
         * The string legendItem.text is an initial segment of legendItem.fullText.
         * If the two coincide, no need to generate a tooltip. If a tooltip
         * for the legend already exists, it is already good and does not
         * need to be recreated.
         */
        const { fullText, text } = legendItem;
        if (this.legendTooltip || text === fullText) {
            return;
        }
        const viewContentTop = this.canvasRef.el.getBoundingClientRect().top;
        const legendTooltip = Object.assign(document.createElement("div"), {
            className: "o_tooltip_legend popover p-3 pe-none",
            innerText: fullText,
        });
        legendTooltip.style.top = `${ev.clientY - viewContentTop}px`;
        legendTooltip.style.maxWidth = getMaxWidth(this.chart.chartArea);
        this.containerRef.el.appendChild(legendTooltip);
        this.fixTooltipLeftPosition(legendTooltip, ev.clientX);
        this.legendTooltip = legendTooltip;
    }

    /**
     * If there's a legend tooltip and the user mouse out of the
     * corresponding legend item, the tooltip is removed.
     */
    onLegendLeave() {
        this.canvasRef.el.style.cursor = "";
        this.removeLegendTooltip();
    }

    /**
     * Prepares options for the chart according to the current mode
     * (= chart type). This function returns the parameter options used to
     * instantiate the chart.
     */
    prepareOptions() {
        const { disableLinking, mode } = this.model.metaData;
        const options = {
            maintainAspectRatio: false,
            scales: this.getScaleOptions(),
            plugins: {
                legend: this.getLegendOptions(),
                tooltip: this.getTooltipOptions(),
            },
            elements: this.getElementOptions(),
        };
        if (!disableLinking && mode !== "line") {
            options.onClick = this.onGraphClicked.bind(this);
        }
        return options;
    }

    /**
     * Removes the legend tooltip (if any).
     */
    removeLegendTooltip() {
        if (this.legendTooltip) {
            this.legendTooltip.remove();
            this.legendTooltip = null;
        }
    }

    /**
     * Removes all existing tooltips (if any).
     */
    removeTooltips() {
        if (this.tooltip) {
            this.tooltip.remove();
            this.tooltip = null;
        }
        this.removeLegendTooltip();
    }

    /**
     * Instantiates a Chart (Chart.js lib) to render the graph according to
     * the current config.
     */
    renderChart() {
        if (this.chart) {
            this.chart.destroy();
        }
        const config = this.getChartConfig();
        this.chart = new Chart(this.canvasRef.el, config);
    }

    /**
     * Execute the action to open the view on the current model.
     *
     * @param {Array} domain
     * @param {Array} views
     * @param {Object} context
     */
    openView(domain, views, context) {
        this.actionService.doAction(
            {
                context,
                domain,
                name: this.model.metaData.title,
                res_model: this.model.metaData.resModel,
                target: "current",
                type: "ir.actions.act_window",
                views,
            },
            {
                viewType: "list",
            }
        );
    }
    /**
     * @param {string} domain the domain of the clicked area
     */
    onGraphClickedFinal(domain) {
        const { context } = this.model.metaData;

        Object.keys(context).forEach((x) => {
            if (x === "group_by" || x.startsWith("search_default_")) {
                delete context[x];
            }
        });

        const views = {};
        for (const [viewId, viewType] of this.env.config.views || []) {
            views[viewType] = viewId;
        }
        function getView(viewType) {
            return [views[viewType] || false, viewType];
        }
        const actionViews = [getView("list"), getView("form")];
        this.openView(domain, actionViews, context);
    }

    /**
     * @param {Object} param0
     * @param {string} param0.measure
     */
    onMeasureSelected({ measure }) {
        this.model.updateMetaData({ measure });
    }

    /**
     * @param {"bar"|"line"|"pie"} mode
     */
    onModeSelected(mode) {
        this.model.updateMetaData({ mode });
    }

    /**
     * @param {"ASC"|"DESC"} order
     */
    toggleOrder(order) {
        const { order: currentOrder } = this.model.metaData;
        const nextOrder = currentOrder === order ? null : order;
        this.model.updateMetaData({ order: nextOrder });
    }

    toggleStacked() {
        const { stacked } = this.model.metaData;
        this.model.updateMetaData({ stacked: !stacked });
    }

    toggleCumulated() {
        const { cumulated } = this.model.metaData;
        this.model.updateMetaData({ cumulated: !cumulated });
    }
}

GraphRenderer.template = "web.GraphRenderer";
GraphRenderer.components = { Dropdown, DropdownItem };
GraphRenderer.props = ["class?", "model", "buttonTemplate"];
