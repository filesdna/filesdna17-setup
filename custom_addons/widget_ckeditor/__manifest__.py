{
    "name": "Widget CKEditor",
    "version": "1.0",
    "summary": "CKEditor widget for fields type of text",
    'license': 'LGPL-3',
    "application": True,
    "depends": ["web"],
    "author": "oyx1231",
    "website": "https://github.com/oyx1231/widget_ckeditor",
    "images": ["static/description/screenshot.png"],
    "assets": {
        "web.assets_backend": [
            "widget_ckeditor/static/lib/ckeditor/builds/ckeditor.js",
            "widget_ckeditor/static/src/widgets/ckeditor_widget.scss",
            "widget_ckeditor/static/src/widgets/ckeditor_widget.xml",
            "widget_ckeditor/static/src/widgets/ckeditor_widget.js",
        ],
    },
}