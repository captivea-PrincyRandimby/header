import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { uniqueId } from "@web/core/utils/functions";

/**
 * Turns the suggestion panel of the Captivea header search bar into the
 * centered modal of the mock-up.
 *
 * Everything about the search itself stays native: `search_bar.js` fetches and
 * renders the panel, `search_bar_results.js` keeps handling the clicks inside
 * it, and closing goes through the very same `Escape` the interaction listens
 * to. This only changes where the panel is in the page and how it is dressed.
 *
 * The panel is rendered by `renderAt()`, which starts the interactions of what
 * it inserts, so this one is started and destroyed with the panel itself - no
 * observer, no lifecycle of our own.
 */
export class CapSearchModal extends Interaction {
    // The `.all` suggestion template is shared by every search bar whose scope
    // is "All"; the modal is for the header one. Matching happens before
    // `start()` moves the panel, so the ancestor is still there to select on.
    static selector = ".cap_search_form .cap_search_panel";

    dynamicSelectors = {
        ...this.dynamicSelectors,
        _input: () => this.inputEl,
    };

    dynamicContent = {
        ".cap_search_dialog_close": { "t-on-click": this.onClose },
        _root: { "t-on-keydown": this.onKeydown },
        _input: { "t-on-keydown": this.onKeydown },
    };

    setup() {
        this.formEl = this.el.closest(".o_searchbar_form");
        this.inputEl = this.formEl.querySelector(".search-query");
    }

    start() {
        // `position-absolute` and `w-100` hang the panel under the input. They
        // are Bootstrap utilities, i.e. `!important`, so a modal has to drop
        // them rather than override them.
        this.el.classList.remove("position-absolute", "w-100");
        this.el.classList.add("cap_search_modal");

        // "All results" is a `<button type="submit">`, and a submit button
        // outside of its form needs to be told which one it belongs to. That is
        // the only reason the form is given an id.
        this.formEl.id ||= uniqueId("cap_search_form_");
        for (const buttonEl of this.el.querySelectorAll("button[type='submit']")) {
            buttonEl.setAttribute("form", this.formEl.id);
        }

        // Out of the header, exactly like Odoo moves its own `#o_search_modal`
        // (`website/static/src/js/content/adapt_content.js`): a header that
        // scrolls carries a `transform`, which makes it the containing block of
        // anything `position: fixed` inside it - the "full screen" overlay
        // would then be the size of the header.
        //
        // Safe here and not in `setup()`: Odoo runs the `setup()` of every
        // interaction of a batch before the first `start()`, so
        // `search_bar_results.js` has already resolved its own
        // `closest(".o_searchbar_form")`.
        document.body.appendChild(this.el);
    }

    onClose() {
        // Closing the panel is `search_bar.js`'s business, and `Escape` is how
        // it is asked to. Going through it rather than removing the element
        // keeps the interaction and its state in agreement, and leaves the
        // focus in the search field.
        this.inputEl.focus();
        this.inputEl.dispatchEvent(
            new KeyboardEvent("keydown", { key: "Escape", bubbles: true })
        );
    }

    /**
     * Arrow navigation through the suggestions.
     *
     * `search_bar.js` walks the children of the panel, which are the results
     * only as long as the panel is flat. This one has a title bar, a scrolling
     * body and a footer, so the walk is redone on the entries themselves. It
     * runs after the native one - this interaction is started last - and the
     * last `focus()` is the one that sticks.
     *
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (ev.key !== "ArrowUp" && ev.key !== "ArrowDown") {
            return;
        }
        ev.preventDefault();
        const focusableEls = [this.inputEl, ...this.el.querySelectorAll(".dropdown-item")];
        const currentIndex = Math.max(focusableEls.indexOf(document.activeElement), 0);
        const delta = ev.key === "ArrowUp" ? focusableEls.length - 1 : 1;
        focusableEls[(currentIndex + delta) % focusableEls.length].focus();
    }
}

registry.category("public.interactions").add("cap_website_header.search_modal", CapSearchModal);
