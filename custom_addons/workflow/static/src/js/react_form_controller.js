/** @odoo-module **/

import { registry } from '@web/core/registry';
import { patch } from '@web/core/utils/patch';
import { FormController } from '@web/views/form/form_controller';

patch(FormController.prototype, 'smartform.FormController', {
    setup() {
        this._super.apply(this, arguments);
        this.onModelLoaded = this.onModelLoaded.bind(this);
        this.model.load().then(this.onModelLoaded);
    },
    onModelLoaded() {
        const dataPath = this.props.context.default_data_path;
        if (dataPath) {
            const rootElement = document.getElementById('root');
            if (rootElement) {
                rootElement.setAttribute('data-path', dataPath);
            }
        }
    },
});
