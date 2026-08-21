import json

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------------------------------------------------------
    # Google Search Console and Analytics 4
    # ------------------------------------------------------------------
    cap_google_enabled = fields.Boolean(
        string="Connect Google Search Console and Analytics",
        compute='_compute_cap_google_enabled',
        readonly=False,
        groups='base.group_system',
    )
    cap_google_service_account_json = fields.Char(
        string="Service account key",
        config_parameter='cap_website_builder.google_service_account_json',
        readonly=False,
        groups='base.group_system',
        help="The full JSON key file of a Google Cloud service account. Give "
             "that account's email read access on the Search Console property "
             "and on the GA4 property, or Google denies the request.",
    )
    cap_google_service_account_email = fields.Char(
        string="Service account email",
        compute='_compute_cap_google_service_account_email',
        groups='base.group_system',
        help="Give this address read access on your Search Console and GA4 "
             "properties, or Google refuses every request.",
    )
    cap_gsc_site_url = fields.Char(
        string="Search Console site",
        config_parameter='cap_website_builder.gsc_site_url',
        readonly=False,
        groups='base.group_system',
        help="Exactly as it appears in Search Console, e.g. "
             "sc-domain:example.com or https://www.example.com/",
    )
    cap_ga4_property_id = fields.Char(
        string="Analytics property",
        config_parameter='cap_website_builder.ga4_property_id',
        readonly=False,
        groups='base.group_system',
        help="GA4 property ID, e.g. properties/123456789. The number alone "
             "works too.",
    )

    # ------------------------------------------------------------------
    # Surfer SEO
    # ------------------------------------------------------------------
    cap_surfer_enabled = fields.Boolean(
        string="Connect Surfer SEO",
        compute='_compute_cap_surfer_enabled',
        readonly=False,
        groups='base.group_system',
    )
    cap_surfer_api_key = fields.Char(
        string="Surfer API key",
        config_parameter='cap_website_builder.surfer_api_key',
        readonly=False,
        groups='base.group_system',
        help="Surfer only issues API keys to the account owner, on plans that "
             "include API access.",
    )
    cap_surfer_workspace_id = fields.Char(
        string="Surfer workspace",
        config_parameter='cap_website_builder.surfer_workspace_id',
        readonly=False,
        groups='base.group_system',
        help="Leave empty to use the account's first workspace.",
    )

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------
    # There is deliberately no "translate into" setting. The target languages
    # are the ones active in the database and published by the website, read at
    # run time: a list kept here as well would be a second place to maintain
    # and a way for the two to disagree - a language added to a site but not to
    # the list would silently never be translated.
    cap_translate_published_pages = fields.Boolean(
        string="Translate published pages automatically",
        config_parameter='cap_website_builder.translate_published_pages',
        readonly=False,
        groups='base.group_system',
        help="Runs hourly, translating published pages into every language "
             "active in this database that their website publishes, except the "
             "one the site is written in and its own variants.\n\n"
             "Uses Odoo's own translation service - the one behind the "
             "editor's Translate button, billed as Odoo credits - not the AI "
             "models configured above, which are for writing pages.\n\n"
             "Terms already translated are never sent again, so the cost falls "
             "to nothing once a site has caught up. The scheduled action "
             "itself must also be active.",
    )
    cap_translate_pages_per_run = fields.Integer(
        string="Pages per run",
        config_parameter='cap_website_builder.translate_pages_per_run',
        default=5,
        readonly=False,
        groups='base.group_system',
        help="How many pages one run may translate. A bound rather than a "
             "target: a run stops here and the next one carries on. This is "
             "what keeps 'every active language' from being a bill nobody "
             "asked for.",
    )

    @api.depends('cap_google_service_account_json')
    def _compute_cap_google_enabled(self):
        for record in self:
            record.cap_google_enabled = bool(record.cap_google_service_account_json)

    @api.depends('cap_google_service_account_json')
    def _compute_cap_google_service_account_email(self):
        for record in self:
            email = False
            if record.cap_google_service_account_json:
                try:
                    email = json.loads(
                        record.cap_google_service_account_json).get('client_email')
                except ValueError:
                    email = False
            record.cap_google_service_account_email = email

    @api.depends('cap_surfer_api_key')
    def _compute_cap_surfer_enabled(self):
        for record in self:
            record.cap_surfer_enabled = bool(record.cap_surfer_api_key)
