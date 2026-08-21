from markupsafe import Markup

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools.translate import _

from ..models import page_writer


class CapWebsiteBuilderPreview(http.Controller):
    """Render a draft with the website's own theme.

    The Draft field in the backend is a plain HTML widget: it has none of the
    site's SCSS, so a draft that is correct still looks like unstyled Bootstrap
    there. This route renders the same markup inside website.layout, on the
    frontend, where the theme assets actually load.
    """

    @http.route('/cap_website_builder/preview/<int:record_id>',
                type='http', auth='user', website=True, sitemap=False)
    def preview(self, record_id, **kwargs):
        if not request.env.user.has_group('website.group_website_designer'):
            raise AccessError(_(
                "You need Website Designer access rights to preview a draft."))

        record = request.env['cap.website.builder'].browse(record_id)
        record.check_access('read')
        if not record.draft_arch:
            return request.not_found()

        # Same cleaning as Apply, so the preview shows what would be written,
        # then serialised as HTML: this markup goes straight to the browser's
        # parser rather than through QWeb, and an XML-style <i ... /> would
        # stay open there and collapse everything after it.
        arch = page_writer.sanitize_arch(request.env, record.draft_arch)
        return request.render('cap_website_builder.preview_page', {
            'record': record,
            'body': Markup(page_writer.as_html(arch)),
        })
