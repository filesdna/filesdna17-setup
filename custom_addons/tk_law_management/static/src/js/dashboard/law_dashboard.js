/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { session } from "@web/session";
import { Domain } from "@web/core/domain";
import { sprintf } from "@web/core/utils/strings";

const { Component, useSubEnv, useState, onMounted, onWillStart, useRef } = owl;
import { loadJS, loadCSS } from "@web/core/assets"

class LawDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            caseMaterStats: { 'case_matter': 0, 'open_case_matter': 0, 'pending_case_matter': 0, 'close_case_matter': 0 },
            lawStatic: { 'law_practise_area': 0, 'matter_category': 0, 'law_court': 0, 'case_lawyer': 0 },
            caseMatterStatus: { 'x-axis': [], 'y-axis': [] },
            overAllInfo: { 'x-axis': [], 'y-axis': [] },
        });

        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
        });

        this.caseMatterStatus = useRef('case_matter_status');
        this.overAllInfo = useRef('overall_info');

        onWillStart(async () => {
            let caseMaterData = await this.orm.call('law.dashboard', 'get_law_dashboard', []);
            if (caseMaterData) {
                this.state.caseMaterStats = caseMaterData;
                this.state.lawStatic = caseMaterData;
                this.state.caseMatterStatus = { 'x-axis': caseMaterData['case_matter_status'][0], 'y-axis': caseMaterData['case_matter_status'][1] }
                this.state.overAllInfo = { 'x-axis': caseMaterData['over_all_info'][0], 'y-axis': caseMaterData['over_all_info'][1] }
            }
        });
        onMounted(() => {
            this.renderCaseMatterStatusGraph();
            this.renderOverAllInfoGraph();
        })
    }

    viewCaseMaterDetails(status) {
        let domain, context;
        let matters = this.getCaseMaters(status);
        if (status === 'all') {
            domain = []
        } else {
            domain = [['state', '=', status]]
        }
        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: matters,
            res_model: 'case.matter',
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'calendar'], [false, 'search'], [false, 'activity']],
            target: 'current',
            context: context,
            domain: domain,
        });
    }

    getCaseMaters(status) {
        let matters;
        if (status === 'all') {
            matters = 'Cases'
        } else if (status === 'open') {
            matters = 'Open Cases'
        } else if (status === 'pending') {
            matters = 'Pending Cases'
        } else if (status === 'close') {
            matters = 'Close Cases'
        }
        return matters;
    }

    viewLawPractiseArea() {
        let context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Practise Area',
            res_model: 'law.practise.area',
            views: [[false, 'list']],
            target: 'current',
            context: context,
        });
    }

    viewMatterCategory() {
        let context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Case Category',
            res_model: 'matter.category',
            views: [[false, 'list']],
            target: 'current',
            context: context,
        });
    }

    viewLawCourt() {
        let context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Courts',
            res_model: 'law.court',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
        });
    }

    viewCaseLawyers() {
        let domain = [['is_lawyer', '=', true]];
        let context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Lawyers',
            res_model: 'res.partner',
            domain: domain,
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
        });
    }

    renderGraph(el, options) {
        const graphData = new ApexCharts(el, options);
        graphData.render();
    }

    renderCaseMatterStatusGraph() {
        const options = {
            series: this.state.caseMatterStatus['y-axis'],
            chart: {
                height: 430,
                type: 'polarArea',
            },
            labels: this.state.caseMatterStatus['x-axis'],
            stroke: {
                colors: ['#fff']
            },
            fill: {
                opacity: 0.8
            },
            yaxis: {
                labels: {
                    formatter: function (val) {
                        if (typeof val === 'number') {
                            return val.toFixed(0);
                        } else {
                            return val;
                        }
                    }
                },
            },
            legend: {
                position: 'bottom'
            },
            responsive: [{
                breakpoint: 480,
                options: {
                    chart: {
                        width: 200
                    },
                    legend: {
                        position: 'bottom'
                    }
                }
            }]
        };
        this.renderGraph(this.caseMatterStatus.el, options);
    }

    renderOverAllInfoGraph() {
        const options = {
            series: [
                {
                    name: 'Status',
                    data: this.state.overAllInfo['y-axis'],
                }
            ],
            chart: {
                height: 430,
                type: 'bar',
            },
            plotOptions: {
                bar: {
                    columnWidth: '20%',
                    distributed: true,
                }
            },
            dataLabels: {
                enabled: false
            },
            legend: {
                show: false
            },
            xaxis: {
                categories: this.state.overAllInfo['x-axis'],
                labels: {
                    style: {
                        fontSize: '12px'
                    }
                }
            }
        };
        this.renderGraph(this.overAllInfo.el, options);
    }
}
LawDashboard.template = "tk_law_management.law_management_dashboard";
registry.category("actions").add("law_dashboard", LawDashboard);