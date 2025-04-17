/** @odoo-module **/

import {
  Component,
  onMounted,
  onWillUpdateProps,
  useRef,
  useEffect,
  xml,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render"; 
import { _t } from "@web/core/l10n/translation";

export class ChartPreview extends Component {
  setup() {
    super.setup(...arguments);
    this.root = useRef("root");
    useEffect(()=>{
      this._render(this.props);
    }); 
  }

  async _render(props) {
    var self = this;
    var $PreviewBord = "";
    try {
      var options = this.props.record.data[this.props.name] ? JSON.parse(this.props.record.data[this.props.name]) : {};
    } catch (err) {
      var options = {};
    }
    this.root.el.innerHTML = "";
    if (options && props.record.data.item_type == "statistics") {
      if (!props.record.data.statistics_with_trend) {
      if (!options.statistics_data) {
        return;
      }
      var $PreviewBord = renderToElement("StatisticsItemBits", { item: options });
      let filter = props.record.data.default_time_frame
        ? props.record.data.default_time_frame.split("_").join(" ")
        : "";
      filter = filter.charAt(0).toUpperCase() + filter.slice(1);
      this.root.el.innerHTML += `<h5 style="padding-bottom: 5px; text-align: center; color: #000000c4;">This data is filtered using '${filter}' dashboard date filter</h5>`;
      this.root.el.appendChild($PreviewBord);
      } else {
      if (!options["statistics_data"] || !options["trend_display_style"]) {
        return;
      }
      var $PreviewBord = await renderToElement("StatisticsItem_WithTrendbits", {
        item: options["item_data"],
        botton_vals: options["bottom_values"],
        statistics_data: options["statistics_data"],
        trend_display_style: options["trend_display_style"],
        trend_primary_color: options["trend_primary_color"],
      });
      var op_data = options.center_values_options.options;
      if (op_data && op_data.series && op_data.series.length) {
        let filter = props.record.data.default_time_frame
        ? props.record.data.default_time_frame.split("_").join(" ")
        : "";
        filter = filter.charAt(0).toUpperCase() + filter.slice(1);
        this.root.el.innerHTML += `<h5 style="padding-bottom: 5px; text-align: center; color: #000000c4;">This data is filtered using '${filter}' dashboard date filter</h5>`;
        this.root.el.appendChild($PreviewBord);
        var ctx = $PreviewBord.querySelector(".trend_line.statistics");
        if (ctx) {
        if (props.record.data.trend_display_style == "style_3") {
          var Chart = echarts.init(ctx, null, { width: 300, height: 150 });
        } else {
          var Chart = echarts.init(ctx, null, { width: 512, height: 200 });
        }
        if (
          options.center_values_options &&
          options.center_values_options.options
        ) {
          Chart.setOption(options.center_values_options.options);
        }
        }
      }
      }
    } else if (props.record.data.item_type == "kpi") {
      if (options.kpi_config && !options.kpi_config.kpi_display_style) {
      return false;
      }
      var $PreviewBord = renderToElement("KpiItemsBits", {
      item: options["item_data"],
      kpi_config: options["kpi_config"],
      });
      if (!options.item_data && !options.kpi_config) {
      return;
      }
      let filter = props.record.data.default_time_frame
      ? props.record.data.default_time_frame.split("_").join(" ")
      : "";
      filter = filter.charAt(0).toUpperCase() + filter.slice(1);
      this.root.el.innerHTML += `<h5 style="padding-bottom: 5px; text-align: center; color: #000000c4;">This data is filtered using '${filter}' dashboard date filter</h5>`;
      this.root.el.appendChild($PreviewBord);
      var ctx = $PreviewBord.querySelector(".progress_line");
      if (options.kpi_config.kpi_display_style == "style_3") {
      this.init_kpi_s3(options);
      } else {
      var Chart = echarts.init(ctx, null, { width: 175, height: 175 });
      Chart.setOption(options.kpi_config.progress_chart_options);
      }
    } else if (props.record.data.item_type == "list_view") {
      if (!options.list_view_data) {
      return;
      }
      const newOptions = Object.assign({}, options);
      if (options?.list_view_data?.list_data)
      newOptions.list_view_data.list_data =
        options?.list_view_data?.list_data.slice(0, 11);
      var $PreviewBord = renderToElement("list_view_item_bits", {
      item: newOptions,
      isArray: (obj) => Array.isArray(obj),
      });
      let filter = props.record.data.default_time_frame
      ? props.record.data.default_time_frame.split("_").join(" ")
      : "";
      filter = filter.charAt(0).toUpperCase() + filter.slice(1);
      this.root.el.innerHTML += `<h5 style="padding-bottom: 5px; text-align: center; color: #000000c4;">This data is filtered using '${filter}' dashboard date filter</h5>`;
      this.root.el.appendChild($PreviewBord);
    } else if (props.record.data.item_type == "embade_iframe") {
      if (!props.record.data.embade_code) {
      return;
      }
      var $PreviewBord = renderToElement("EmbadeIframe", { item: props.record.data });
      $PreviewBord.querySelector('.iframe-body').innerHTML = props.record.data.embade_code;
      this.root.el.appendChild($PreviewBord);
    } else if (options) {
      var $PreviewBord = renderToElement("chart_preview_bits", { item: options });
      let filter = props.record.data.default_time_frame
      ? props.record.data.default_time_frame.split("_").join(" ")
      : "";
      filter = filter.charAt(0).toUpperCase() + filter.slice(1);
      this.root.el.innerHTML += `<h5 style="padding-bottom: 5px; text-align: center; color: #000000c4;">This data is filtered using '${filter}' dashboard date filter</h5>`;
      this.root.el.appendChild($PreviewBord);
      var ctx = this.root.el.querySelector("#d-item-bits");
      var Chart = echarts.init(ctx, null, { width: 500, height: 500 });
      if (
      options.group &&
      !options.group.filter((i) => {
        return i;
      }).length
      ) {
      return;
      }
      if (options.options) {
      Chart.setOption(options.options);
      Chart.resize();
      }
    }
  }

  init_kpi_s3() {
    var progress = this.root.el.querySelector(".progress-per");
    var per = parseFloat(progress.getAttribute("per"));
    progress.style.width = (per > 100 ? 100 : per) + "%";
    var animatedValue = 0;
    var startTime = null;
    function animate(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = timestamp - startTime;
      var stepPercentage = progress / 1000;

      if (stepPercentage < 1) {
      animatedValue = per * stepPercentage;
      progress.setAttribute("per", Math.floor(animatedValue) + "%");
      requestAnimationFrame(animate);
      } else {
      animatedValue = per;
      progress.setAttribute("per", Math.floor(animatedValue) + "%");
      }
    }
    requestAnimationFrame(animate);
  }
}

ChartPreview.template = xml`<div class="container" t-ref="root"></div>`;

export const chartPreview = {
  component: ChartPreview,
  displayName: _t("Chart Preview"),
  supportedTypes: ["char"],
};
registry.category("fields").add("chart_preview_bits", chartPreview);