/** @odoo-module **/
const { DateTime } = luxon;
import { serializeDate } from "@web/core/l10n/dates";

import {
    registry
} from "@web/core/registry";
import {
    useService
} from "@web/core/utils/hooks";
import {
    Component,
    EventBus,
    onWillStart,
    useSubEnv,
    useState,
    onMounted,
    onPatched
} from "@odoo/owl";
import {
    renderToElement
} from "@web/core/utils/render";

export class FileStatComponent extends Component {
    init() {
        this._super.apply(this, arguments);
        this.rpc = this.bindService("rpc");
    }
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.variants = [];
        this.warehouses = [];
        this.showVariants = false;
        this.uomName = "";
        this.extraColumnCount = 0;
        this.unfoldedIds = new Set();
        //        this.rpc = this.bindService("rpc");
        this.state = useState({
            showOptions: {
                uom: false,
                availabilities: false || Boolean(this.props.action.context.activate_availabilities),
                costs: true,
                operations: true,
                leadTimes: true,
                attachments: false,
            },
            currentWarehouse: null,
            currentVariantId: null,
            bomData: {},
            precision: 2,
            bomQuantity: null,
        });

        useSubEnv({
            overviewBus: new EventBus(),
        });

        onWillStart(async () => {
            //            await this.getWarehouses();
            //            await this.initBomData();
            var self = this;
            await self.render_dashboards();
            await self.render_graphs();
            await self.render_graphsmonthly_car();
        });
        onMounted(() => {
            // do something
            var self = this;
            self.datadisplay();
            self.render_graphs();
            self.render_graphsmonthly_car();
            self.get_order();
            self.get_customer_count();
            self.get_sale_order_cancel();
        });
        onPatched(() => {
            // do something
            var self = this;
            self.render_dashboards();
        });
    }
    action_done() {
        this.actionService.doAction({
            name: "Cars Done",
            type: 'ir.actions.act_window',
            res_model: 'car.repair.form',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['state', '=', 'done']
            ],
            target: 'current'
        }, )
    }
    action_in_progress() {
        this.actionService.doAction({
            name: "Cars In-Progress",
            type: 'ir.actions.act_window',
            res_model: 'car.repair.form',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['state', '=', 'progress']
            ],
            target: 'current'
        }, )
    }
    action_in_diagnosis() {
        this.actionService.doAction({
            name: "Cars In Diagnosis",
            type: 'ir.actions.act_window',
            res_model: 'car.repair.form',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['state', '=', 'diagnosis']
            ],
            target: 'current'
        }, )
    }
    action_received() {
        this.actionService.doAction({
            name: "Cars Received",
            type: 'ir.actions.act_window',
            res_model: 'car.repair.form',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            domain: [
                ['state', '=', 'received']
            ],
            target: 'current'
        }, )
    }
    job_card() {
        this.actionService.doAction({
            name: "Job Roles",
            type: 'ir.actions.act_window',
            res_model: 'job.roles',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            target: 'current'
        }, )
    }
    card_contan() {
        this.actionService.doAction({
            name: "Car Parts",
            type: 'ir.actions.act_window',
            res_model: 'car.parts',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            target: 'current'
        }, )
    }
    card_maintence() {
        this.actionService.doAction({
            name: "Service Repair CheckList",
            type: 'ir.actions.act_window',
            res_model: 'maintenance.checklist',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            target: 'current'
        });
    }
    getRandomColor() {
        var letters = '0123456789ABCDEF'.split('');
        var color = '#';
        for (var i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }
    async get_order()
    {
        var self = this;
        var result = await this.orm.call("sale.order", "get_sale_table", [])

                if(result){

                    var res = result.order
                    var dataSet = []
                    for(var i=0;i<res.length;i++){
                        dataSet.push([res[i].order_reference, res[i].partner_name,res[i].date_order,res[i].delievery_date,'<span class="label label-success">' + '</span>'])
                    }
                    if(dataSet.length > 0){
                        $('.sale').DataTable( {
                            lengthChange : false,
                            info: false,
                            "destroy": true,
                            "responsive": false,
                            pagingType: 'simple',
                            "pageLength": 4,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                { title: "Order Reference" },
                                { title: "Customer Name" },
                                { title: "Creation Order" },
                                { title: "Delivery Date" }
                            ]
                        });
                    }
                }

    }
    action_today_appointment()
    {
        this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'dms.file',
            view_mode: 'kanban',
            view_type: 'list',
            views: [[false, 'list'],[false, 'form']],
            // context: {
            //             'search_default_':true,
            //         },
            // domain: [['start_at','=',serializeDate(luxon.DateTime.now().plus({ days: 0 }))]],
            target: 'current'
        });
    }
    action_rejected_appointment()
    {
        this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'calendar'],[false, 'form']],
            context: {
                        'search_default_rejected_appointment':true,
                    },
            domain: [['attendee_ids.state','in',['declined']]],
            target: 'current'
        });
    }
    action_approved_appointment()
    {
        this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'calendar'],[false, 'form']],
            context: {
                        'search_default_approved_appointment':true,
                    },
            domain: [['attendee_ids.state','in',['accepted']]],
            target: 'current'
        });
    }
    action_pending_appointment()
    {
         this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'calendar'],[false, 'form']],
            context: {
                        'search_default_pending_appointment':true,
                    },
            domain: [['attendee_ids.state','in',['needsAction']]],
            target: 'current'
        });
    }
    action_view_calendar_event_calendar()
    {
        this.actionService.doAction({
            name: "Meetings",
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'list'],[false, 'calendar'],[false, 'form']],
            target: 'current'
        });
    }
        action_appointment_group() {
        this.actionService.doAction({
            name: "Appointment Group",
            type: 'ir.actions.act_window',
            res_model: 'appointment.group',
            view_mode: 'tree,form',
            view_type: 'list',
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            target: 'current'
        });
    }
    async get_customer_count()
    {
         var self = this;
        var result = await this.orm.call("sale.order", "get_sale_table", [])

                if(result){
                    var res = result.count_customer
                    var dataSet = []
                    for(var i=0;i<res.length;i++){
                        dataSet.push([res[i].customer_name,'<span class="label label-success">' + '</span>'])
                    }
                    if(dataSet.length > 0){
                        $('.customer').DataTable( {
                            lengthChange : false,
                            info: false,
                            "destroy": true,
                            "responsive": false,
                            pagingType: 'simple',
                            "pageLength": 10,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                { title: "Customer Name" },

                            ]
                        });
                    }
                }
//            });
    }
     async get_sale_order_cancel()
    {
         var self = this;
        var result = await this.orm.call("sale.order", "get_sale_table", [])

                if(result){
                    var res = result.sale_cancel
                    var dataSet = []
                    for(var i=0;i<res.length;i++){
                        dataSet.push([res[i].customer_name,'<span class="label label-success">' + '</span>'])
                    }
                    if(dataSet.length > 0){
                        $('.sale-cancel').DataTable( {
                            lengthChange : false,
                            info: false,
                            "destroy": true,
                            "responsive": false,
                            pagingType: 'simple',
                            "pageLength": 10,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                { title: "Customer Name" },

                            ]
                        });
                    }
                }
//            });
    }
    async datadisplay() {
        var result = await this.orm.call("appointment.group", "get_count_list", [])
        $('.total-service').text(result.total_service)
        $('.total-appointment').text(result.total_appointment)
        $('.pending-appointment').text(result.pending_appointment)
        $('.rejected-appointment').text(result.rejected_appointment)
        $('.today-appointment').text(result.today_appointment)
        $('.table').text(result.sale_tables)
    }
    async render_dashboards() {
//        var self = this;
//        var result = await this.orm.call("car.repair.form", "get_car_repair_count_list", [])
//        var car_repair_dashboard = renderToElement('CarDashboardView', {});
//        return car_repair_dashboard
     var self = this;
     var result = await this.orm.call("appointment.group", "get_count_list", [])
        var appointment_dashboard = renderToElement('AppointmentDashboardView', {});


        return appointment_dashboard

    }
    async render_graphsmonthly_car() {
        var self = this;
        var ctx = $('#monthlyappointment')
        Chart.plugins.register({
            beforeDraw: function(chartInstance) {
                var ctx = chartInstance.chart.ctx;
                ctx.fillStyle = "white";
                ctx.fillRect(0, 0, chartInstance.chart.width, chartInstance.chart.height);
            }
        });
        var bg_color_list = []
        for (var i = 0; i <= 12; i++) {
            bg_color_list.push(self.getRandomColor())
        }
        //        rpc.query({
        //                model: 'car.repair.form',
        //                method: 'get_car_repair_statistics_data',
        //            })
        var result = await this.orm.call("calendar.event", "get_monthly_appointments", [])
        if (result) {
            var data = result.data
            var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                'August', 'September', 'October', 'November', 'December'
            ]
            var month_data = [];

            if (data) {
                for (var i = 0; i < months.length; i++) {
                    months[i] == data[months[i]]
                    var day_data = months[i];
                    var month_count = data[months[i]];
                    if (!month_count) {
                        month_count = 0;
                    }
                    month_data[i] = month_count

                }
            }
            var myChart = new Chart(ctx, {
                type: 'bar',
                data: {

                    labels: months,
                    datasets: [{
                        label: 'Appointees',
                        data: month_data,
                        backgroundColor: bg_color_list,
                        borderColor: bg_color_list,
                        borderWidth: 1,
                        pointBorderColor: 'white',
                        pointBackgroundColor: 'red',
                        pointRadius: 1,
                        pointHoverRadius: 10,
                        pointHitRadius: 30,
                        pointBorderWidth: 1,
                        pointStyle: 'rectRounded'
                    }]
                },
                options: {
                    scales: {
                        yAxes: [{
                            ticks: {
                                min: 0,
                                max: Math.max.apply(null, month_data),
                            }
                        }]
                    },
                    responsive: true,
                    maintainAspectRatio: true,
                    leged: {
                        display: true,
                        labels: {
                            fontColor: 'black'
                        }
                    },
                },
            });

        };

    }
    async render_graphs() {
        var self = this;
        var ctx = $('#highprice')
        Chart.plugins.register({
            beforeDraw: function(chartInstance) {
                var ctx = chartInstance.chart.ctx;
                ctx.fillStyle = "white";
                ctx.fillRect(0, 0, chartInstance.chart.width, chartInstance.chart.height);
            }
        });
        var bg_color_list = []
        for (var i = 0; i <= 12; i++) {
            bg_color_list.push(self.getRandomColor())
        }
        var result = await this.orm.call("calendar.event", "get_value_price", [])
        if (result) {
            var data = result.data;
            var day = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"
            ]
            var week_data = [];
            if (data) {
                for (var i = 0; i < day.length; i++) {
                    day[i] == data[day[i]]
                    var day_data = day[i];
                    var day_count = data[day[i]];
                    if (!day_count) {
                        day_count = 0;
                    }
                    week_data[i] = day_count

                }
            }

            var myChart = new Chart(ctx, {
                type: 'bar',
                data: {

                    labels: day,
                    datasets: [{
                        label: 'Appointees',
                        data: week_data,
                        backgroundColor: bg_color_list,
                        borderColor: bg_color_list,
                        borderWidth: 1,
                        pointBorderColor: 'white',
                        pointBackgroundColor: 'red',
                        pointRadius: 5,
                        pointHoverRadius: 10,
                        pointHitRadius: 30,
                        pointBorderWidth: 2,
                        pointStyle: 'rectRounded'
                    }]
                },
                options: {
                    scales: {
                        yAxes: [{
                            ticks: {
                                min: 0,
                                max: Math.max.apply(null, week_data),
                            }
                        }]
                    },
                    responsive: true,
                    maintainAspectRatio: true,
                    leged: {
                        display: true,
                        labels: {
                            fontColor: 'black'
                        }
                    },
                },
            });
        };
    }

}

CarRepairComponent.template = "AppointmentDashboardView";

registry.category("actions").add("appointment_dashboard", CarRepairComponent);