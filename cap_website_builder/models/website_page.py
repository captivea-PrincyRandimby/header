"""The build instructions a design template carries.

A page built to the "Case study" template and one built to "Sector hub" are not
the same job: the sections they need, the order they come in, what belongs above
the fold. That is knowledge about *that template*, so it lives on the template
record rather than on the AI model, where it would be the same sentence for
every page the model ever writes.

No new model for it. The theme already ships its templates as `website.page`
records, and a template's prompt belongs to the template - a second model
holding a foreign key back to it would be the same data with a join in front.
"""
from odoo import fields, models


class WebsitePage(models.Model):
    _inherit = 'website.page'

    # Split the same way as the AI model's two prompts, and for the same reason:
    # the copy is written before any layout exists, the page is built after. A
    # template author has something to say about both, but not in one breath -
    # "never quote a figure the client did not confirm" belongs to the words,
    # "the result strip sits directly under the hero" belongs to the markup.
    cap_content_prompt = fields.Text(
        string='AI Content Instructions',
        help="What a page of this kind should say, and how. Added to the AI "
             "model's Content & SEO prompt whenever this page is chosen as the "
             "design template - it does not replace it.\n\n"
             "Write what is particular to this kind of page: what it has to "
             "cover, in what order, the questions it must answer, what may "
             "never be claimed on it.\n\n"
             "Leave it empty and only the model's own content prompt is used.")
    cap_builder_prompt = fields.Text(
        string='AI Build Instructions',
        help="How the AI Page Builder should lay a page of this kind out. "
             "Added to the AI model's Page Generation prompt whenever this "
             "page is chosen as the design template - it does not replace "
             "it.\n\n"
             "Describe the shape of the page: which sections it needs, in what "
             "order, what each one is for, and anything that must always or "
             "never appear. The words are written earlier in the pipeline, "
             "under the content prompts above.\n\n"
             "Leave it empty and only the model's own page prompt is used.")
