# -*- coding: utf-8 -*-
{
    'name': 'Website Logo per Language',
    'summary': 'Assign a different website logo for each language (SVG supported).',
    'description': """
Website Logo per Language
=========================
Adds a per-language logo table to the Website settings (Settings > Websites).
Each row maps one of the website's active languages to a logo (SVG/PNG/JPG).
The header displays the logo matching the visitor's current language, falling
back to the standard website logo when no language-specific logo is set.

Theme-agnostic: depends only on `website` and works with any theme.
""",
    'category': 'Website',
    'version': '19.0.1.0.0',
    'author': 'Captivea',
    'website': 'https://www.captivea.com',
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'views/cap_web_logo_lang_views.xml',
        'views/logo_templates.xml',
    ],
    'post_init_hook': 'post_init_hook',
}
