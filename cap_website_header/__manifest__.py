{
    'name': "Captivea Website Header",
    # 3.3: the "Transform your solutions" panel got one pane per shortcut,
    # switched on hover and on click. Existing panels keep their single pane
    # until "Reset the mega menu panels" is clicked.
    # 3.4: the language selector prints the language name on its entries, so the
    # seven published languages stop all reading `EN` or `FR`. The button keeps
    # the compact code of the mock-up.
    # 3.4.1: the row 1 dropdown entry of the page being read was turned white by
    # `website.scss`, on a white dropdown.
    'version': '19.0.3.4.3',
    'category': 'Website/Website',
    'summary': "Three-row Captivea website header (top bar, logo/search/CTA, mega menu bar)",
    'description': """
Captivea Website Header
=======================

Replaces the standard Odoo header by the Captivea header, made of three rows:

1. a light grey top bar (right aligned, hidden below ``lg``) with the secondary
   menus and the language selector;
2. the main row: logo, centered search bar and the "Contact us" call to action;
3. a mega menu bar (hidden below ``lg``) whose panels use the native
   ``website.menu.mega_menu_content`` field, so they stay editable in the builder.

The header is a regular ``website.layout`` header template: it is enabled per
website (Website ‣ Configuration ‣ Settings, or the builder's Header ‣ Template
option), through Odoo's copy-on-write mechanism on ``ir.ui.view``.
""",
    'author': "Captivea",
    'website': "https://www.captivea.com",
    'license': 'LGPL-3',
    'depends': [
        'website',
    ],
    'data': [
        'views/cap_mega_menu_templates.xml',
        'views/cap_header_templates.xml',
        'views/website_menu_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cap_website_header/static/src/scss/cap_header.scss',
            'cap_website_header/static/src/scss/cap_mega_menu.scss',
            'cap_website_header/static/src/js/cap_header_dropdown.js',
            'cap_website_header/static/src/js/cap_mega_solutions.js',
            'cap_website_header/static/src/js/cap_search_bar.js',
            'cap_website_header/static/src/js/cap_search_modal.js',
            # Suggestion panel of the "All" search bars; picked up by
            # `search_bar.js` through its `.<searchType>` naming convention.
            'cap_website_header/static/src/xml/cap_search_autocomplete.xml',
        ],
        # Bundle that actually carries `website.HeaderTemplateOption` (the parent
        # of our extension); `html_builder.assets` alone does not.
        'website.website_builder_assets': [
            'cap_website_header/static/src/builder/cap_header_template_option.xml',
            'cap_website_header/static/src/builder/cap_mega_menu_option.xml',
        ],
    },
    'installable': True,
    'application': False,
}