/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { X2ManyFieldDialog } from "@web/views/fields/relational_utils";
import { useService } from "@web/core/utils/hooks";

patch(X2ManyFieldDialog.prototype,{
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.notification = useService("notification");
    },
    async load_faceid_models(){
        var self = this;
        const promises = [];

        var params = await this.rpc('/faceid_authentication/_get_human_config_params');        
        this.configParams = params;
        
        this.humanConfig = {
            backend: this.configParams.human_backend || 'webgl', //webgl, humangl, wasm
            async: true,
            warmup: 'none', //none, face
            cacheSensitivity: 0,
            debug: false,
            deallocate: true,
            face: {
                enabled: true,
                detector: {
                    return: true,
                    rotation: false,
                    maxDetected: 1,
                    iouThreshold: 0.01,
                    minConfidence: 0.6,
                    modelPath: '/faceid_authentication/static/src/lib/models/blazeface.json',
                },
                mesh: { 
                    enabled: true,
                    modelPath: '/faceid_authentication/static/src/lib/models/facemesh.json',
                },
                iris: { 
                    enabled: false,
                    modelPath: '/faceid_authentication/static/src/lib/models/iris.json',
                },
                emotion: { 
                    enabled: false,
                    modelPath: '/faceid_authentication/static/src/lib/models/emotion.json',
                },
                description: { 
                    enabled: true,
                    modelPath: '/faceid_authentication/static/src/lib/models/faceres.json',
                },
            },
            body: { enabled: false },
            hand: { enabled: false },
            object: { enabled: false },
            gesture: { enabled: false },
        };
        this.human = new Human.Human(this.humanConfig);
        this.human.env['perfadd'] = false; // is performance data showing instant or total values
        this.human.validate(this.humanConfig);            
        await this.human.load();
        if (true) {
            const warmup = new ImageData(50, 50);
            await this.human.detect(warmup);
        }
        promises.push([this.human, this.configParams]);
        return Promise.all(promises).then(() => {
            return Promise.resolve();
        });
    },

    async save({ saveAndNew }) {
        if(this.record.resModel === 'res.users.faces'){
            var self = this;
            var image = this.record.data.image || false;            
            if (image){
                var image = $('#face_image div img')[0];        
                self.getUsersDescriptor(image);
            }
        }else{
            return super.save({ saveAndNew });
        }
    },

    async getUsersDescriptor(image){
        var self = this;
        if (image.src.indexOf("placeholder.png") > -1) {
            self.notification.add(this.env._t("Photo unavailable."),{ 
                type: "danger" 
            });
            return;
        }

        await self.load_faceid_models().then(async function(){
            console.log(self.human);
            if (("Human" in window)) {
                var img = document.createElement('img');
                img.src= image.src;

                await self.human.detect(img, self.humanConfig).then((res) => {
                    for (const i in res.face) {
                        // did not get valid results
                        if (!res.face[i].tensor) {
                            self.notification.add(this.env._t("Did not get valid results from uploaded photo."), {
                                type: "danger",
                            });
                            return;
                        }
                        // face analysis score too low
                        if ((res.face[i].faceScore || 0) < self.human.config.face.detector.minConfidence) {
                            self.notification.add(this.env._t("Face analysis score too low."), {
                                type: "danger",
                            });
                            return;
                        }
                        self.human.tf.dispose(res.tensor);
                        var embedding = res.face[i].embedding;
                        if (embedding) {  
                            var descriptor = self.arrayBufferToBase64Users(embedding);
                            self.updateUsersDescriptor(descriptor).then(function(){
                                window.location.reload();
                            });
                        }else{
                            self.notification.add(this.env._t("Did not get valid results from uploaded photo."), {
                                type: "danger",
                            });
                            return;
                        }                        
                    }
                });
            }else{
                return setTimeout(() => self.getUsersDescriptor(image))
            }
        })
    },
    async updateUsersDescriptor(descriptor){
        var self = this;
        this.record.update({
            'descriptor': descriptor,
            'has_descriptor' : true,
        });
        if (await this.record.checkValidity()) {
            const saved = (await this.props.save(this.record, {})) || this.record;
        } else {
            return false;
        }
        this.props.close && this.props.close();
        return true;
    },
    arrayBufferToBase64Users(embedding) {
        var binary = '';
        var embedding = new Float32Array(embedding);
        var bytes = new Uint8Array(embedding.buffer);
        var len = bytes.byteLength;
        for (var i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    },
});
