import { DynamicSnippet, DynamicSnippetCached } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { registry } from "@web/core/registry";

const CHEVRON_L = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>`;
const CHEVRON_R = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>`;
const GAP = 24;
const AUTOPLAY_MS = 4500;
const DURATION = 450;

/**
 * Testimonials dynamic snippet + single-line INFINITE carousel.
 *
 * After every render the server-rendered cards are re-parented into a
 * transform-based track. To make the loop truly infinite (rather than snapping
 * back to the first card), `visible` clones are added on each side; when the
 * track animates into a clone zone it silently jumps by one full set once the
 * transition ends. This lets ANY card — including the first/last — sit centered
 * and emphasized (.is-center scaled up, .is-side scaled down).
 *
 * 3 cards visible on desktop/tablet, 1 on phone. If there are as few cards as
 * fit on screen, they are simply centered (no arrows, no autoplay).
 *
 * Editor filters still drive the search domain (company/industry/role/tags).
 */
export class Testimonials extends DynamicSnippet {
    static selector = ".s_captivea_testimonials";

    setup() {
        super.setup();
        this._carAuto = null;
    }

    getSearchDomain() {
        const domain = super.getSearchDomain(...arguments);
        const ds = this.el.dataset;
        const companyId = parseInt(ds.filterByCompanyId);
        if (companyId > 0) {
            domain.push(["company_id", "=", companyId]);
        }
        const industryId = parseInt(ds.filterByIndustryId);
        if (industryId > 0) {
            domain.push(["partner_id.industry_id", "=", industryId]);
        }
        const roleId = parseInt(ds.filterByRoleId);
        if (roleId > 0) {
            domain.push(["role_id", "=", roleId]);
        }
        const tagIds = (ds.filterByTagIds || "")
            .split(",")
            .map((v) => parseInt(v))
            .filter((v) => v > 0);
        if (tagIds.length) {
            domain.push(["tag_ids", "in", tagIds]);
        }
        return domain;
    }

    renderContent() {
        super.renderContent();
        this._buildCarousel();
    }

    destroy() {
        this._stopAuto();
        super.destroy();
    }

    _buildCarousel() {
        this._stopAuto();
        const area = this.el.querySelector(".dynamic_snippet_template");
        if (!area) {
            return;
        }
        const cards = [...area.querySelectorAll(".s_cap_tcard")];
        if (!cards.length) {
            return;
        }
        const visible = uiUtils.isSmall() ? 1 : 3;
        const m = cards.length;
        const loop = m > visible;

        const root = document.createElement("div");
        root.className = "s_cap_tcarousel_root position-relative";
        const viewport = document.createElement("div");
        viewport.className = "s_cap_tviewport";
        const track = document.createElement("div");
        track.className = "s_cap_ttrack";

        const slideOf = (node) => {
            const s = document.createElement("div");
            s.className = "s_cap_tslide";
            s.appendChild(node);
            return s;
        };
        const real = cards.map((c) => slideOf(c));
        let ordered = real;
        if (loop) {
            const head = real.slice(0, visible).map((s) => s.cloneNode(true));
            const tail = real.slice(m - visible).map((s) => s.cloneNode(true));
            ordered = [...tail, ...real, ...head];
        }
        ordered.forEach((s) => track.appendChild(s));
        viewport.appendChild(track);

        const prev = document.createElement("button");
        prev.type = "button";
        prev.className = "s_cap_tcar_prev";
        prev.setAttribute("aria-label", "Previous");
        prev.innerHTML = CHEVRON_L;
        const next = document.createElement("button");
        next.type = "button";
        next.className = "s_cap_tcar_next";
        next.setAttribute("aria-label", "Next");
        next.innerHTML = CHEVRON_R;
        root.append(prev, viewport, next);
        area.replaceChildren(root);

        this.track = track;
        this.viewport = viewport;
        this.slides = [...track.children];
        this.m = m;
        this.visible = visible;
        this.lead = loop ? visible : 0;
        this.loop = loop;
        this.idx = 0;

        root.classList.toggle("no-nav", !loop);
        this._layout();

        if (loop) {
            this._go(0, false);
            this.addListener(track, "transitionend", (ev) => this._onTrackEnd(ev));
            this.addListener(prev, "click", () => {
                this._go(this.idx - 1, true);
                this._restartAuto();
            });
            this.addListener(next, "click", () => {
                this._go(this.idx + 1, true);
                this._restartAuto();
            });
            this.addListener(viewport, "pointerenter", () => this._stopAuto());
            this.addListener(viewport, "pointerleave", () => this._startAuto());
            this.addListener(window, "resize", () => {
                this._layout();
                this._go(this.idx, false);
            });
            this._startAuto();
        } else {
            track.classList.add("is-centered");
            this._markCenter(Math.floor((m - 1) / 2));
        }

        // If the snippet was measured before layout settled (width 0), redo it
        // once a frame later so the slide step isn't computed as ~0.
        if (!this.W) {
            this.waitForTimeout(() => {
                this._layout();
                if (this.loop) {
                    this._go(this.idx, false);
                }
            }, 120);
        }
    }

    // Compute the visible viewport width and set explicit pixel widths on the
    // slides (3 up desktop/tablet, 1 up phone). Pixel widths make the per-click
    // step deterministic instead of relying on a % flex-basis that can measure
    // as ~0 at build time.
    _layout() {
        const W = this.track.clientWidth || this.viewport.clientWidth || this.el.clientWidth || 0;
        this.W = W;
        this.slideW = this.visible > 0 ? (W - (this.visible - 1) * GAP) / this.visible : W;
        this.step = this.slideW + GAP;
        this.slides.forEach((s) => {
            s.style.flex = `0 0 ${this.slideW}px`;
            s.style.width = `${this.slideW}px`;
            s.style.maxWidth = `${this.slideW}px`;
        });
    }

    _pos(idx) {
        const d = idx + this.lead;
        return this.W / 2 - (d * this.step + this.slideW / 2);
    }

    _onTrackEnd(ev) {
        // Only react to the track's own translate transition — not the scale
        // transitions that bubble up from the slides.
        if (ev.target === this.track && ev.propertyName === "transform") {
            this._normalize();
        }
    }

    _go(idx, animate) {
        this.idx = idx;
        this.track.style.transition = animate ? `transform ${DURATION}ms ease` : "none";
        this.track.style.transform = `translateX(${this._pos(idx)}px)`;
        if (!animate) {
            // Force reflow so a subsequent animated move actually transitions.
            void this.track.offsetWidth;
        }
        this._markCenter(idx + this.lead);
    }

    _markCenter(d) {
        this.slides.forEach((s, i) => {
            s.classList.toggle("is-center", i === d);
            s.classList.toggle("is-side", i !== d);
        });
    }

    _normalize() {
        let i = this.idx;
        if (i >= this.m) {
            i -= this.m;
        } else if (i < 0) {
            i += this.m;
        }
        if (i !== this.idx) {
            this._go(i, false);
        }
    }

    _startAuto() {
        if (this._carAuto || !this.loop) {
            return;
        }
        this._carAuto = setInterval(() => this._go(this.idx + 1, true), AUTOPLAY_MS);
    }

    _stopAuto() {
        if (this._carAuto) {
            clearInterval(this._carAuto);
            this._carAuto = null;
        }
    }

    _restartAuto() {
        this._stopAuto();
        this._startAuto();
    }
}

registry.category("public.interactions").add(
    "cap_web_quote.testimonials",
    Testimonials
);

registry.category("public.interactions.preview").add("cap_web_quote.testimonials", {
    Interaction: Testimonials,
    mixin: DynamicSnippetCached,
});
