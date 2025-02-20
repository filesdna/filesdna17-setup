/* @odoo-module */

import { FileViewer } from "@web/core/file_viewer/file_viewer";
import { useRef, useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(FileViewer.prototype, {
    setup() {
        super.setup();
        this.viewerMsOfficeRef = useRef("ViewerMsOffice");
        // Preview Office file: docx, pptx, xlsx
        useEffect(() => {
            if (this.viewerMsOfficeRef.el) {
                this.previewMsOffice(this.viewerMsOfficeRef.el);
            }
        });
        this.instancePreviewOffice = null;
    },

    async getFileFromUrl(url, name, defaultType = 'image/jpeg'){
        const blob = await (await fetch(url)).blob();
        return new File([blob], name, { type: blob.type || defaultType });
    },

    async previewMsOffice(rootElement) {
        var self = this;

        if (!this.state.file.isOfficeFile || !$.isFunction(window.createDocxJS)
            || !$.isFunction(window.createCellJS) || !$.isFunction(window.createSlideJS)) {
            this.close();
            return;
        }

        if (this.state.file.isDocx) {
            this.instancePreviewOffice = window.docxJS = window.createDocxJS();
        } else if (this.state.file.isXLSX) {
            this.instancePreviewOffice = window.cellJS = window.createCellJS();
        } else if (this.state.file.isPPTX) {
            this.instancePreviewOffice = window.slideJS = window.createSlideJS();
        }

        if (this.instancePreviewOffice) {
            var file = await this.getFileFromUrl(this.state.file.defaultSource, this.state.file.name);
            this.instancePreviewOffice.parse(
                file,
                function () {
                    self.afterRender(file, rootElement);
                }, function (e) {
                    if(e.isError && e.msg){
                        alert(e.msg);
                    }
                    self.instancePreviewOffice.destroy(function(){
                        self.instancePreviewOffice = null;
                    });
                }, null
            );
        }
    },

    afterRender(file, element) {
        if (!$('#' + element.getAttribute('id')).length) {
            return;
        }
        $(element).css('height','calc(100% - 55px)');

        var endCallBackFn = function(result){
            if (result.isError) {
                // console.log("Error Render");
            } else {
                // console.log("Success Render");
            }
        };

        if (this.state.file.isDocx) {
            window.docxAfterRender(element, endCallBackFn);
        } else if (this.state.file.isXLSX) {
            window.cellAfterRender(element, endCallBackFn);
        } else if (this.state.file.isPPTX) {
            window.slideAfterRender(element, endCallBackFn, 0);
        }
    },

});
