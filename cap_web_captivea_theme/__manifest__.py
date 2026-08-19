# -*- coding: utf-8 -*-
{
    'name': 'Captivea Theme',
    'description': 'Captivea brand theme for Odoo 19 Website — brand color palette, '
                   'fonts (Nunito) and CSS presets, plus the Captivea website snippets '
                   '(customer references, blog tag filter).',
    'category': 'Theme/Corporate',
    'summary': 'Odoo integration, ERP, Web, Business Intelligence, AI — Captivea brand',
    'sequence': 110,
    'version': '19.0.1.0.0',
    'author': 'Captivea',
    'license': 'LGPL-3',
    'application': True,
    'depends': [
        'website',
        'website_blog',        # blog snippet tag filter + card customizations
        'website_customer',    # customer references (pulls website_crm_partner_assign, website_partner, website_google_map)
        'cap_web_lucide_icons',  # Lucide icon picker
        'cap_web_logo_lang',     # logo per language
        'cap_web_quote',         # testimonials + dynamic snippet
        'cap_web_seo_json_ld',   # per-page JSON-LD SEO field
    ],
    'data': [
        'data/generate_primary_template.xml',
        'data/ir_asset.xml',
        'data/website_data.xml',
        'views/images.xml',
        'views/customizations.xml',
        'views/website_templates.xml',
        'views/snippets.xml',
        'data/pages.xml',
        'data/menu.xml',
        'views/new_page_template.xml',
        # merged from the former cap_website_snippets module
        'data/customer_references_filter.xml',
        'views/customer_references_templates.xml',
        'data/blog_posts_filter.xml',
        'views/blog_posts_templates.xml',
    ],
    # NOTE: frontend + website_builder assets are declared via data/ir_asset.xml
    # (ir.asset records), NOT here — on this theme module the manifest 'assets'
    # block was not being bundled. See data/ir_asset.xml for details.
    'configurator_snippets': {
        'homepage': [
            's_banner', 's_image_text', 's_text_image',
            's_three_columns', 's_references', 's_call_to_action',
        ],
    },
}
