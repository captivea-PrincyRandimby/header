from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

# Sent with ARTICLE_PROMPT, at the step that writes the words. Nothing here is
# about markup: at that point in the pipeline the page has no layout yet and the
# answer is plain text with markdown headings.
DEFAULT_CONTENT_PROMPT = """How this company writes, and what makes a page worth
ranking.

Voice:
- Write for the person who has to make a decision, not for a search engine.
- Concrete over abstract. Name the product, the industry, the job, the number.
- No superlatives you cannot support, no "leading provider", no "in today's
  fast-paced world".

Substance:
- Every section says something a reader did not already know from its heading.
- Never invent a figure, a client name, a date, an award or a certification. If
  the material you are given does not contain it, write around it.
- Prefer what the company actually does over what any company could claim.

SEO:
- The main keyword belongs in the H1 and in the first paragraph, written the way
  a person would say it. Never repeat a keyword for its own sake.
- Give each sub keyword a section of its own, headed in the words people search.
- Answer the question a searcher came with early, then earn the rest of the page.
- Close with what the reader should do next, in one short section."""

DEFAULT_SYSTEM_PROMPT = """You write the body content of Odoo 19 website pages.

Output rules:
- Answer with HTML only. No explanation, no markdown code fences.
- Never output <html>, <head>, <body>, <script> or inline event handlers.
- Return only the sections that live inside the page body.

An Odoo page is stored as XML, not HTML, so the markup must be XML-valid or
Odoo refuses the whole page:
- Self-close every void element: <img ... />, <br/>, <hr/>, <input ... />,
  <source ... />. A bare <img ...> without the closing slash is the single
  most common way a generated page fails to load.
- Self-close nothing else. An empty <i>, <span>, <a>, <div> or <section> is
  written open and closed: <i class="fa fa-flag"></i>, never <i ... />. The
  slash is legal XML but a browser ignores it on those tags, leaves the element
  open, and swallows the rest of the section into it - which collapses the page
  from that point down. Generate keywords 
- Every tag closes, in the right order. Never leave a <div> or <section> open.
- Every attribute value is quoted, and no attribute stands alone: write
  autoplay="autoplay", not a bare autoplay.
- Escape & as &amp; everywhere, including inside href and src.
- Use numeric character references, not named HTML entities: write &#160;
  rather than &nbsp;. Named entities are undefined in XML.
- Write real, specific copy about the subject. Never lorem ipsum, never placeholders.
- When asked to change an existing page, return the complete new body, not a diff.

When a reference page is supplied, it outranks every style rule below.
Your job is not to design a page. It is to rebuild the reference page with new
content. Work like this:

1. Pick the blocks you need from the supplied list of block types. That list is
   exhaustive: you may not use any other kind of section. In particular, do not
   fall back on plain s_text_block sections, and do not stack bare headings and
   paragraphs where the reference uses a real snippet.
2. For each block, start from its full-markup example and change only the words
   inside the text nodes and the image URLs. Keep everything else byte for byte:
   the s_* snippet class, the o_cc / o_cc1..5 colour classes, the pt* / pb*
   spacing classes, the data-snippet and data-name attributes, the
   container / row / col-lg-* nesting, and the heading levels.
3. Keep the parts that are easy to drop and change the look completely: the
   call-to-action buttons with their exact classes, the image wrappers and their
   classes (rounded corners, shadows, ratios), and the column split between
   image and text.
4. Images: only use a URL from the supplied list, copied exactly. Never invent a
   path, never point at an external site, never use a placeholder. If no listed
   image suits the block, drop the <img> and keep the rest of the block intact.
5. Follow the reference's own conventions even where they differ from generic
   Bootstrap practice. Do not modernise it, do not simplify it, do not
   substitute your own layout ideas.

The structure outline shows the whole page; the full-markup examples show the
exact syntax. Take the vocabulary from the outline and the spelling from the
examples.

Only when no reference page is supplied, fall back to plain Odoo defaults:
top level <section class="s_text_block pt32 pb32"> elements, container / row /
col-lg-* grids, <h1>/<h2>/<h3> headings, <a class="btn btn-primary"> buttons."""


class CapAiModel(models.Model):
    _name = 'cap.ai.model'
    _description = 'AI Model'
    _order = 'is_default desc, sequence, id'

    name = fields.Char(
        string='Name', required=True,
        help="Label shown when picking a model, e.g. 'Mistral Large'.")
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    is_default = fields.Boolean(
        string='Default',
        help="Model preselected on new page requests. Only one can be the default.")

    provider = fields.Selection(
        [
            ('mistral', 'Mistral'),
            ('anthropic', 'Anthropic (Claude)'),
            ('openai_compatible', 'OpenAI-compatible endpoint'),
        ],
        string='Provider', required=True, default='mistral')
    model_name = fields.Char(
        string='Model ID', required=True,
        help="Identifier sent to the API, e.g. claude-opus-5, claude-sonnet-5, "
             "mistral-large-latest, gpt-4o.")
    api_key = fields.Char(
        string='API Key', groups='base.group_system',
        help="Stored in database. Only settings administrators can read it.")
    base_url = fields.Char(
        string='Base URL',
        help="Only for an OpenAI-compatible endpoint, without the trailing "
             "/chat/completions. For example http://localhost:11434/v1")

    timeout = fields.Integer(
        string='Timeout (s)', default=600,
        help="How long to wait for one answer. Writing a page against a full "
             "Surfer brief runs past three minutes on a large model.")
    max_tokens = fields.Integer(string='Max Tokens', default=16000)
    thinking_budget = fields.Integer(
        string='Thinking Budget', default=0,
        help="Anthropic only. Tokens the model may spend reasoning before it "
             "answers, taken from the same budget as the answer itself. Leave "
             "at 0: with thinking on, a model given a long list of constraints "
             "can spend the whole budget reasoning and return nothing at all.")
    max_context_chars = fields.Integer(
        string='Reference Page Limit', default=60000,
        help="Maximum number of characters of a reference page sent to the AI. "
             "Real website pages are large; a low limit means the AI only ever "
             "sees the top of the page it is meant to imitate.")
    # Two prompts, because the pipeline asks the model for two different things
    # at two different moments. The copy is written before any layout exists and
    # comes back as plain text; the page is built afterwards and comes back as
    # markup. One prompt covering both used to mean every page carried markup
    # rules into the step that writes sentences, and voice rules into the step
    # that writes <section> tags.
    content_prompt = fields.Text(
        string='Content & SEO Prompt', default=DEFAULT_CONTENT_PROMPT,
        help="Voice, substance and SEO. Sent when the copy is written, before "
             "the page has any layout, so it is about words rather than "
             "markup.\n\n"
             "Applies to every page built with this model. A design template's "
             "own content instructions are added after it, not in place of it.")
    system_prompt = fields.Text(
        string='Page Generation Prompt', default=DEFAULT_SYSTEM_PROMPT,
        help="Style and layout. Sent when the copy is turned into a page, and "
             "it carries the markup rules an Odoo view has to satisfy.\n\n"
             "Applies to every page built with this model. A design template's "
             "own build instructions are added after it, not in place of it.")

    request_count = fields.Integer(
        string='Requests', compute='_compute_request_count')

    def _compute_request_count(self):
        data = self.env['cap.website.builder']._read_group(
            [('ai_model_id', 'in', self.ids)], groupby=['ai_model_id'],
            aggregates=['__count'])
        counts = {model.id: count for model, count in data}
        for record in self:
            record.request_count = counts.get(record.id, 0)

    @api.constrains('provider', 'base_url')
    def _check_base_url(self):
        for record in self:
            if record.provider == 'openai_compatible' and not record.base_url:
                raise UserError(_(
                    "An OpenAI-compatible model needs a base URL."))

    def write(self, vals):
        result = super().write(vals)
        if vals.get('is_default'):
            (self.search([('is_default', '=', True)]) - self).write({'is_default': False})
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if any(record.is_default for record in records):
            last_default = records.filtered('is_default')[-1]
            (self.search([('is_default', '=', True)]) - last_default).write(
                {'is_default': False})
        return records

    @api.model
    def _get_default_model(self):
        return self.search([('is_default', '=', True)], limit=1) \
            or self.search([], limit=1)

    def action_reset_system_prompt(self):
        """Overwrite both stored prompts with the module's current defaults.

        Records created by an earlier version keep whatever prompts they were
        created with, so an upgrade alone never improves their output.
        """
        self.write({
            'content_prompt': DEFAULT_CONTENT_PROMPT,
            'system_prompt': DEFAULT_SYSTEM_PROMPT,
        })
        return True

    def action_open_requests(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'cap_website_builder.cap_website_builder_action')
        action['domain'] = [('ai_model_id', '=', self.id)]
        action['context'] = {'default_ai_model_id': self.id}
        return action
