# -*- coding: utf-8 -*-
{
    'name': 'Lucide Icons',
    'summary': 'Lucide icon picker in the website editor, backed by an extensible '
               'database catalog (add more selectable icons on demand).',
    'category': 'Website',
    'version': '19.0.1.0.0',
    'author': 'Captivea',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'data/lucide_icons.xml',
        'wizard/lucide_icon_import_views.xml',
        'views/lucide_icon_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cap_web_lucide_icons/static/src/scss/lucide_frontend.scss',
        ],
        'website.website_builder_assets': [
            'cap_web_lucide_icons/static/src/js/**/*',
            'cap_web_lucide_icons/static/src/xml/**/*',
            'cap_web_lucide_icons/static/src/scss/lucide_picker.scss',
        ],
    },
    'installable': True,
}
