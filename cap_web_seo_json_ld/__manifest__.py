# -*- coding: utf-8 -*-
{
    'name': 'Website SEO JSON-LD',
    'summary': 'Per-page JSON-LD (schema.org) code field in the Optimize SEO dialog, '
               'injected into the page <head> when set.',
    'category': 'Website',
    'version': '19.0.1.0.0',
    'author': 'Captivea',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'views/website_settings_views.xml',
        'views/seo_json_ld_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cap_web_seo_json_ld/static/src/seo_dialog/seo_json_ld.js',
            'cap_web_seo_json_ld/static/src/seo_dialog/seo_json_ld.xml',
        ],
    },
    'installable': True,
}
