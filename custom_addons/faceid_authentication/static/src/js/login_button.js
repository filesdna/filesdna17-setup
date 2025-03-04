/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { Deferred } from "@web/core/utils/concurrency";
import { FaceIdRecognitionDialog } from "./faceid_recognition_dialog";
import { loadCSS, loadJS } from "@web/core/assets";

publicWidget.registry.faceidLoginButton = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click button.faceid_login_button': '_onClickFaceID',
    },
    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.dialog = this.bindService("dialog");
        this.notificationService = this.bindService("notification");

        this.labeledFaceDescriptors = [];
        this.load_label = new Deferred();
    },
    willStart: async function () {
        var _loadJS = loadJS('/faceid_authentication/static/src/lib/source/human.js');
        var _loadCss = loadCSS('/faceid_authentication/static/src/css/style.css')
        return Promise.all([this._super.apply(this, arguments), _loadJS, _loadCss]);
    },
    load_models: async function () {
        let modelsDef = new Deferred();
        var params = await this.rpc('/faceid_authentication/_get_human_config_params');        
        this.configParams = params;
        this.humanConfig = {
            debug: false,
            backend: this.configParams.human_backend || 'webgl', //webgl, humangl, wasm
            async: true,
            warmup: 'none',
            cacheSensitivity: 0,
            deallocate: true,
            modelBasePath: '/faceid_authentication/static/src/lib/models/',
            filter: {
                enabled: true,
                equalization: true,
            },
            face: {
                enabled: true, 
                detector: { 
                    rotation: false,
                    minConfidence: 0.6,
                    maxDetected: 1,
                    mask: false,
                    skipInitial: true,
                }, 
                mesh: { 
                    enabled: true 
                }, 
                attention: { 
                    enabled: false 
                }, 
                iris: { 
                    enabled: true 
                }, 
                description: { 
                    enabled: true 
                }, 
                emotion: { 
                    enabled: true 
                }, 
                antispoof: { 
                    enabled: true 
                }, 
                liveness: { 
                    enabled: true 
                } 
            },
            body: { 
                enabled: false 
            },
            hand: { 
                enabled: false 
            },
            object: { 
                enabled: false 
            },
            segmentation: { 
                enabled: false 
            },
            gesture: { 
                enabled: true 
            },
        };
        this.human = new Human.Human(this.humanConfig);
        this.human.env['perfadd'] = false; // is performance data showing instant or total values
        this.human.draw.options.font = 'small-caps 18px "Lato"'; // set font used to draw labels when using draw methods
        this.human.draw.options.lineHeight = 20;
        this.human.validate(this.humanConfig);
        await this.human.load();
        if (true) {
            const warmup = new ImageData(50, 50);
            await this.human.detect(warmup);
        }
        modelsDef.resolve();
        return modelsDef;
    },
    base64ToArrayBuffer: function (base64) {
        var binary_string = window.atob(base64);
        var len = binary_string.length;
        var bytes = new Uint8Array(len);
        for (var i = 0; i < len; i++) {
            bytes[i] = binary_string.charCodeAt(i);
        }
        return new Float32Array(bytes.buffer);
    },
    start: function () { 
        var self = this;
        self.$('.o_database_list .card-body').addClass('d-none');
        self.$('.o_database_list').addClass('faceid_loading');
        self.promise_load_models = self.load_models();
        return $.when(this._super.apply(this, arguments)).then(async function () {                
            await self.loadLabeledImages();
        });
    },
    loadLabeledImages: function () {
        var self = this;
        return this.rpc('/faceid_authentication/loadLabeledImages/').then(async function (data) {
            data.map((data, i) => {
                for (var i = 0; i < data.descriptors.length; i++) {                        
                    if (data.descriptors[i].descriptor_id && data.descriptors[i].descriptor) {
                        var buffer = self.base64ToArrayBuffer(data.descriptors[i].descriptor);
                        self.labeledFaceDescriptors.push({
                            'name': data.name,
                            'label': data.label,
                            'descriptor_id':data.descriptors[i].descriptor_id,
                            'descriptor': Array.from(buffer),
                            'login': data.login,
                        });
                    }
                }
            });
            self.$('.o_database_list .card-body').removeClass('d-none');
            self.$('.o_database_list').removeClass('faceid_loading');
            self.load_label.resolve();
        });
    },
    async _onClickFaceID(ev) {
        ev.preventDefault();
        var self = this;
        if (self.labeledFaceDescriptors && self.labeledFaceDescriptors.length != 0) {
            await self.dialog.add(FaceIdRecognitionDialog, {
                human: self.human,
                configParams: self.configParams,
                labeledFaceDescriptors : self.labeledFaceDescriptors,
            }); 
        }else{
            self.notificationService.add(_t("Detection Failed: Resource not found, Please add it to your user profile."), {
                type: "danger",
            });
        }
    }

});
