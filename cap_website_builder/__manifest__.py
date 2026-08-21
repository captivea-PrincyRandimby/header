{
    'name': 'AI Website Page Builder',
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Chat with an AI to create and edit website pages',
    'description': """
AI Website Page Builder
=======================

Describe a website page in plain language and let an LLM write it.

* Backend conversation record with a chatter-style thread.
* Provider agnostic: Mistral, Anthropic or any OpenAI-compatible endpoint.
* Pick an existing page as a style reference, or as the page to rewrite.
* The AI output is always a draft: nothing is written to the site until
  you press Apply, and applied pages stay unpublished.
""",
    'author': 'Captivea',
    'license': 'LGPL-3',
    'depends': ['website', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/cap_website_builder_data.xml',
        'views/cap_ai_model_views.xml',
        'views/cap_design_template_views.xml',
        'views/cap_translation_skip_views.xml',
        'views/cap_website_builder_views.xml',
        'views/cap_seo_query_views.xml',
        'views/res_config_settings_views.xml',
        'views/preview_templates.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cap_website_builder/static/src/js/**/*',
            'cap_website_builder/static/src/xml/**/*',
            'cap_website_builder/static/src/scss/**/*',
        ],
    },
    'installable': True,
    'application': True,
}
