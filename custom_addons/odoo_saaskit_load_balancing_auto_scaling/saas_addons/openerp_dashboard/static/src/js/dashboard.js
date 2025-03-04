/** @odoo-module **/
//odoo.define('openerp_dashboard.meeting_chart', function(require) {
//    'use strict';

  import { Component } from "@odoo/owl";
//  var AbstractAction = require('web.AbstractAction');
//  var core = require('web.core');
    import { session } from "@web/session";
//  var session = require('web.session');
//  var rpc = require('web.rpc');
//  import { rpc } from '@web/core/rpc/rpc';
//  var Widget = require('web.Widget');
//  import { Widget } from '@web/core/widget/widget';
//  var Dialog = require('web.Dialog');
    import { registry } from "@web/core/registry";
    import { Dialog } from '@web/core/dialog/dialog';

//  var _t = core._t;
    import { _t } from "@web/core/l10n/translation";
    class XeroDashboardViewNew extends Component{

//    template : 'XeroDashboardViewNew',
//    // events: {
//    // "click #pending_order": "on_pending_order",
//    //  },
//    init: function(parent, action) {
//     console.log("11111111111s333",this)
//        this.googlePieChart1();
//    // }
//     return this._super.apply(this, arguments);
//     },
//
    static template = "XeroDashboardViewNew"
    setup(parent, options) {
    super.setup(parent, options)
    console.log('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
        this.googlePieChart1();
//       return super.setup(parent, action);
     }


    // });
    googlePieChart1(){
        console.log("db_infoooooooo")
        let db_info,total_db_size;
        let filestore_info,total_filestore_size;
        db_info = this.getDbInfo('database');
        filestore_info = this.getDbInfo('filestore');
        console.log("db_infoooooooo",db_info)
//            console.log(db_info);
//            console.log(filestore_info);
        total_db_size = parseFloat(db_info[1][1])+parseFloat(db_info[2][1]);
        total_filestore_size = parseFloat(filestore_info[1][1])+parseFloat(filestore_info[2][1]);


        setTimeout(function(){
                google.charts.load("visualization", "1", {'packages':['corechart']});
                google.charts.setOnLoadCallback(drawChart1);
                google.charts.setOnLoadCallback(drawChart2);

                function drawChart1() {
                    console.log(db_info);
                    var data = google.visualization.arrayToDataTable(db_info);
                    let i = 90;
                    var options = {
                        title: 'Database Total Size '+total_db_size.toFixed(2)+" GB",
                        titleTextStyle: {
                                            fontSize: 15, // 12, 18 whatever you want (don't specify px)
                                            bold: true,    // true or false
                                        },
                        width: 640,
                        height: 350,
                        pieSliceText: 'none',
                        legend: { position: 'labeled',
                                  labeledValueText: 'both',
                                  alignment:'center',
                                  textStyle: {
                                      color: 'black',
                                      fontSize: 12 }, strokeColor: {color: 'black'},
                         },
                        tooltip: { trigger: 'none' },
//                        is3D: true,
                    };
                    var chart = new google.visualization.PieChart(document.getElementById('piechart1'));
                    chart.draw(data, options);

                };
                function drawChart2() {
                    console.log(filestore_info);
                    var data = google.visualization.arrayToDataTable(filestore_info);
                    var options = {
                        title: 'Filestore Total Size '+total_filestore_size.toFixed(2)+" GB",
                        titleTextStyle: {
                                            fontSize: 15, // 12, 18 whatever you want (don't specify px)
                                            bold: true,    // true or false
                                        },
                        width: 640,
                        height: 350,
                        pieSliceText: 'none',
                        legend: { position: 'labeled',
                                  labeledValueText: 'both',
                                  alignment:'center',
                                  textStyle: {
                                      color: 'black',
                                      fontSize: 12 }, strokeColor: {color: 'black'},
                        },
                        tooltip: { trigger: 'none' },
//                         is3D: true,
                    };
                    var chart = new google.visualization.PieChart(document.getElementById('piechart2'));
                    chart.draw(data, options);

                };
                }, 1000);

    }

    getDbInfo (type){
        var model = 'saas.service';
        var dict = {};
        var ret = [];
        $.ajax({
            url : '/db/space_info/',
            async : false,
            data : {    model: model, type:type },
            success : function(data) {
                var data1 = JSON.parse(data);

//                    if( parseFloat(data1.dbInfo.default_db_size) < parseFloat(data1.dbInfo.used_db_size)){
//                         framework.blockUI();
//                    }
//                    if( parseFloat(data1.dbInfo.default_filestore_size) < parseFloat(data1.dbInfo.used_filestore_size)){
//                         framework.blockUI();
//                    }
                let db_consumed_size = 0;
                let filestore_consumed = 0;
                if(data1.dbInfo.default_db_size){
                    db_consumed_size = parseFloat(data1.dbInfo.default_db_size) - parseFloat(data1.dbInfo.used_db_size);
                }

                if(data1.dbInfo.default_filestore_size){
                    filestore_consumed = parseFloat(data1.dbInfo.default_filestore_size)-parseFloat(data1.dbInfo.used_filestore_size);
                }
                console.log(db_consumed_size+"---"+filestore_consumed);
                ret.push(['Type', 'volume']);
                if(db_consumed_size <= 0 || filestore_consumed <= 0){
                        var div = document.createElement("div");
                        div.classList.add('popup_div');
                        var newContent = document.createElement("div");
                        newContent.style.marginTop= 250+"px";
                        newContent.style.padding = 35+"px";
                        newContent.style.background = "none no-repeat scroll 0 0 #fff";
                        newContent.classList.add('container');
                        newContent.style.height =150+"px";
                        newContent.style.width =500+"px";
                        newContent.style.borderColor= "red green blue pink";
                        var text1 = document.createElement("h5");

                        if ((type=='database')&&(db_consumed_size <= 0)){

                            var text_content1 = document.createTextNode("Your database size limit is exceeded from allocated size ...!");
                            db_consumed_size = 0;

                        }else if((type=='filestore')&&(filestore_consumed <= 0)){

                            var text_content1 = document.createTextNode('Your filestore size limit is exceeded from allocated size ...!');
                            filestore_consumed=0;

                        }

                        if(text_content1){
                            text1.appendChild(text_content1);
                            newContent.appendChild(text1);
                            var text2 = document.createElement("h6");
                            var text_content2 = document.createTextNode("Please purchase more space");
                            text2.appendChild(text_content2);
                            newContent.appendChild(text2);
                            var space = document.createElement("br");
                            newContent.appendChild(space);
                            div.appendChild(newContent);

                            var sub_button = document.createElement("button");
                            sub_button.classList.add('submit_button');
                            var sub_button_text = document.createTextNode("OK");
                            sub_button.appendChild(sub_button_text);
                            sub_button.style.width =76+"px";
                            sub_button.style.float ="right";
                            sub_button.style.backgroundColor ="#4CAF50";
                            sub_button.style.borderRadius= 2+"px";
                            sub_button.style.marginRight= 10+"px";
                            sub_button.style.height =31+"px";
                            newContent.appendChild(sub_button);
                            div.style.width =100+"%";
                            div.style.backgroundColor = "rgb(0,0,0,0.4)";
                            div.style.height =100+"%";
                            div.style.position ="absolute";
                            div.style.display ="block";
                        }
                         if((data1.dbInfo.default_db_size)||(data1.dbInfo.default_filestore_size)){
                            document.body.appendChild(div);
                         }
                }


                    if (type == 'filestore'){
                        ret.push(['Unused Filestore Size '+filestore_consumed.toFixed(2)+" GB", filestore_consumed]);
                        ret.push(["Used Filestore Size "+data1.dbInfo.used_filestore_size.toFixed(2)+" GB", data1.dbInfo.used_filestore_size]);
                    }else{
                        ret.push(["Unused Database Size "+db_consumed_size.toFixed(2)+" GB", db_consumed_size]);
                        ret.push(["Used Database Size "+data1.dbInfo.used_db_size.toFixed(2)+" GB", data1.dbInfo.used_db_size ]);
                    }
                    if (data1.exist == true){
                        alert("Instance name is not available")
                        ret = false
                    }

            }
        });
        $('.submit_button').on('click',function(){
            if (user > 5){
                framework.blockUI();
            }
            else{
                $(".popup_div").hide()
            }
        })

        return ret;
    }
}
    registry.category("actions").add('test_dashboard_sand', XeroDashboardViewNew);
//    core.action_registry.add('test_dashboard_sand', XeroDashboardViewNew);
//    return {
//     XeroDashboardViewNew : XeroDashboardViewNew,
//    };
//    });

