import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Captivea header: the row 1 dropdowns and the row 3 mega menus open on hover
 * *and* on click.
 *
 * Both behaviours are native and used as is:
 *
 * - hover: the `website.hoverable_dropdown` interaction, which selects on the
 *   `o_hoverable_dropdown` class `template_header_captivea` puts on `<header>`;
 * - click: Bootstrap's own handler, delegated on `document` for
 *   `[data-bs-toggle="dropdown"]`.
 *
 * They contradict each other on exactly one point. Moving the pointer onto a
 * toggle opens the menu, so the click that follows finds it open and Bootstrap
 * closes it right away: the panel blinks and clicking looks broken.
 *
 * This interaction only neutralises that one click. A click on a menu the
 * pointer has just opened keeps it open and takes ownership of it, so that the
 * next click closes it like on any dropdown. Everything else is left to the
 * native code: closing on mouse out, on outside click or on `Escape`, keyboard
 * navigation, `aria-expanded`, and the moving of the mega menu panels between
 * the desktop and the mobile navbars.
 *
 * Nothing is needed below `lg`: `.cap_header` is `d-none d-lg-block` and the
 * offcanvas is built from the native `website.submenu`, so its dropdowns only
 * ever see a click.
 */
export class CapHeaderDropdown extends Interaction {
    static selector = "header#top";
    // `:has()` equivalent, but supported everywhere.
    static selectorHas = ".cap_header";

    dynamicContent = {
        ".cap_header .dropdown-toggle": {
            "t-on-click.withTarget": this.onToggleClick,
            // Bootstrap fires its dropdown events on the toggle, not on the menu.
            "t-on-hide.bs.dropdown.withTarget": this.onDropdownHide,
            "t-on-hidden.bs.dropdown.withTarget": this.onDropdownHidden,
        },
    };

    setup() {
        // Toggles whose open menu belongs to a click: for those the next click
        // has to close the menu instead of keeping it open.
        this.clickOwnedToggleEls = new Set();
        // Toggle whose next `hide` has to be vetoed, see `onToggleClick`.
        this.adoptedToggleEl = null;
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} toggleEl
     */
    onToggleClick(ev, toggleEl) {
        this.adoptedToggleEl = null;
        // Bootstrap puts `show` on the toggle itself, whoever opened the menu.
        const isShown = toggleEl.classList.contains("show");

        if (isShown && !this.clickOwnedToggleEls.has(toggleEl)) {
            // Opened by the pointer. Bootstrap's handler runs right after this
            // one (it is delegated on `document`, so it only sees the event once
            // it has bubbled up) and would call `hide()`: flag the toggle so
            // that `onDropdownHide` vetoes that single hide. No need to
            // `preventDefault()` the `href="#"` of the toggle either, Bootstrap
            // still does it.
            this.clickOwnedToggleEls.add(toggleEl);
            this.adoptedToggleEl = toggleEl;
            return;
        }

        // Closed: Bootstrap is about to open it, and the menu is then owned by
        // the click. Open and already owned: Bootstrap closes it, and
        // `onDropdownHidden` does the bookkeeping.
        if (!isShown) {
            this.clickOwnedToggleEls.add(toggleEl);
        }
    }

    /**
     * @param {Event} ev `hide.bs.dropdown`, cancelable
     * @param {HTMLElement} toggleEl
     */
    onDropdownHide(ev, toggleEl) {
        if (this.adoptedToggleEl === toggleEl) {
            this.adoptedToggleEl = null;
            ev.preventDefault();
        }
    }

    /**
     * @param {Event} ev `hidden.bs.dropdown`
     * @param {HTMLElement} toggleEl
     */
    onDropdownHidden(ev, toggleEl) {
        // Mouse out, outside click, `Escape`, ...: the next click has to open
        // the menu again, not to take ownership of it.
        this.clickOwnedToggleEls.delete(toggleEl);
    }
}

registry.category("public.interactions").add("cap_website_header.header_dropdown", CapHeaderDropdown);
