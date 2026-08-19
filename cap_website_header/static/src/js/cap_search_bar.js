import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@website/snippets/s_searchbar/search_bar";

/**
 * Captivea header search bar: searching answers in the modal, it never leaves
 * the page for `/website/search`.
 *
 * `search_bar.js` is built the other way around. Submitting is how you get the
 * full results page, so both `Enter` and the `search` event set `limit = 0` -
 * "stop suggesting, we are navigating away". Here the panel *is* the answer, so
 * those two shortcuts are the only things this patch takes over; the fetching,
 * the rendering and the concurrency are the native ones.
 *
 * Scoped to `.cap_search_form`: every other search bar of the website, header
 * mobile or `/website/search` included, keeps behaving exactly as Odoo intends.
 */
patch(SearchBar.prototype, {
    setup() {
        super.setup();
        this.capIsModal = this.el.classList.contains("cap_search_form");
        if (this.capIsModal) {
            // Read by Colibri after `setup()`, so extending it here is enough.
            this.dynamicContent = {
                ...this.dynamicContent,
                _root: {
                    ...this.dynamicContent._root,
                    "t-on-submit": this.onCapSubmit,
                },
            };
        }
    },

    /**
     * @param {SubmitEvent} ev
     */
    onCapSubmit(ev) {
        // "All results" stays the way out to the full page: it is the one
        // submit that is still allowed to navigate.
        if (ev.submitter?.closest(".cap_search_panel")) {
            return;
        }
        ev.preventDefault();
        this.capSearch();
    },

    /**
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (this.capIsModal && ev.key === "Enter") {
            // Also stops the implicit submit of the form, so `onCapSubmit`
            // does not run twice.
            ev.preventDefault();
            this.capSearch();
            return;
        }
        return super.onKeydown(ev);
    },

    /**
     * @param {Event} ev
     */
    onSearch(ev) {
        if (this.capIsModal) {
            // Native `onSearch` gives up on the suggestions as soon as the
            // field has a value, for the same "we are navigating" reason.
            // Clearing the field still closes the panel.
            if (!this.inputEl.value) {
                this.render();
                ev.preventDefault();
            }
            return;
        }
        return super.onSearch(ev);
    },

    async onInput() {
        // Answers on submit only. The panel of this search bar is a full
        // screen modal, so opening it again 400ms after every keystroke would
        // fight the typing - and would fire a request the submit is about to
        // fire a second time.
        if (this.capIsModal) {
            return;
        }
        return super.onInput();
    },

    /** Open the modal at once, fill it in when the results are there. */
    async capSearch() {
        if (!this.inputEl.value.trim()) {
            return;
        }
        this.capRenderLoading();
        const res = await this.keepLast.add(this.waitFor(this.fetch()));
        this.render(res);
    },

    /**
     * Same dance as `render()`, with the spinner template: the panel is
     * replaced, the interactions of the previous one are stopped, and the
     * dropdown is flagged as open so that a focus out still closes it.
     */
    capRenderLoading() {
        if (this.menuEl) {
            this.services["public.interactions"].stopInteractions(this.menuEl);
        }
        const prevMenuEl = this.menuEl;
        this.menuEl = this.renderAt(
            "cap_website_header.search_loading",
            { search: this.inputEl.value, results: [], parts: {}, widget: this.options },
            this.el
        )[0];
        this.hasDropdown = true;
        prevMenuEl?.remove();
    },
});
