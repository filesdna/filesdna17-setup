odoo.define('elastic_search.TagInput', function (require) {
    "use strict";

    const FormView = require('web.FormView');
    const FieldChar = require('web.relational_fields').FieldChar;

    const TagInput = FieldChar.extend({
        template: 'TagInputTemplate',
        
        events: {
            'keypress input': 'onKeyPress',
            'click .remove-tag': 'removeTag',
        },

        init: function (parent, name, record, options) {
            this._super(parent, name, record, options);
            this.tags = [];
        },

        onKeyPress: function (event) {
            const input = event.target;
            if (event.key === 'Enter' && input.value) {
                this.addTag(input.value);
                input.value = ''; // Clear input field
                event.preventDefault();
            }
        },

        addTag: function (value) {
            if (!this.tags.includes(value)) {
                this.tags.push(value);
                this.renderTags();
            }
        },

        removeTag: function (event) {
            const tag = $(event.currentTarget).data('tag');
            this.tags = this.tags.filter(t => t !== tag);
            this.renderTags();
        },

        renderTags: function () {
            const tagsContainer = this.$('.tags-container');
            tagsContainer.empty();
            this.tags.forEach(tag => {
                tagsContainer.append(`<span class="tag">${tag}<span class="remove-tag" data-tag="${tag}">✖</span></span>`);
            });
        },

        // Override the getValue method to return the tags
        getValue: function () {
            return this.tags.join(', ');
        },

        // Add your template here
    });

    FormView.include({
        render_view: function (viewType, arch, options) {
            this._super(viewType, arch, options);
            this.$('.o_field_widget.o_field_char').each(function () {
                const field = new TagInput(this);
                field.appendTo(this);
            });
        },
    });
});
