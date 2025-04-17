/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { loadJS } from "@web/core/assets";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { 
    Component, 
    markup, 
    onMounted, 
    onWillUnmount, 
    onWillUpdateProps,
    onWillStart, 
    useEffect,
    useRef, 
    useState, 
} from "@odoo/owl";

function formatLang(lang) {
    if (lang === 'zh_CN') {
        return 'zh-cn';
    }else {
        return lang.split('_')[0];
    }
}

export class CkEditorField extends Component {

    static template = "widget_ckeditor.CkEditorField";

    static props = {
        ...standardFieldProps,
    };

    get propsValue() {
        return this.props.record.data[this.props.name];
    }

    setup() {
        this.textareaRef = useRef("textarea");
        this.state = useState({
            value: this.propsValue.toString(),
        });

        onWillStart(async () => {
            await this.loadEditorLanguage();
        });

        onMounted(async () => {
            const editor = await this.loadCKEditor();
            this.editor = editor;
        });

        onWillUpdateProps((nextProps) => {
            if (this.editor) {
                this.state.value = nextProps.record.data[nextProps.name].toString();
                this.editor.setData(this.state.value);
            }
        });

        onWillUnmount(() => {
            this.editor.destroy();
            this.editor = null;
        });

        useEffect(() => {
            const value = this.propsValue.toString();
            if (!this.props.record.dirty && value !== this.state.value) {
                this.state.value = value;
                this.editor.setData(value);
            }
        });

    };

    async loadEditorLanguage() {
        const lang = formatLang(session.user_context.lang);
        if (lang === 'en') return;
        try {
            await loadJS(`/widget_ckeditor/static/lib/ckeditor/builds/translations/${lang}.js`);
        }
        catch (error) {
            console.warn("Unable to load CKEditor language: ", lang);
        }
    };

    async loadCKEditor() {
        const editor = await ClassicEditor
            .create(this.textareaRef.el, {
                initialData: this.state.value,
                language: formatLang(session.user_context.lang),
            })
            .catch(error => {
                console.error(error);
            });
        if (this.props.readonly) {
            editor.isReadOnly = true;
        }else {
            editor.model.document.on('change:data', () => {
                if (editor.getData() !== this.state.value) {
                    this._onChange();
                }
            });
        };
        return editor;
    };

    _onChange() {
        this.state.value = this.editor.getData();
        if (markup(this.state.value) !== this.props.value) {
            this.props.record.update({ [this.props.name]: markup(this.state.value) });
        }
    };

}

export const ckeditorField = {
    component: CkEditorField,
    supportedFieldTypes: ["text", "html"],
};

registry.category("fields").add("ckeditor", ckeditorField);