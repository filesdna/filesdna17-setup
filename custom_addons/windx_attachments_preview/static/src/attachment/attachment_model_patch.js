/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get isDoc() {
        return this.extension === "doc" && this.mimetype.includes("officedocument");
    },
    get isDocx() {
        return this.extension === "docx" && this.mimetype.includes("officedocument");
    },
    get isPPT() {
        return this.extension === "ppt" && this.mimetype.includes("officedocument");
    },
    get isPPTX() {
        return this.extension === "pptx" && this.mimetype.includes("officedocument");
    },
    get isXLS() {
        return this.extension === "xls" && this.mimetype.includes("ms-excel");
    },
    get isXLSX() {
        return this.extension === "xlsx" && this.mimetype.includes("officedocument");
    },

    get isOfficeFile() {
        return ((this.isDocx || this.isPPTX || this.isXLSX) && !this.uploading);
    },

    get isViewable() {
        return this.isOfficeFile || super.isViewable;
    },

});
