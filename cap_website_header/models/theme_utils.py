from odoo import models

from odoo.addons.website.models.theme_models import ThemeUtils as WebsiteThemeUtils

from .website import CAP_HEADER_VIEW


class ThemeUtils(models.AbstractModel):
    _inherit = 'theme.utils'

    # ``theme.utils`` uses this list for two things:
    #  - ``enable_view()`` disables every other header template before enabling
    #    the requested one (only one header template may be active at a time);
    #  - ``_reset_default_config()`` disables everything but the *last* entry,
    #    which must therefore stay ``website.template_header_default``.
    _header_templates = [CAP_HEADER_VIEW] + WebsiteThemeUtils._header_templates
