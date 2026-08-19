import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * "Transform your solutions" panel: the shortcut column on the left switches
 * the content on the right, on hover and on click (New1 to New6 mock-ups).
 *
 * Everything is already in the page - six `.cap_mm_pane`, `display: none` on all
 * but the active one - so this only moves the `active` class around. Nothing is
 * fetched: the panel is one stored `mega_menu_content` value.
 *
 * A shortcut is paired with its pane by `data-cap-pane` rather than by position,
 * so that reordering or duplicating one in the builder cannot end up showing
 * the wrong content. A shortcut whose pane does not exist is left alone and
 * behaves like the plain link it is - which is also what happens on the panels
 * saved before this design existed: they have shortcuts but no pane, and
 * "Reset the mega menu panels" is the way to bring them up to date.
 *
 * Interactions do not run in edit mode, so the builder would only ever reach the
 * first pane. The stylesheet handles that: under `body.editor_enable` the six
 * panes are shown stacked.
 */
export class CapMegaSolutions extends Interaction {
    static selector = ".s_mega_menu_cap_solutions";

    dynamicContent = {
        ".cap_mm_shortcut": {
            "t-on-mouseenter.withTarget": this.onShortcutActivate,
            // Keyboard parity: tabbing through the column shows the same panes
            // the pointer does.
            "t-on-focus.withTarget": this.onShortcutActivate,
            "t-on-click.withTarget": this.onShortcutClick,
        },
    };

    setup() {
        this.shortcutEls = [...this.el.querySelectorAll(".cap_mm_shortcut")];
        this.paneEls = [...this.el.querySelectorAll(".cap_mm_pane")];
    }

    start() {
        // The stored content is edited in the builder, where a duplicated or
        // deleted block can leave no `active` at all, or two of them. One pane
        // has to be visible and only one, so the first is picked.
        const activeEl = this.paneEls.find((paneEl) => paneEl.classList.contains("active"));
        this.select(activeEl?.dataset.capPane ?? this.paneEls[0]?.dataset.capPane);
    }

    /**
     * Show the pane named `name`, and mark its shortcut. A name with no pane
     * changes nothing at all - see the class comment.
     *
     * @param {string|undefined} name
     */
    select(name) {
        if (!name || !this.paneEls.some((paneEl) => paneEl.dataset.capPane === name)) {
            return;
        }
        for (const paneEl of this.paneEls) {
            paneEl.classList.toggle("active", paneEl.dataset.capPane === name);
        }
        for (const shortcutEl of this.shortcutEls) {
            shortcutEl.classList.toggle("active", shortcutEl.dataset.capPane === name);
        }
    }

    /**
     * @param {Event} ev `mouseenter` or `focus`
     * @param {HTMLElement} shortcutEl
     */
    onShortcutActivate(ev, shortcutEl) {
        this.select(shortcutEl.dataset.capPane);
    }

    /**
     * A click on a shortcut that is not the active one selects it, and stops
     * there; a click on the active one follows the link.
     *
     * That is what the chevron of the mock-ups says, and it works out the same
     * for both ways in: with a pointer the hover has already selected the
     * shortcut, so a single click navigates, while on a touch screen - where
     * there is no hover - the first tap shows the pane and the second one
     * leaves. Same reconciliation as the hover/click dropdowns of the header,
     * see `cap_header_dropdown.js`.
     *
     * @param {MouseEvent} ev
     * @param {HTMLElement} shortcutEl
     */
    onShortcutClick(ev, shortcutEl) {
        const name = shortcutEl.dataset.capPane;
        if (!name || !this.paneEls.some((paneEl) => paneEl.dataset.capPane === name)) {
            return; // no pane behind it: a plain link
        }
        if (!shortcutEl.classList.contains("active")) {
            ev.preventDefault();
            this.select(name);
        }
    }
}

registry
    .category("public.interactions")
    .add("cap_website_header.mega_solutions", CapMegaSolutions);
