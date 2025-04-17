/** @odoo-module **/

import {
  Component,
  onWillStart,
  onMounted,
  useState,
  useRef,
  onWillUnmount,
  onWillDestroy,
  status, 
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session"; 
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render"; 
import { makeContext } from "@web/core/context";
import { View } from "@web/views/view";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { isMobileOS } from "@web/core/browser/feature_detection";
// import { rpc } from "@web/core/network/rpc";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { DuplicateConfirmation } from "@analytix_dashboard_bits/dialogs/DuplicateConfirmation";
import { CopyEmbadeCodeDialog } from "@analytix_dashboard_bits/dialogs/CopyEmbadeCodeDialog";
// import { user } from "@web/core/user";

function get_time_frames() {
  return {
    default: "Default",
    today: "Today",
    yesterday: "Yesterday",
    next_day: "Next Day",
    next_week: "Next Week",
    next_month: "Next Month",
    next_year: "Next Year",
    this_week: "This Week",
    this_month: "This Month",
    this_year: "This Year",
    last_week: "Last Week",
    last_month: "Last Month",
    last_two_months: "Last 2 Months",
    last_three_months: "Last 3 Months",
    last_year: "Last Year",
    last_24_hr: "Last 24 Hr",
    last_10: "Last 10 Days",
    last_30: "Last 30 Days",
    last_60: "Last 60 Days",
    last_90: "Last 90 Days",
    last_365: "Last 365 Days",
    custom: "Custom Range",
  };
}
const { DateTime } = luxon;

class DashboardControllerBits extends Component {
  setup() {
    super.setup(); 
    this.orm = useService("orm");
    this.state = useState({});
    this.action = useService("action");
    this.notification = useService("notification");
    this.el = useRef("el");
    this.grid = useRef("grid");
    this.busService = this.env.services.bus_service;
    this.dialogService = this.env.services.dialog;

    onWillStart(async () => {
      this.state.dashboard_data = [];
      this.state.charts = [];
      this.state.viewData = [];
      this.state.dashboard_id = this.props.action?.context?.params?.dashboard_id
        ? parseInt(this.props.action?.context?.params?.dashboard_id)
        : parseInt(this.props?.action?.params?.dashboard_id);
      this.state.visual_options = {
        staticGrid: true,
        float: false,
        styleInHead: true,
        cellHeight: 100,
        verticalMargin: 8,
      };
      this.state.editMode = false;
      if (this.props.action?.context?.params?.default_color_theme) {
        this.state.color_theme =
          this.props.action?.context?.params?.default_color_theme;
      } else {
        if (
          this.props?.action?.params &&
          this.props?.action?.params?.default_color_theme
        ) {
          this.state.color_theme =
            this.props?.action?.params?.default_color_theme;
        } else {
          this.state.color_theme = false;
        }
      } 
      this.state.time_frame = this.props.action?.context?.params
        ?.default_time_frame
        ? this.props.action?.context?.params?.default_time_frame
        : this.props?.action?.params?.default_time_frame
        ? this.props?.action?.params?.default_time_frame
        : "default";
      this.state.view_mode = this.props.action?.context?.params
        ?.default_view_mode
        ? this.props.action?.context?.params?.default_view_mode
        : this.props?.action?.params?.default_view_mode
        ? this.props?.action?.params?.default_view_mode
        : false;

      this.state.all_time_frames = get_time_frames();
      this.state.is_filter = false;
      this.state.all_color_themes = {};
 
      this.state.from_date = DateTime.now();
      this.state.to_date = DateTime.now();
      this.state.applied_filters = [];
      this.state.filter_data = {};
      this.state.fav_filters = [];
      this.state.isAdded = false;
      this.busService.subscribe("dashboard_notify", (params) => {  
        this._onNotification(params)
      }); 
    });
    onMounted(async () => {
      // Load data
      if (this.state.dashboard_id) {
        let defs = [];
        defs.push(this.loadFavFilters());
        defs.push(this.loadDashboardData());
        defs.push(this.load_theme_data());
        await Promise.all(defs);
        await this.on_attach_callback();
      }
      document.documentElement.style.setProperty(
        "--dash_primary_color",
        this.state.dashboard_data.default_theme_paletts[0]
      );
      document.documentElement.style.setProperty(
        "--dash_secondary_color",
        this.state.dashboard_data.default_theme_paletts[1]
      );
      document
        .getElementById("body_container_bits")
        .addEventListener("click", this.handleOnclickEvents.bind(this));
      // Select the target node
      const target = document.getElementById("default_view");

      // Create an observer instance
      const observer = new MutationObserver(this.onMutation.bind(this));

      // Configuration of the observer
      const obs_config = { childList: true, subtree: true };

      // Start observing the target node for configured mutations
      document.addEventListener("click", (ev) => {
        ev.stopPropagation();
        document
          .querySelectorAll("body .header_container_bits .show")
          .forEach((element) => {
            element.classList.remove("show");
          });
      });
      observer.observe(target, obs_config);
    });

    onWillUnmount(() => {
      document
        .getElementById("body_container_bits")
        .removeEventListener("click", this.handleOnclickEvents.bind(this));
    });
    // onWillDestroy(() => {
    //   this.busService.unsubscribe("dashboard_notify");
    // });
  }
  onClickHome(e) {
    this.action.doAction({
      type: "ir.actions.client",
      tag: "bits_all_dashboard_action",
    });
  }
  handleOnclickEvents(ev) {
    if (ev.target.classList.contains("item_menu_dropdown_bits")) {
      // Perform your action when the button is clicked
      this.toggleDropdownClass(ev);
    } else if (ev.target.classList.contains("edit_item_bits")) {
      this.onClickEditItem(ev);
    } else if (ev.target.classList.contains("export_item_bits")) {
      this.onClickExportItem(ev);
    } else if (ev.target.classList.contains("duplicate_item_bits")) {
      this.onClickDupicateItem(ev);
    } else if (ev.target.classList.contains("delete_item_bits")) {
      this.onClickDeleteItem(ev);
    } else if (ev.target.classList.contains("oe_close")) {
      this.deleteCustomView(ev);
    } else if (ev.target.classList.contains("pg-v")) {
      this.onClickPager(ev);
    } else if (ev.target.classList.contains("sortable-itlems-list")) {
      this.onClickSort(ev);
    } else if (ev.target.classList.contains("statistics-bits")) {
      this.onClickStatistics(ev);
    }
  }
  onMutation(mutation) {
    const target = document.getElementById("default_view").cloneNode(true); 
    target.querySelector("#o_control_panel")?.remove();
    const children = target.children;
    let grid_config = this.state.dashboard_data.grid_config;
    for (let i = 0; i < children.length; i++) {
      const data = this.state.viewData[i];
      if (grid_config?.[data.node.id]) {
        this.Grid.addWidget(children[i], {
          id: data.node.id,
          x: grid_config[data.node.id].x,
          y: grid_config[data.node.id].y,
          w: grid_config[data.node.id].w,
          h: grid_config[data.node.id].h,
          autoPosition: grid_config[data.node.id]["autoPosition"],
          minW: grid_config[data.node.id].minW,
          maxW: grid_config[data.node.id].maxW,
          minH: grid_config[data.node.id].minH,
          maxH: grid_config[data.node.id].maxH,
        });
      } else {
        this.Grid.addWidget(children[i], {
          id: data.node.id,
          x: 0,
          y: 0,
          w: 6,
          h: 4,
          autoPosition: true,
          minW: 3,
          maxW: 12,
          minH: 3,
          maxH: 12,
        });
      }
    }
    this.state.isAdded = true;
  }
  // @deprecated
  async _onNotification(notifications) {   
    debugger
    if (this.state && this?.__owl__?.component && status(this.__owl__.component) != "destroyed") {
      var self = this;
      if (notifications.updates) {
        var type = notifications?.type;
        var updates = notifications?.updates;
        if (!updates) {
          return;
        }
        if (updates.dashboard_ids.includes(this.state.dashboard_id) &&
          ["model_update_notify","item_update_notify","ditem_create_notify","theme_add_nitify",].includes(type)
        ) {  
          self.loadDashboardData().then(() => {
            self.on_attach_callback();
          });
        }  
      }
    }
  }
  async on_attach_callback() {
    var gridElement = document.querySelector(".grid-items-container-bits .grid-stack");
    if (gridElement) {gridElement.innerHTML = "";}
    this.state.viewData = [];
    this._load_analytics();
    // this.initLayoutMode();
  }
  loadFavFilters() {
    var self = this;
    return this.orm
      .call(
        "dashboard.bits",
        "get_fav_filtrer_data",
        [this.state.dashboard_id],
        { context: self.prepareContex() }
      )
      .then(function (result) {
        self.state.fav_filters = result;
        if (result.length > 0) {
          result.forEach(function (res) {
            if (res.is_active && res.filters_value.length > 0) {
              res.filters_value.forEach(function (val) {
                self.state.applied_filters.push(val);
              });
            }
          });
        }
      });
  }
  loadDashboardData() {
    try {
      var self = this;
      return this.orm
        .call(
          "dashboard.bits",
          "get_dashboard_data",
          [this.state.dashboard_id],
          { context: self.prepareContex() }
        )
        .then(function (result) {
          self.state.dashboard_data = result;
          self.state.userid = result.user_id;
          if (self.state.dashboard_data.default_from_date)
            self.state.from_date = DateTime.fromISO(
              self.state.dashboard_data.default_from_date
            );
          if (self.state.dashboard_data.default_to_date)
            self.state.to_date = DateTime.fromISO(
              self.state.dashboard_data.default_to_date
            );
        });
    } catch (e) {
      return e;
    }
  }
  load_theme_data() {
    var self = this;
    this.orm.call("dashboard.themes", "get_themes", []).then(function (result) {
      self.state.all_color_themes = result;
    });
  }
  async fetch_items_data(updates, notifications = false) {
    var self = this;
    var notify = notifications;
    var items = notify[0].payload.updates;
    if (!items.length) {
      return;
    }
    var item_ids = items.map((i) => {
      return i.item_id;
    });
    return await this.orm
      .call("dashboard.item.bits", "prepare_items_data", [item_ids], {
        context: self.prepareContex(),
      })
      .then(function (result) {
        items.forEach((value, index) => {
          if (self.dashboard_id != value.dashboard_id) {
            return;
          }
          self.state.dashboard_data.dashboard_items[value.item_id] =
            result[index][value.item_id];
        });
        self.on_attach_callback();
      });
  }
  async fetch_item_data(updates, notifications = false) {
    var self = this;
    var item_id = updates.item_id;
    return await await this.orm
      .call("dashboard.bits", "get_grid_config", [this.dashboard_id])
      .then(async function (config) {
        self.state.dashboard_data.grid_config = config;
        return await self.orm
          .call("dashboard.item.bits", "prepare_item_data", [item_id], {
            context: self.prepareContex(),
          })
          .then(function (result) {
            if (!result.item_data) {
              return;
            }
            self.state.dashboard_data.dashboard_items[item_id] = result;
            self.on_attach_callback();
          });
      });
  }
  async get_grid_config() {
    return await this.orm.call(
      "dashboard.bits",
      "search_read",
      [[this.dashboard_id]],
      {
        fields: ["grid_config"],
      }
    );
  }
  prepareContex() {
    var context = {
      time_frame: this.state.time_frame,
      from_date: this.state.from_date.toISODate(),
      to_date: this.state.to_date.toISODate(),
      color_theme: parseInt(this.state.color_theme),
      filters: this.state.applied_filters,
      view_mode: this.state.view_mode,
    };
    return Object.assign(context, {});
  }
  _load_analytics() { 
    var self = this;
    var $gridstackContainer = this.el.el.querySelector(
      ".grid-items-container-bits .grid-stack"
    );
    if (this.Grid) {
      this.Grid.removeAll();
    }
    this.Grid = GridStack.init(this.state.visual_options, $gridstackContainer);
    this.DisableEditMode();
    if (
      this.state.view_mode &&
      this.state.view_mode == "dark" &&
      document.querySelector(".container_bits").innerHTML
    ) {
      document.body
        .querySelector(".o_action .o_content")
        .classList.add("dark_mode_bits");
    } else {
      document.body
        .querySelector(".o_action .o_content")
        .classList.remove("dark_mode_bits");
    }
    var dashboard_items = this.state.dashboard_data.dashboard_items;
    // custom_views
    this._render_visuals(dashboard_items);
    this.Grid.on("resize", function (event, elem) {
      self.resize_chart();
    });
  }
  // custom_view
  async _render_view(dashboard_view, grid_config = {}) {
    if (!dashboard_view) {
      return;
    }
    try {
      this._createController({
        vnode: dashboard_view,
        actionID: dashboard_view.action_id,
        context: dashboard_view.context_to_save,
        domain: JSON.parse(dashboard_view.domain),
        viewType: dashboard_view.view_mode,
      });
    } catch (err) {
      console.log(err);
    }
  }

  async _createController(params) {
    let result = await rpc("/web/action/load", {
      action_id: params.actionID,
    });
    if (!result) {
      // action does not exist
      this.isValid = false;
      // this.state.viewData.push({ node: params.node, value: false });
      return;
    }
    const viewMode = params.viewType || result.views[0][1];
    const formView = result.views.find((v) => v[1] === "form");
    if (formView) {
      this.formViewId = formView[0];
    }
    let viewProps = {
      resModel: result.res_model,
      type: viewMode,
      display: { controlPanel: false },
      selectRecord: (resId) => this.selectRecord(result.res_model, resId),
    };
    const view = result.views.find((v) => v[1] === viewMode);
    if (view) {
      viewProps.viewId = view[0];
    }
    const searchView = result.views.find((v) => v[1] === "search");
    viewProps.views = [
      [viewProps.viewId || false, viewMode],
      [(searchView && searchView[0]) || false, "search"],
    ];

    if (params.context) {
      viewProps.context = makeContext([
        params.context,
        { lang: user.context.lang },
      ]);
      if ("group_by" in viewProps.context) {
        const groupBy = viewProps.context.group_by;
        viewProps.groupBy = typeof groupBy === "string" ? [groupBy] : groupBy;
      }
      if ("comparison" in viewProps.context) {
        const comparison = viewProps.context.comparison;
        if (
          comparison !== null &&
          typeof comparison === "object" &&
          "domains" in comparison &&
          "fieldName" in comparison
        ) {
          // Some comparison object with the wrong form might have been stored in db.
          // This is why we make the checks on the keys domains and fieldName
          viewProps.comparison = comparison;
        }
      }
    }
    if (params.domain) {
      viewProps.domain = params.domain;
    }
    if (viewMode === "list") {
      viewProps.allowSelectors = false;
    }
    this.state.viewData.push({ node: params.vnode, value: viewProps });
  }

  selectRecord(resModel, resId) {
    this.action.doAction({
      type: "ir.actions.act_window",
      res_model: resModel,
      views: [[this.formViewId, "form"]],
      res_id: resId,
    });
  }
  deleteCustomView(ev) {
    var self = this;
    const dataID = ev.target.parentNode.parentNode.dataset.id.split("_");
    const id = dataID[2]? parseInt(dataID[2]):false;
    this.orm
      .call("dashboard.bits", "remove_custom_view", [this.dashboard_id, id])
      .then((res) => {
        if (res) {
          self.loadDashboardData().then(() => {
            self.on_attach_callback();
          });
        }
      });
  }

  _render_visuals(dashboard_items) {
    var self = this;
    var grid_config = this.state.dashboard_data.grid_config;
    if (!grid_config) {
      grid_config = {};
    } 
    let sorted_grid_keys = this._sort_grid_data(grid_config);
    sorted_grid_keys.forEach((key) => {
      let item = dashboard_items[key];
      if (!item || !item.display_type) {
        return;
      }
      // Custom view
      if (self.state.dashboard_data.has_group_admin_bits) {
        if (item.display_type == "default_base_view") {
          this.$item_header = renderToElement("GridItemCustomHeader", {});
        } else {
          this.$item_header = renderToElement("GridItemHeader", { item: item });
        }
      }
      if (
        ["statistics", "statistics_with_trend_bits"].includes(item.display_type)
      ) {
        this.render_statistics(item, grid_config);
      } else if (["kpi"].includes(item.display_type)) {
        this.render_kpi_view(item, grid_config);
      } else if (["list_view"].includes(item.display_type)) {
        this.render_list_view(item, grid_config);
      } else if (["geo_map"].includes(item.display_type)) {
        this.render_map_view(item, grid_config);
      } else if (["embade_iframe"].includes(item.display_type)) {
        this._render_iframe(item, grid_config);
      } else if (["default_base_view"].includes(item.display_type)) {
        this._render_view(item.action, grid_config);
      } else {
        this.render_chart_view(item, grid_config);
      }
    });
  }
  _sort_grid_data(config) {
    let sorted_conf = Object.entries(config).sort(
      (a, b) => a[1].y - b[1].y || a[1].x - b[1].x
    );
    let sorted_keys = [];
    sorted_conf.forEach((i) => sorted_keys.push(i[0]));
    let d_items_keys = Object.keys(this.state.dashboard_data.dashboard_items);
    d_items_keys.forEach((item_key) => {
      if (!sorted_keys.includes(item_key)) {
        sorted_keys.push(item_key);
      }
    });
    return sorted_keys;
  }
  prepare_position_object(grid_config, item) {
    // @depricated
    let autoPosition = isMobileOS() ? true : false;
    let config_obj = grid_config["item_" + item.item_data.id]
      ? grid_config["item_" + item.item_data.id]
      : grid_config[item.item_data.id];
    // ----------------------------------------------------------------
    return {
      id: item.item_data.id,
      x: config_obj["x"],
      y: config_obj["y"],
      w: config_obj["w"],
      h: config_obj["h"],
      autoPosition: autoPosition ? true : config_obj["autoPosition"],
      minW: config_obj["minW"],
      maxW: config_obj["maxW"],
      minH: config_obj["minH"],
      maxH: config_obj["maxH"],
    };
  }
  render_statistics(item, grid_config) {
    if (!item.item_data.statistics_with_trend) {
      if (!item.statistics_data || !item.display_type) {
        return;
      }
      var ItemElement = renderToElement("StatisticsItemBits", { item: item });
      if(this.$item_header){
        ItemElement.querySelector(".grid-stack-item-content").prepend(
          this.$item_header
        );
      }
      // ----------------------------------------------------------------
      // Statistics item
      // ----------------------------------------------------------------
      let grid_id = "item_" + String(item.item_data.id);
      if (grid_id in grid_config) {
        this.Grid.addWidget(
          ItemElement,
          this.prepare_position_object(grid_config, item)
        );
      } else {
        this.Grid.addWidget(ItemElement, {
          id: item.item_data.id,
          x: 0,
          y: 0,
          w: 3,
          h: 2,
          autoPosition: true,
          minW: 2,
          maxW: 3,
          minH: 2,
          maxH: 2,
        });
      }
    } else {
      // ----------------------------------------------------------------
      // Statistics with trens item
      // ----------------------------------------------------------------
      if (
        !item.center_values_options ||
        !item.statistics_data ||
        !item.bottom_values
      ) {
        return;
      }
      var ItemElement = renderToElement("StatisticsItem_WithTrendbits", {
        item: item["item_data"],
        botton_vals: item["bottom_values"],
        statistics_data: item["statistics_data"],
        trend_display_style: item["trend_display_style"],
        trend_primary_color: item["trend_primary_color"],
        apply_background: item["apply_background"],
      });

      if(this.$item_header){
        ItemElement.querySelector(".grid-stack-item-content").prepend(
          this.$item_header
        );
      }
      let grid_id = "item_" + String(item.item_data.id);
      if (grid_id in grid_config) {
        this.Grid.addWidget(
          ItemElement,
          this.prepare_position_object(grid_config, item)
        );
      } else {
        this.Grid.addWidget(ItemElement, {
          id: item.item_data.id,
          x: 0,
          y: 0,
          w: 3,
          h: 3,
          autoPosition: true,
          minW: 2,
          maxW: 6,
          minH: 3,
          maxH: 3,
        });
      }
      var ctx = ItemElement.querySelector(".trend_line.statistics");
      if (item.center_values_options) {
        if (item.item_data.trend_display_style == "style_1") {
          var Chart = echarts.init(ctx, this.view_mode, {
            height: 125,
          });
        } else {
          var Chart = echarts.init(ctx, this.view_mode);
        }
        if (item.center_values_options && item.center_values_options.options) {
          Chart.setOption(item.center_values_options.options);
          this.state.charts.push(Chart);
        }
      }
    }
  }
  render_kpi_view(item, grid_config) {
    if (item.kpi_config && !item.kpi_config.kpi_display_style) {
      return false;
    }
    var ItemElement = renderToElement("KpiItemsBits", {
      item: item["item_data"],
      kpi_config: item["kpi_config"],
    });
    if(this.$item_header){
        ItemElement.querySelector(".grid-stack-item-content").prepend(
          this.$item_header
        );
      }
    let grid_id = "item_" + String(item.item_data.id);
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement,
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement, {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 3,
        h: 2,
        autoPosition: true,
        minW: 2,
        maxW: 3,
        minH: 2,
        maxH: 3,
      });
    }
    var ctx = ItemElement.querySelector(".kpi.progress_line");
    if (item.kpi_config.kpi_display_style == "style_3") {
      this.init_kpi_s3(ItemElement);
    } else {
      var Chart = echarts.init(ctx, null, {
        width: 175,
        height: 175,
      });
      Chart.setOption(item.kpi_config.progress_chart_options);
      this.state.charts.push(Chart);
    }
  }
  init_kpi_s3(ItemElement) {
    var $progress = ItemElement.querySelector(".progress-per");
    var per = parseFloat($progress.getAttribute("per"));
    if (per > 100) {
      $progress.style.width = "100%";
    } else {
      $progress.style.width = per + "%";
    }
    var animatedValue = 0;
    var startTime = null;
    function animate(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = timestamp - startTime;
      var stepPercentage = progress / 1000;

      if (stepPercentage < 1) {
        animatedValue = per * stepPercentage;
        $progress.setAttribute("per", Math.floor(animatedValue) + "%");
        requestAnimationFrame(animate);
      } else {
        animatedValue = per;
        $progress.setAttribute("per", Math.floor(animatedValue) + "%");
      }
    }
    requestAnimationFrame(animate);
  }
  render_list_view(item, grid_config) {
    var self = this;
    if (!item.list_view_data) {
      return;
    }
    var ItemElement = renderToElement("list_view_item_bits", {
      item: item,
      primary_color: this.color_theme,
      isArray: (obj) => Array.isArray(obj),
    });
    if(this.$item_header){
        ItemElement.querySelector(".grid-stack-item-content").prepend(
          this.$item_header
        );
      }
    let grid_id = "item_" + String(item.item_data.id);
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement,
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement, {
        id: item.item_data.id,
        w: 5,
        h: 6,
        x: 0,
        y: 0,
        autoPosition: true,
        minW: 3,
        maxW: 8,
        minH: 3,
        maxH: 8,
      });
    }
  }
  render_map_view(item, grid_config) {
    var self = this;
    var ItemElement = renderToElement("CountryMapBits", { item: item });
    let grid_id = "item_" + String(item.item_data.id);
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement,
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement, {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 4,
        h: 2,
        autoPosition: true,
        minW: 2,
        maxW: 12,
        minH: 2,
        maxH: 2,
      });
    }
    var ctx = ItemElement.querySelector(
      "#" + item.item_data.id + "_" + item.item_data.item_type
    );
    var Chart = echarts.init(ctx, this.state.view_mode);
    if(this.$item_header){
      ItemElement.querySelector(".grid-stack-item-content").prepend(
        this.$item_header
      );
    }
    // item.options.tooltip.formatter = function (params) {
    //   var value = (params.value + "").split(".");
    //   value =
    //     value[0].replace(/(\d{1,3})(?=(?:\d{3})+(?!\d))/g, "$1,") +
    //     "." +
    //     value[1];
    //   return params.seriesName + "<br/>" + params.name + " : " + value;
    // };
    Chart.setOption(item.options);
  }
  render_chart_view(item, grid_config) {
    var ItemElement = renderToElement("GridstackItemBits", {
      item: item["item_data"],
    });
    let grid_id = "item_" + String(item.item_data.id);
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement,
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement, {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 4,
        h: 3,
        autoPosition: true,
        minW: 2,
        maxW: 12,
        minH: 2,
        maxH: 12,
      });
    }
    if (item.group && item.group.length <= 0) {
      ItemElement.querySelector(".grid-stack-item-content > div")[1].remove();
      ItemElement.querySelector(".grid-stack-item-content").append(
        renderToElement("NoDataBits")
      );
      if(this.$item_header){
        ItemElement.querySelector(".grid-stack-item-content").prepend(
          this.$item_header
        );
      }
      return;
    }
    // var ctx = ItemElement.querySelector("#" + item.item_data.id + "_" + item.item_data.item_type);
    var chartClass = this.get_chart_class(item.display_type);
    var ctx = ItemElement.querySelector(chartClass);
    // ".line.grid-stack-item-content"); 
    var Chart = echarts.init(ctx, this.state.view_mode);
    if(this.$item_header){
      ItemElement.querySelector(".grid-stack-item-content").prepend(
        this.$item_header
      );
    }
    try {
      Chart.setOption(item.options);
      this.state.charts.push(Chart);
    } catch (e) {
      ItemElement.querySelector(".grid-stack-item-content > div").remove();
      ItemElement.querySelector(".grid-stack-item-content > div").remove();
      ItemElement.querySelector(".grid-stack-item-content").append(renderToElement("NoDataBits"));
      if(this.$item_header){
        ItemElement.querySelector(".grid-stack-item-content").prepend(this.$item_header);
      }
    }
  }
  _render_iframe(item, grid_config) {
    var ItemElement = renderToElement("EmbadeIframe", { item: item.item_data });
    ItemElement.querySelector(".iframe-header").append(this.$item_header);
    ItemElement.querySelector(".iframe-body").innerHTML =
      item.item_data.embade_code;
    let grid_id = "item_" + String(item.item_data.id);
    if (grid_id in grid_config) {
      this.Grid.addWidget(
        ItemElement,
        this.prepare_position_object(grid_config, item)
      );
    } else {
      this.Grid.addWidget(ItemElement, {
        id: item.item_data.id,
        x: 0,
        y: 0,
        w: 6,
        h: 6,
        autoPosition: true,
        minW: 3,
        maxW: 12,
        minH: 3,
        maxH: 12,
      });
    }
  }
  resize_chart() {
    if (this.state.charts) {
      this.state.charts.forEach((element) => {
        element.resize();
      });
    }
  }
  get_chart_class(type) {
    if (!type) {
      return "";
    }
    if (type == "line") {
      return ".line.grid-stack-item-content";
    } else if (type == "bar") {
      return ".bar.grid-stack-item-content";
    } else if (type == "pie") {
      return ".pie.grid-stack-item-content";
    } else if (type == "radar") {
      return ".radar.grid-stack-item-content";
    } else if (type == "funnel") {
      return ".funnel.grid-stack-item-content";
    }
  }
  // Edit dashboard layout events
  // ----------------------------------------------------------------
  //           EDIT DASHBOAR LAYOUT EVENTS
  // ----------------------------------------------------------------
  onEditGridLayout(ev) {
    this.Grid.setStatic(false);
    this.state.editMode = true;
    this.el.el.querySelector(".bf_edit_controls").classList.add("d-none");
    this.el.el.querySelector(".af_edit_controls").classList.remove("d-none");
    if (this.Grid) {
      this.Grid.enable();
    }
  }
  onSaveGridLayout(ev) {
    var configuration = this.get_current_grid_config();
    var model = "dashboard.bits";
    var rec_id = this.state.dashboard_data.dashboard_id;
    this.orm.call(model, "write", [
      rec_id,
      {
        grid_config: JSON.stringify(configuration),
      },
    ]);
    this.state.dashboard_data.grid_config = configuration;
    this.DisableEditMode();
    this.resize_chart();
  }
  toggleDropdownClass(ev) {
    const parent = ev.target.parentNode;
    ev.stopPropagation();
    parent.querySelector(".dropdown-menu")?.classList.toggle("show"); 
  }
  onDiscartGridLayout(ev) {
    this.state.editMode = false;
    this.DisableEditMode();
    this.on_attach_callback();
  }
  DisableEditMode(ev) {
    this.Grid.setStatic(true);
    this.el.el.querySelector(".bf_edit_controls")?.classList.remove("d-none");
    this.el.el.querySelector(".af_edit_controls")?.classList.add("d-none");
    this.Grid.commit();
  }
  get_current_grid_config(ev) {
    var curr_grid_data =
      document.querySelector(".grid-stack").gridstack.el.gridstack.engine.nodes;
    var configuration = {};
    if (this.state.dashboard_data.grid_config) {
      configuration = this.state.dashboard_data.grid_config;
    }
    Object.keys(curr_grid_data).forEach((element) => {
      configuration["item_" + String(curr_grid_data[element].id)] = {
        x: curr_grid_data[element]["x"],
        y: curr_grid_data[element]["y"],
        h: curr_grid_data[element]["h"],
        w: curr_grid_data[element]["w"],
        minH: curr_grid_data[element]["minH"] || false,
        maxH: curr_grid_data[element]["maxH"] || false,
        maxW: curr_grid_data[element]["maxW"] || false,
        minW: curr_grid_data[element]["minW"] || false,
      };
    });
    return configuration;
  }
  // ----------------------------------------------------------------
  //           OVER EDIT DASHBOAR LAYOUT EVENTS
  // ----------------------------------------------------------------

  // ----------------------------------------------------------------
  //           LIST VIEW EVENTS START
  // ----------------------------------------------------------------
  onClickPager(e) {
    var self = this;
    var target = e.target;
    var target_event = target.getAttribute("data-event");
    var curr_list = target.parentElement
      .querySelector(".records-count-bits")
      .getAttribute("data-count");
    var item_id = parseInt(target.getAttribute("data-itemid"));
    var model = target.getAttribute("data-model");
    var item = target.closest(".grid-stack-item-content");
    this.page;
    var order_by = target;
    this.orm
      .call("dashboard.bits", "prepare_more_list_data", [
        item_id,
        {
          model: parseInt(model),
          target_event: target_event,
          curr_list: parseInt(curr_list),
          order_by: order_by,
        },
        this.dashboard_id,
      ])
      .then(function (result) {
        var list_items = renderToElement("MoreItemsBits", {
          item: result,
          isArray: (obj) => Array.isArray(obj),
        });
        item.querySelector("#list_body").replaceWith(list_items);
        target.parentElement
          .querySelector(".records-count-bits")
          .setAttribute("data-count", result.curr_list);
        target.parentElement.querySelector(".records-count-bits").innerHTML =
          result.list_numbers;

        if (result.is_next) {
          if (!target.parentElement.querySelector(".btn-next.pager")) {
            target.parentElement
              .querySelector(".btn-next")
              .classList.add("pager");
          }
        } else {
          if (!result.is_next) {
            target.parentElement
              .querySelector(".btn-next")
              .classList.remove("pager");
          }
        }

        if (result.is_previous) {
          if (!target.parentElement.querySelector(".btn-previous.pager")) {
            target.parentElement
              .querySelector(".btn-previous")
              .classList.add("pager");
          }
        } else {
          if (!result.is_previous) {
            target.parentElement
              .querySelector(".btn-previous")
              .classList.remove("pager");
          }
        }
      });
  }
  onClickSort(e) {
    var current = e.target;
    var index = Array.from(current.parentNode.children).indexOf(current);
    var rows = [];
    var thClass = current.classList.contains("asc") ? "desc" : "asc";
    Array.from(current.parentNode.children).forEach(function (th) {
      th.classList.remove("asc", "desc");
    });
    current.classList.add(thClass);

    Array.from(current.closest("table").querySelectorAll("tbody tr")).forEach(function (row) {
      rows.push(row.parentNode.removeChild(row));
    });

    rows.sort(function (a, b) {
      var aValue = a.querySelector("td:nth-child(" + (index + 1) + ")").textContent;
      var bValue = b.querySelector("td:nth-child(" + (index + 1) + ")").textContent;
      if (Number(aValue) && Number(bValue))
        return Number(aValue) > Number(bValue)
          ? 1
          : Number(aValue) < Number(bValue)
          ? -1
          : 0;
      return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
    });

    if (current.classList.contains("desc")) {
      rows.reverse();
    }
    rows.forEach(function (row) {
      current.closest("table").querySelector("tbody").appendChild(row);
    });
  }
  // ----------------------------------------------------------------
  //           OVER LIST VIEW EVENTS
  // ----------------------------------------------------------------
  async onClickDatesApply(ev) { 
    if (this.state.from_date && this.state.to_date) {
      var d_start_date = this.state.from_date.toISODate();
      var d_end_date = this.state.to_date.toISODate();

      await this.orm.call("dashboard.bits", "write", [
        [this.state.dashboard_id],
        {
          default_start_date: d_start_date,
          default_end_date: d_end_date,
        },
      ]);
    }
    if (this.state.from_date && this.state.to_date) {
      this.loadDashboardData().then(() => {
        this.on_attach_callback();
      });
    }
  }
  AddItemButton(ev) {
    this.action.doAction({
      name: _t("Dashboard Item"),
      type: "ir.actions.act_window",
      res_model: "dashboard.item.bits",
      view_mode: "form",
      views: [[false, "form"]],
      context: {
        bits_dashboard_id: this.state.dashboard_id || false,
      },
    });
  }
  // HEADER EVENTS:
  async onSelectTimeframe(ev) {
    var $target = ev.currentTarget;
    var Tframe = $target.dataset?.dateFormat || "default";
    this.state.time_frame = Tframe;
    // check date range filter selection
    var $range_ele = $target
      .closest(".time_range_filter")
      .querySelector(".date_picker_container");
    if (Tframe == "custom") {
      if ($range_ele.classList.contains("d-hidden")) {
        $range_ele.classList.toggle("d-hidden");
      }
    } else {
      $range_ele.classList.add("d-hidden");
    }
    // hide date filters selection
    $target.parentNode.classList.toggle("show");
    // fetch new dahsboard data
    if (this.state.time_frame != "custom") {
      this.loadDashboardData().then(() => {
        this.on_attach_callback();
      });
    }
  }
  async onSelectColorTheme(ev) {
    ev.preventDefault();
    var $target = ev.currentTarget;
    var colorTheme = $target.dataset?.colorTheme;
    this.state.color_theme = parseInt(colorTheme);
    // $target.parents(".color_theme_bits").find("#color_theme_selection_bits").html($target.text());
    $target.parentNode.classList.toggle("show");
    this.loadDashboardData().then(() => {
      this.on_attach_callback();
    });
  }
  async onSelectViewMode(ev) {
    var $target = ev.target;
    var viewMode = $target.dataset.viewMode;
    this.state.view_mode = viewMode;
    // $target.parentNode.parentNode.querySelector(".view_mode_switch").querySelector("#view_mode_selection_bits").innerHTML = $target.textContent;
    document
      .querySelector(".grid-items-container-bits .grid-stack")
      .classList.add("grid-stack");
    await this.on_attach_callback();
  }
  saveViewMode(ev) {
    var $target = ev.target;
    var mode = $target.dataset.currMode;
    if (mode) {
      this.orm.call("dashboard.bits", "write", [
        [this.state.dashboard_id],
        { default_view_mode: mode },
      ]);
    }
  }
  onDefaultTimeFrame(ev) {
    var $target = ev.target;
    var tframe = $target.dataset.currMode;
    if (tframe) {
      this.orm.call("dashboard.bits", "write", [
        this.state.dashboard_id,
        {
          default_time_frame: tframe,
          default_start_date: this.state.from_date.toISODate(),
          default_end_date: this.state.to_date.toISODate(),
        },
      ]);
    }
  }
  async onDefaultColorTheme(ev) {
    var $target = ev.target;
    var ctheme = $target.dataset.currMode;
    if (ctheme) {
      await this.orm.call("dashboard.bits", "write", [
        this.state.dashboard_id,
        { default_color_theme: parseInt(ctheme) },
      ]);
    }
    this.loadDashboardData().then(() => {
      this.on_attach_callback();
    });
  }
  // custome filter evnets
  onInputFocusOut(ev) {
    ev.target.value = "";
    ev.target.parentNode.querySelector(".c_filters_container_bits").classList.remove("show");
  }
  async onClickCustomfilter(ev) {
    ev.preventDefault();
    this.toggleDropdownClass(ev);
    var self = this;
    var $target_data = ev.target.dataset;
    this.state.is_filter = false;
    if ($target_data.ttype == "relational") {
      if (
        !Object.keys(self.state.filter_data).includes(
          String($target_data.filter_id)
        )
      ) {
        this.orm
          .call($target_data.target_model, "fields_get")
          .then(function (fields) {
            var fields = [];
            if (Object.keys(fields).includes("name")) {
              fields = ["name"];
            } else {
              fields = ["display_name"];
            }
            var kwargs = { fields: fields };
            self.orm
              .call($target_data.target_model, "search_read", [], { ...kwargs })
              .then(function (result) {
                self.state.filter_data[parseInt($target_data.filter_id)] =
                  result;
              });
          });
      }
    } else {
      if (
        !Object.keys(self.state.filter_data).includes(
          String($target_data.filter_id)
        )
      ) {
        this.orm
          .call($target_data.target_model, "fields_get")
          .then(function (result) {
            var selections = result[$target_data.field].selection;
            self.state.filter_data[parseInt($target_data.filter_id)] =
              selections;
          });
      }
    }
    this.state.is_filter = true;
  }
  onClickCustomfilterInput(ev) {
    var self = this;
    var targetData = ev.target.dataset;
    var target = ev.target;
    var inputStr = target.value;
    if (targetData.ttype != "selection") {
      this.state.is_filter = false;
      var filteredData = self.state.filter_data[targetData.filter_id];
      if (inputStr.trim().length < 0) {
        filteredData = self.state.filter_data[targetData.filter_id].slice(0, 10);
      } else {
        filteredData = filteredData.filter(function(obj) {
          return obj.name
            ? obj.name.toLowerCase().includes(inputStr)
            : obj.display_name.toLowerCase().includes(inputStr);
        });
      }
      this.state.is_filter = true;
    } else {
      target.value = "";
    }
  }
  async onClickFilterValue(ev) {
    var self = this;
    var $target = ev.target;
    var $targetInput = $target.closest(".filter-bits").querySelector("input");
    var ttype = $target.dataset.ttype;
    var filterId = parseInt($targetInput.dataset?.filter_id) || 0;
    var t_model_id = $targetInput.dataset.target_model;
    var rec_id = parseInt($target.dataset.rid) || 0;
    var filter = this.state.dashboard_data.filters.filter((f) => {
      return f.target_field_model == t_model_id;
    });
    if (!filter.length) {
      return;
    } else {
      filter = filter[0];
    }
    // changed fid to model
    if (
      ttype == "relational" &&
      this.state.applied_filters.length &&
      this.state.applied_filters.filter((el) => {
        return el.model_id == t_model_id;
      }).length
    ) {
      this.state.applied_filters.forEach(async function (element) {
        var curr_elem = element;
        if (curr_elem.model_id == t_model_id) {
          if (!curr_elem.apply_filter_rec_ids.includes(rec_id)) {
            curr_elem.apply_filter_rec_ids.push(rec_id);
            curr_elem.field_names.push($target.dataset.value);
            curr_elem.filter_name =
              filter.target_field_name +
              " in " +
              curr_elem.field_names.join(",");
          }
        }
        self.state.applied_filters[
          self.state.applied_filters.indexOf(element)
        ] = curr_elem;
      });
    } else {
      if (ttype == "relational") {
        this.state.applied_filters.push({
          uid: Date.now(),
          fid: filterId,
          filter_name:
            filter.target_field_name + " in " + $target.dataset.value,
          model_id: filter.target_field_model,
          filter_domain:
            "[('" + filter.target_field_tname + "','in',[" + rec_id + "])]",
          apply_filter_field: filter.target_field_tname,
          apply_filter_rec_ids: [rec_id],
          field_names: [$target.dataset.value],
          filter_field_type: "relational",
        });
      } else {
        var field_value = $target.dataset.sid;
        if (
          this.state.applied_filters.length &&
          this.state.applied_filters.filter((el) => {
            return el.model_id == filterId;
          }).length
        ) {
          this.state.applied_filters.forEach(async function (element) {
            var curr_elem = element;
            if (curr_elem.model_id == filterId) {
              self.state.applied_filters[
                self.state.applied_filters.indexOf(element)
              ] = {
                uid: Date.now(),
                fid: filterId,
                model_id: filter.target_field_model,
                filter_name:
                  filter.target_field_name + " = " + $target.dataset.value,
                filter_domain:
                  "[('" +
                  filter.target_field_tname +
                  "','=','" +
                  field_value +
                  "')]",
                filter_field_type: "selection",
              };
            }
          });
        } else {
          this.state.applied_filters.push({
            uid: Date.now(),
            fid: filterId,
            model_id: filter.target_field_model,
            filter_name:
              filter.target_field_name + " = " + $target.dataset.value,
            filter_domain:
              "[('" +
              filter.target_field_tname +
              "','=','" +
              field_value +
              "')]",
            filter_field_type: "selection",
          });
        }
      }
    }
    this.state.applied_filters = this.state.applied_filters.filter(
      (obj, index, self) =>
        index === self.findIndex((o) => o["filter_name"] === obj["filter_name"])
    );
    this.loadDashboardData().then(() => {
      this.on_attach_callback();
    });
  }
  async onClickFacetRemove(ev) {
    var self = this;
    var $target = ev.target;
    this.state.applied_filters = this.state.applied_filters.filter((flt) => {
      return flt.uid != parseInt($target.dataset.uid);
    });
    self.loadDashboardData().then(() => {
      self.on_attach_callback();
    });
  }
  async onClickFavoriteFilterSave(ev) {
    var self = this;
    var user_id = session.uid;
    if (!this.state.applied_filters.length) {
      this.notification.add("Opps! No any filters applied.", {
        type: "info",
      });
      return false;
    }
    var $parent = ev.target.closest(".dropdown-item");
    var fname = $parent.querySelector(".input-filter-bits").value;
    var use_default = $parent.querySelector(".user-default-bits").checked;
    // made empty when default use set true

    // ---------------
    var dashboard_id = this.state.dashboard_id;
    await this.orm
      .call("favorite.filter.bits", "create_fav_filter", [
        [],
        {
          name: fname,
          dashboard_id: dashboard_id,
          is_active: use_default,
          filter_value: this.state.applied_filters,
        },
      ])
      .then(async function (result) {
        if (use_default) {
          self.state.applied_filters = [];
        }
        self.loadFavFilters().then(() => {
          self.loadDashboardData().then(() => {
            self.on_attach_callback();
          });
        });
      });
  }
  async onClickFavoriteApply(ev) {
    ev.preventDefault();
    var self = this;
    this.state.applied_filters = [];
    var filterId = parseInt(ev.target.dataset.filter_id);
    await this.orm
      .call("favorite.filter.bits", "write", [[filterId], { is_active: 1 }])
      .then(async function (result) {
        self.loadFavFilters().then(() => {
          self.loadDashboardData().then(() => {
            self.on_attach_callback();
          });
        });
      });
  }
  async onClickFavoriteRemove(ev) {
    ev.stopPropagation();
    this.state.applied_filters = [];
    var self = this;
    var filterId = parseInt(ev.target.dataset.fvid);
    await this.orm.call("favorite.filter.bits", "unlink", [[filterId]]);
    await self.loadFavFilters();
    this.loadDashboardData().then(() => {
      this.on_attach_callback();
    });
  }
  onClickToggleSidebar() {
    document.querySelector(".mob_filter_bits").classList.toggle("d-hidden");
  }
  // ----------------------------------------------------------------
  // Item events
  onClickEditItem(ev) {
    var rec_id = ev.target.dataset.stackId; 
    this.action.doAction({
      title: "",
      name: _t("Dashboard Item"),
      type: "ir.actions.act_window",
      views: [[false, "form"]],
      res_model: "dashboard.item.bits",
      res_id: parseInt(rec_id),
      flags: {
        mode: "edit",
      },
      target: "current",
      context: {
        create: false,
      },
    });
  }
  async onClickExportItem(e) {
    var rec_id = e.target.closest(".grid-stack-item").dataset.stackId;

    const res = await rpc("/export/dashboard/item", {
      item_id: rec_id,
    });
    this.action.doAction(res);
  }
  onClickDupicateItem(e) {
    var self = this;
    var rec_id = parseInt(e.target.dataset.stackId);
    this.dialogService.add(DuplicateConfirmation, {
      title: _t("Copy/Duplicate Item"), 
      dashboards: this.state.dashboard_data.dashboards,
      record_id: rec_id,
      confirm: async (res) => {
        if (res && res.action == "copy") {
          self.doCopyrecord(res.dashboard_id, res.record_id);
        }
        if (res && res.action == "move") {
          self.doMoverecord(res.dashboard_id, res.record_id);
        }
      },
    });
  }
  async doCopyrecord(selected_dashboard, item_id) {
    await this.orm.call(
      "dashboard.item.bits",
      "copy_dashboard_item_bits",
      [item_id],
      { context: { selected_dashboard_id: parseInt(selected_dashboard) } }
    );
  }
  async doMoverecord(selected_dashboard, item_id) {
    var self = this;
    await this.orm
      .call("dashboard.item.bits", "move_dashboard_item_bits", [item_id], {
        context: {
          selected_dashboard_id: parseInt(selected_dashboard),
        },
      })
      .then(async function () {
        self.loadDashboardData().then(() => {
          self.on_attach_callback();
        });
      });
  }
  async onClickDeleteItem(e) {
    var self = this;
    var rec_id = parseInt(e.target.dataset.stackId);
    this.dialogService.add(ConfirmationDialog, {
      body: _t("Are you sure that you want to delete this item ?"),
      confirm: () => {
        self.doDeleteItem(rec_id);
      },
      cancel: () => {},
    });
  }
  async doDeleteItem(rec_id) {
    var self = this;
    // removed direct unlink method bcase of delete
    await this.orm
      .call("dashboard.item.bits", "unlink_item_bits", [[rec_id]])
      .then(async function () {
        self.loadDashboardData().then(() => {
          self.on_attach_callback();
        });
      });
  }
  onClickStatistics(e) {
    var item_id = e.target.closest(".statistics-bits").dataset.stackId;
    var action_data = this.state?.dashboard_data?.dashboard_items[item_id]?.statistics_data.action;
    if (action_data && action_data.id) {
      this.action.doAction({
      name: _t(action_data.name),
      type: "ir.actions.act_window",
      res_model: action_data.res_model,
      views: [
        [false, "list"],
        [false, "form"],
      ],
      target: "current",
      });
    }
  }
  onClickToggleDropdown(e) {}
  // ----------------------------------------------------------------
  //           Media Option Events
  // ----------------------------------------------------------------
  // onSlideshowDashboard:function(e) {
  // },
  onCaptureDashboard(e) {
    e.stopPropagation();
    var $dashboard = document.querySelector(".grid-items-container-bits");
    html2canvas($dashboard, { useCORS: true, allowTaint: false }).then(
      function (canvas) {
        window.jsPDF = window.jspdf.jsPDF;
        var document = new jsPDF("p", "mm", "a4");
        var img = canvas.toDataURL("image/jpeg", 0.9);
        var Props = document.getImageProperties(img);
        var w = document.internal.pageSize.getWidth();
        var h = (Props.height * w) / Props.width;
        var pageHeight = 295;
        var heightLeft = h;
        var position = 0;

        document.addImage(img, "JPEG", 0, 0, w, h, "FAST");
        heightLeft -= pageHeight;
        while (heightLeft >= 0) {
          position = heightLeft - h;
          document.addPage();
          document.addImage(img, "JPEG", 0, position, w, h, "FAST");
          heightLeft -= pageHeight;
        }
        document.save("test.pdf");
      }
    );
  }
  // copy_text: function(){
  // },
  onGenerateShareLink(e) {
    var self = this;
    var $content = "";
    var base_url = window.location.origin;
    this.orm
      .call("dashboard.bits", "get_sharable_link", [this.state.dashboard_id])
      .then(function (result) {
        var link = base_url + result;
         
        self.dialogService.add(CopyEmbadeCodeDialog, { 
          title: _t("Copy Dashboard Sharable Link"),
          embade_code: link,
          close: () => {}, 
          confirm: async (res) => {
            if (navigator.clipboard) {
              await navigator.clipboard.writeText(res.ecode);
              self.notification.add("Copied Successfully", {
                title: "Copy Embed Link",
                type: "info",
                sticky: false,
              });
            } else {
              self.notification.add(
                "Opps! Enable to copy the text. It seems you are using insecure contexts. Use HTTPS instead of HTTP OR copy text manually",
                {
                  title: "Copy Embed Link",
                  type: "info",
                  sticky: false,
                }
              );
            }
          }, 
        });
      });
  }
  onEmbadeDashboard(e) {
    var self = this;
    var $content = "";
    var base_url = window.location.origin;
    this.orm
      .call("dashboard.bits", "get_sharable_link", [this.state.dashboard_id])
      .then(function (result) {
        var link = base_url + result; 
        var linkElement = '<iframe src="' + link + '" width="100%" height="100%"></iframe>';
        self.dialogService.add(CopyEmbadeCodeDialog, {
          title: _t("Copy the embed dashboard code"),
          embade_code: linkElement,
          close: () => {}, 
          confirm: async (res) => {
            if (navigator.clipboard) {
              await navigator.clipboard.writeText(res.ecode);
              self.notification.add("Copied Successfully", {
                title: "Copy Embed Link",
                type: "info",
                sticky: false,
              });
            } else {
              self.notification.add(
                "Opps! Enable to copy the text. It seems you are using insecure contexts. Use HTTPS instead of HTTP OR copy text manually",
                {
                  title: "Copy Embed Link",
                  type: "info",
                  sticky: false,
                }
              );
            }
          }, 
        });
      });
  }
  // ----------------------------------------------------------------
  // Dashboard setting events
  onClickEditDasboard(ev) {
    this.action.doAction({
      name: _t("Edit Dashboard"),
      context: { create: false },
      type: "ir.actions.act_window",
      res_model: "dashboard.bits",
      res_id: this.state.dashboard_id,
      flags: { mode: "edit" },
      views: [[false, "form"]],
      target: "new",
    });
  }
  onClickAddDasboardFilter(ev) {
    this.action.doAction({
      name: _t("New Filter"),
      context: { create: false },
      type: "ir.actions.act_window",
      res_model: "dashboard.filter.bits",
      flags: { mode: "edit" },
      views: [[false, "form"]],
      target: "new",
      // context: {
      //   dashboard_id: this.state.dashboard_id || false,
      // },
    });
  }
  onClickAddDasboardTheme(ev) {
    this.action.doAction({
      name: _t("New Theme"),
      context: { create: false },
      type: "ir.actions.act_window",
      res_model: "dashboard.themes",
      flags: { mode: "edit" },
      views: [[false, "form"]],
      target: "new",
      // context: {
      //   dashboard_id: this.state.dashboard_id || false,
      // },
    });
  }
  async onClickDupDasboard() {
    const res = await this.orm.call(
      "dashboard.bits",
      "duplicate_dashboard",
      [this.state.dashboard_id],
      { context: this.prepareContex() }
    );
    if (res) {
      this.action.doAction(res);
    }
  }
  async onClickImpDasboard(e) {
    this.action.doAction({
      type: "ir.actions.act_window",
      res_model: "import.dashboard",
      view_mode: "form",
      views: [[false, "form"]],
      target: "new",
    });
  }
  async onClickExpDasboard(e) {
    const res = await rpc("/export/dashboard", {
      dashboard_id: this.state.dashboard_id,
    });
    this.action.doAction(res);
  }
  async onClickImpItemDasboard(e) {
    this.action.doAction({
      type: "ir.actions.act_window",
      res_model: "import.dashboard.item",
      view_mode: "form",
      context: { dashboard_id: this.state.dashboard_id },
      views: [[false, "form"]],
      target: "new",
    });
  }
  onClickRemoveDasboard() {
    var self = this; 
    this.dialogService.add(ConfirmationDialog, {
      body: _t("Are you sure that you want to delete this dashboard ?"),
      title: _t("Delete Dashboard"),
      confirm: () => {
        self.orm.call("dashboard.bits", "unlink", [self.state.dashboard_id])
          .then((res) => {
            self.action.doAction(
              "analytix_dashboard_bits.action_dashboards_view_bits"
            );
          });
      },
      cancel: () => {},
    });
  }

  onStartDatechanged(ev) {
    this.state.from_date = ev;
  }

  onEndDatechanged(ev) {
    this.state.to_date = ev;
  }
}

DashboardControllerBits.template = "DashboardControllerBits";
DashboardControllerBits.components = {
  View,
  Dropdown,
  DropdownItem,
  DateTimeInput,
};
registry
  .category("actions")
  .add("bits_dashboard_action", DashboardControllerBits);
