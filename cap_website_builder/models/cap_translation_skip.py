"""Terms Odoo's translation service hands back unchanged.

Some terms have no translation. Brand and product names (`Odoo ERP`,
`Captivea USA`, `CRM`), slugs, and markup wrapping a bare number are all things
the prompt explicitly tells the service to leave alone - and it obeys, returning
them exactly as sent.

That correct behaviour used to be a permanent cost. An unchanged answer is
dropped rather than written, and Odoo's storage cannot tell "no translation" from
"translated to itself": a term whose stored value equals its source reads back as
untranslated either way. So the term was pending again on the next run, sent
again, paid for again, for ever - and it kept its page looking like unfinished
work, which is what made a bounded run walk the same few pages.

This is the memory that closes that loop. A term the service returns unchanged is
recorded here once and never sent again.

Rows are keyed by a hash of the term, so a term whose source text is later edited
is a different term and gets a fresh chance automatically. The registry is global
rather than per page: `Odoo ERP` appears on dozens of pages, and learning it once
should be enough for all of them.

To make the service reconsider a term - a better model, a changed prompt - delete
its row here and the next run sends it again.
"""
from odoo import api, fields, models

from .page_translator import term_key

# Enough of the term to recognise it in the list, without storing a page of
# markup on every row.
SAMPLE_CHARS = 120


class CapTranslationSkip(models.Model):
    _name = 'cap.translation.skip'
    _description = 'Terms Odoo Translation Returns Unchanged'
    _order = 'lang, sample'

    lang = fields.Char(
        string='Language', required=True, index=True,
        help="The language the term was sent to be translated into. A term can "
             "be untranslatable into one language and translatable into "
             "another, so this is per language, not per term.")
    term_hash = fields.Char(
        string='Term Key', required=True, index=True,
        help="Hash of the exact term that was sent. Edit the text on the page "
             "and it becomes a different term, which is sent again.")
    sample = fields.Char(
        string='Term',
        help="The beginning of the term, so the list can be read.")

    _lang_term_uniq = models.Constraint(
        'unique (lang, term_hash)',
        "A term is only recorded once per language.",
    )

    @api.model
    def known_hashes(self, lang):
        """The hashes already known to come back unchanged in ``lang``.

        Read once per page and language and passed down, rather than queried per
        term: a long page carries hundreds of terms.
        """
        rows = self.sudo().search_read([('lang', '=', lang)], ['term_hash'])
        return {row['term_hash'] for row in rows}

    @api.model
    def remember(self, lang, terms):
        """Record terms the service returned unchanged. Returns how many are new.

        Existing rows are left alone rather than rewritten, so the registry does
        not churn on every run.
        """
        if not terms:
            return 0
        wanted = {term_key(term): term for term in terms if term}
        known = self.known_hashes(lang)
        missing = [key for key in wanted if key not in known]
        if not missing:
            return 0
        self.sudo().create([{
            'lang': lang,
            'term_hash': key,
            'sample': wanted[key][:SAMPLE_CHARS],
        } for key in missing])
        return len(missing)
