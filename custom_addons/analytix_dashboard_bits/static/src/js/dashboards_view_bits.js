/** @odoo-module **/

import {
  Component,
  onWillStart,
  onMounted,
  useState,
  useRef,
  onWillUnmount,
} from "@odoo/owl"; 
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog"; 

class DashboardViewControllerBits extends Component {
  setup() {
    super.setup(); 
    this.orm = useService("orm");
    this.state = useState({});
    this.action = useService("action");
    this.notification = useService("notification");
    this.state.dashboard_data = [];
    this.state.orderFormat = "Default";
    this.el = useRef("el");
    
    onWillStart(async () => {
      this.state.dashboard_data = [];
      this.state.orderFormat = "Default";
      this.state.hasAccess = false;
    });  
    onMounted(async () => {
      await this._fetch_dashboards("");
      document.addEventListener("click", this.onDocumentClick.bind(this));
    }); 
    onWillUnmount(async () => {
      document.removeEventListener("click", this.onDocumentClick.bind(this));
    });
  }

  async onSelectOrder(ev) {
    ev.stopPropagation();  
    ev.target.parentNode.classList.toggle("show");
    this.orderFormat = ev.target?.dataset?.orderFormat?ev.target?.dataset?.orderFormat:"Default";
    await this._fetch_dashboards("");
  }

  toggleDropdownClass(ev) {
    const parent = ev.target.parentNode;
    ev.stopPropagation(); 
    parent.querySelector(".dropdown-menu")?.classList.toggle("show");
  }

  closeDropdownMenus() {
    const dropdownMenus = document.querySelectorAll(".dropdown-menu");
    dropdownMenus.forEach((menu) => {
      menu.classList.remove("show");
    });
  }

  onDocumentClick(ev) {
    this.closeDropdownMenus();
  } 

  sortDashboardData() {
    this.state.dashboard_data = [...this.state.dashboard_data].sort((a, b) => {
      // Convert names to lowercase for case-insensitive sorting
      const nameA = a.name.toLowerCase();
      const nameB = b.name.toLowerCase();

      // Compare the names
      if (nameA < nameB) {
        return this.orderFormat == "ASC" ? -1 : 1;
      }
      if (nameA > nameB) {
        return this.orderFormat == "ASC" ? 1 : -1;
      }
      // Names are equal
      return 0;
    });
  }

  onClickImpDasboard(e) {
    this.action.doAction({
      // name: _t(name),
      type: "ir.actions.act_window",
      res_model: "import.dashboard",
      // res_id: parseInt(rid),
      view_mode: "form",
      views: [[false, "form"]],
      target: "new",
    });
  }
  _AddNewDashboard(ev) {
    ev.preventDefault();
    this.action.doAction({
      type: "ir.actions.act_window",
      name: _t("New Dashboard"),
      res_model: "dashboard.bits",
      views: [[false, "form"]],
    });
  }
  // mt-dn-18
  async _OpenDashboard(ev) { 
    var action_data = ev.currentTarget.dataset; 
    var coverDiv = this.createCoverElement(); 
    
    document.body.appendChild(coverDiv);
    if(action_data.caid){
      await this.action.doAction({
        type: "ir.actions.client",
        id: parseInt(action_data.caid),
        tag: "bits_dashboard_action",
        context: {
          params: {
            dashboard_id: action_data.did,
            default_color_theme: action_data.color_theme || false,
            default_time_frame: action_data.tframe,
            default_view_mode: action_data.view_mode,
          },
        },
      });
    }else{
      return false
    }
    document.body.querySelector('#cover').remove();
  }
  createCoverElement(){
    const coverDiv = document.createElement("div");
    coverDiv.id = "cover";
    coverDiv.style.position = "fixed";
    coverDiv.style.minWidth = "100vw";
    coverDiv.style.minHeight = "100vh";
    coverDiv.style.opacity = "0.5";
    coverDiv.style.color = "white";
    coverDiv.style.top = "0";
    coverDiv.style.left = "0";
    return coverDiv;
  }
  async _fetch_dashboards(src) {
    const dashboard_data = await this.orm.call(
      "dashboard.bits",
      "get_dashboards",
      [[], src]
    ); 
    this.state.dashboard_data = dashboard_data?.dashboards
      ? dashboard_data?.dashboards
      : [];
    this.state.hasAccess = Boolean(dashboard_data?.has_group_admin_bits);
    this.search = dashboard_data.search;
    if (this.orderFormat != "Default") {
      this.sortDashboardData();
    }
  }
  onClickEditDashboard(e) {
    debugger
    var $target = e.target.parentNode.parentNode;
    e.stopPropagation();
    e.preventDefault();
    this.action.doAction({
      name: _t("Dashboard"),
      type: "ir.actions.act_window",
      views: [[false, "form"]],
      res_model: "dashboard.bits",
      res_id: parseInt($target.dataset.did),
      flags: { mode: "edit" },
      context: { create: false },
    });
  }
  onClickDeleteDashboard(e) {
    var self = this;
    var $target = e.target.parentNode.parentNode;
    e.stopPropagation(); 
    this.dialogService.add(ConfirmationDialog, {
      body: _t("Are you sure that you want to delete this dashboard ?"),
      title: _t("Delete Dashboard"),
      confirm: () => {
        self.orm.call("dashboard.bits", "unlink", [parseInt($target.dataset.did)])
          .then((res) => { self.action.doAction("analytix_dashboard_bits.action_dashboards_view_bits"); });
      },
      cancel: () => {},
    });
  }
  async deleteDashboard(rec_id) {
    var self = this;
    // removed direct unlink method bcase of delete
    await this.orm
      .call("dashboard.bits", "unlink_dashboard_bits", [[rec_id]])
      .then(async function () {
        await self._fetch_dashboards("");
      });
  }
  async onSearchInput(e) {
    var target = $(e.currentTarget);
    e.preventDefault();
    if (target.val().trim() == "") {
      await this._fetch_dashboards("");
    } else {
      await this._fetch_dashboards(target.val());
    }
  }
} 

DashboardViewControllerBits.template = "DashboardViewControllerBits";
registry
  .category("actions")
  .add("bits_all_dashboard_action", DashboardViewControllerBits);