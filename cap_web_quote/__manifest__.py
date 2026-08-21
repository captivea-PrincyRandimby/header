# -*- coding: utf-8 -*-
{
    'name': 'Website Quotes / Testimonials',
    'summary': 'Manage testimonial quotes (Website > Content) and a dynamic '
               'testimonials snippet filterable by tag.',
    'category': 'Website',
    'version': '19.0.1.2.0',
    'author': 'Captivea',
    'license': 'LGPL-3',
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'views/quote_views.xml',
        'data/quote_snippet_filter.xml',
        'views/quote_snippet_templates.xml',
        'views/quote_client_quote.xml',
    ],
    'demo': [
        'demo/quote_testimonial_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cap_web_quote/static/src/snippets/testimonials/testimonials.js',
            'cap_web_quote/static/src/snippets/client_quote/client_quote.js',
            'cap_web_quote/static/src/scss/testimonials.scss',
        ],
        'website.website_builder_assets': [
            'cap_web_quote/static/src/website_builder/**/*',
        ],
    },
    'installable': True,
}
