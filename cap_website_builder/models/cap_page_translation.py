"""The scheduled action that translates published website pages.

Translation goes through **Odoo's own service** - the one behind the editor's
Translate button - not through the page builder's AI models. Those are
configured for writing pages; translating is Odoo's job, is billed as Odoo
credits, and produces the same output as clicking the button by hand.
"""
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from . import page_translator

_logger = logging.getLogger(__name__)

# Translating every page into every language is a large bill in one go, so a
# run is bounded and the next one carries on where it stopped. Already
# translated terms are skipped, which is what makes that safe to repeat.
DEFAULT_PAGES_PER_RUN = 5
PARAM_PAGES_PER_RUN = 'cap_website_builder.translate_pages_per_run'
PARAM_ENABLED = 'cap_website_builder.translate_published_pages'
# Where the last run stopped, per website. Not a setting - state.
PARAM_CURSOR = 'cap_website_builder.translate_cursor'


class CapPageTranslation(models.AbstractModel):
    _name = 'cap.page.translation'
    _description = 'Odoo Translation of Website Pages'

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @api.model
    def _pages_per_run(self):
        value = self.env['ir.config_parameter'].sudo().get_param(
            PARAM_PAGES_PER_RUN)
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return DEFAULT_PAGES_PER_RUN

    @api.model
    def _active_languages(self):
        """The languages installed and active in this database.

        ``get_installed()`` is the language list Odoo itself works from - it
        returns active records only, so a language switched off in Settings
        stops being translated into without anything else having to be updated.
        """
        return [code for code, _name in self.env['res.lang'].get_installed()]

    @api.model
    def _split_by_base(self, source, codes):
        """Split ``codes`` into what is worth translating into and what is not.

        Returns ``(targets, same)``. ``same`` holds the codes that share the
        source's base language, and they are dropped rather than translated: a
        database with en_US, en_CA, en_SG and en_IN active offers four
        "languages" that are one language, and sending an English page to be
        handed back in English is the whole cost of the exercise and none of
        the benefit. On this database that is what saves an en_US site from
        paying for en_CA and en_SG on every page.

        They are named in the result instead of being silently dropped, so a
        run that translates into fewer languages than expected says why.
        """
        source_base = (source or 'en_US').split('_')[0]
        targets, same = [], []
        for code in codes:
            if not code or code == source:
                continue
            (same if code.split('_')[0] == source_base else targets).append(code)
        return targets, same

    @api.model
    def _target_languages(self, website):
        """The languages a scheduled run may translate this website into.

        Every language the website publishes that is also active in the
        database, minus the one the site is written in and minus its own
        base-language variants. Driven by what is actually set up rather than
        by a list someone has to remember to maintain: add a language to the
        site and the next run picks it up; switch one off and it stops.

        Bounded by design elsewhere - a run translates a limited number of
        pages, and a term already translated is never sent again - which is
        what keeps "every language the site publishes" from being a bill
        nobody asked for.
        """
        active = set(self._active_languages())
        published = [lang.code for lang in website.language_ids
                     if lang.code and lang.code in active]
        targets, _same = self._split_by_base(
            website.default_lang_id.code, published)
        return targets

    # ------------------------------------------------------------------
    # Work
    # ------------------------------------------------------------------
    @api.model
    def _pages_to_translate(self, website=None, after_id=0):
        """Published pages in id order, starting after ``after_id``.

        The cursor is what makes a bounded run move. Without it every run
        starts from the lowest id and spends its whole budget on the same few
        pages: a page is 95% translated, a couple of borderline terms flip on
        any given run, that counts as work, and the pages further down the list
        are never reached. Ordering alone does not fix that - being ordered is
        exactly what makes it repeat.
        """
        domain = [('is_published', '=', True)]
        if after_id:
            domain.append(('id', '>', after_id))
        if website:
            domain += ['|', ('website_id', '=', website.id),
                       ('website_id', '=', False)]
        return self.env['website.page'].sudo().search(domain, order='id')

    # ------------------------------------------------------------------
    # Where the last run stopped
    # ------------------------------------------------------------------
    @api.model
    def _cursors(self):
        """``{website_id: last page id examined}``, one entry per website.

        Per website rather than one number, because each website walks its own
        list of pages and they are different lengths.
        """
        raw = self.env['ir.config_parameter'].sudo().get_param(PARAM_CURSOR)
        try:
            value = json.loads(raw or '{}')
        except ValueError:
            value = {}
        return value if isinstance(value, dict) else {}

    @api.model
    def _save_cursor(self, website_id, page_id):
        """Record that this website has been walked as far as ``page_id``.

        Saved for every page examined, not only for pages that produced work:
        a page that needed nothing must still be stepped over, or the run
        stalls on it exactly as it did before.
        """
        cursors = self._cursors()
        cursors[str(website_id)] = page_id
        self.env['ir.config_parameter'].sudo().set_param(
            PARAM_CURSOR, json.dumps(cursors))

    @api.model
    def _translate_page(self, page, lang):
        """Translate one page into one language.

        Returns ``(written, skipped)``. A chunk that fails is skipped rather
        than fatal, exactly as in the editor's button, so a transient error on
        one batch does not throw away the batches already paid for.
        """
        view = page.view_id
        if not view:
            return 0, 0
        # Terms already known not to translate are filtered out before anything
        # is sent. Without this a page of brand names is never finished: nothing
        # is written for them, so they look untranslated for ever.
        registry = self.env['cap.translation.skip']
        terms = page_translator.pending_terms(
            view, 'arch_db', lang, known_unchanged=registry.known_hashes(lang))
        if not terms:
            return 0, 0

        # The language is named from its code, not from res.lang.name: that
        # field holds "Luxembourg" for fr_LU and "Singapore" for en_SG on a
        # real database, and a model asked to translate "into Luxembourg"
        # answers with nothing usable.
        translations, skipped, unchanged = page_translator.translate_terms(
            self.env, terms, page_translator.language_name(lang))
        # Recorded before the early return: a page whose whole batch came back
        # unchanged is exactly the case worth remembering, and returning first
        # would throw that answer away and buy it again next run.
        registry.remember(lang, unchanged)
        if not translations:
            return 0, skipped

        # Written in one call per page and language: update_field_translations
        # rewrites the whole jsonb value, so a term at a time would be both slow
        # and a chance to lose the ones already written. Whatever came back is
        # written even when some chunks failed - the next run picks up the rest,
        # and paid-for work is never discarded.
        view.update_field_translations('arch_db', {lang: translations})
        return len(translations), skipped

    @api.model
    def _cron_translate_published_pages(self):
        """Translate published pages into every language their website has.

        Bounded per run, and idempotent: a term already translated is never
        sent again, so the cron converges instead of paying for the same page
        every hour.
        """
        parameters = self.env['ir.config_parameter'].sudo()
        if parameters.get_param(PARAM_ENABLED) in ('0', 'False', 'false'):
            return True

        # Nothing to translate into: every active language is the source.
        if len(self._active_languages()) < 2:
            return True

        budget = self._pages_per_run()
        done = 0
        cursors = self._cursors()
        for website in self.env['website'].sudo().search([]):
            langs = self._target_languages(website)
            if not langs:
                continue
            start = cursors.get(str(website.id), 0)
            pages = self._pages_to_translate(website, after_id=start)
            if not pages and start:
                # Walked to the end of this site. Back to the top next run, so
                # pages edited since their turn are picked up again.
                self._save_cursor(website.id, 0)
                continue
            for page in pages:
                if done >= budget:
                    return True
                written = 0
                for lang in langs:
                    try:
                        added, _skipped = self._translate_page(page, lang)
                        written += added
                    except Exception:  # noqa: BLE001 - one page, not the run
                        _logger.exception(
                            "Could not translate page %s into %s", page.id, lang)
                # Stepped over whether or not it produced anything. A page that
                # needed nothing must still be passed, and so must one that
                # trickles a term or two every run - otherwise the budget is
                # spent on the same few pages and the rest are never reached.
                self._save_cursor(website.id, page.id)
                if written:
                    done += 1
                    # Each page is committed on its own, so a failure later in
                    # the run does not throw away what has been paid for - and
                    # the cursor is committed with it.
                    self.env.cr.commit()
        return True

    # ------------------------------------------------------------------
    # On demand, from the page itself
    # ------------------------------------------------------------------
    @api.model
    def _all_languages_for(self, page):
        """Every language active in the database, minus the ones that would
        translate this page into what it already is.

        Wider than the cron's list on purpose: run by hand on one page, the
        point is to get the lot, so this is not limited to the languages that
        page's website happens to publish.
        """
        source = page.website_id.default_lang_id.code or 'en_US'
        return self._split_by_base(source, self._active_languages())

    def action_translate_pages(self):
        """Translate the selected pages into every language in the database.

        Bound to the Actions menu of website.page. Unlike the scheduled action
        this ignores the configured language list: the point of running it by
        hand on one page is to get the lot.
        """
        if not self.env.user.has_group('website.group_website_designer'):
            raise UserError(_(
                "You need Website Designer access rights to translate pages."))
        pages = self.env.context.get('active_model') == 'website.page' and \
            self.env['website.page'].browse(self.env.context.get('active_ids', []))
        if not pages:
            raise UserError(_("Select the page or pages to translate first."))

        written, done, skipped, not_translated = 0, [], set(), 0
        for page in pages:
            targets, same = self._all_languages_for(page)
            skipped.update(same)
            if not targets:
                continue
            for lang in targets:
                try:
                    added, missed = self._translate_page(page, lang)
                    written += added
                    not_translated += missed
                except Exception as error:  # noqa: BLE001 - report, do not stop
                    _logger.exception(
                        "Could not translate page %s into %s", page.id, lang)
                    skipped.add('%s (%s)' % (lang, error))
            done.append(page.url or page.name)

        message = _(
            "%(terms)s term(s) translated across %(pages)s page(s).",
            terms=written, pages=len(done))
        if not_translated:
            # The wording the editor's button uses, for the same reason: a
            # skipped block is not an error, it is work still to do.
            message += _(
                "\n%s text block(s) were skipped during translation. Run it "
                "again to pick them up.", not_translated)
        if skipped:
            message += _(
                "\nLeft out: %s - already the page's own language, or the call "
                "failed.", ', '.join(sorted(skipped)))
        if not written:
            message = _(
                "Nothing to translate: every term on %s is already translated "
                "into the languages this database has.",
                ', '.join(done) or _("the selection"))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if written else 'info',
                'title': _("Page translation"),
                'message': message,
                'sticky': True,
            },
        }

    # ------------------------------------------------------------------
    # Manual run, for one page
    # ------------------------------------------------------------------
    @api.model
    def translate_page_now(self, page_id, langs=None):
        """Translate one page immediately. Returns terms written per language."""
        page = self.env['website.page'].browse(page_id)
        if not page.exists():
            raise UserError(_("That page does not exist."))
        if not self.env.user.has_group('website.group_website_designer'):
            raise UserError(_(
                "You need Website Designer access rights to translate pages."))
        langs = langs or self._target_languages(page.website_id)
        return {lang: self._translate_page(page, lang)[0] for lang in langs}
