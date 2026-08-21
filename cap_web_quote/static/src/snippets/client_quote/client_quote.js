import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

function esc(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
}

/**
 * Client quote snippet: displays the testimonial selected in the editor
 * (data-testimonial-id). The template already server-renders a default
 * (latest published) testimonial for SEO; this only swaps in the chosen one.
 */
export class ClientQuote extends Interaction {
    static selector = ".s_cap_client_quote";

    setup() {
        this.target = this.el.querySelector(".s_cap_cq_target");
        this.recId = parseInt(this.el.dataset.testimonialId);
    }

    async willStart() {
        if (!this.target || !this.recId) {
            return;
        }
        const recs = await this.waitFor(
            this.services.orm.read(
                "quote.testimonial",
                [this.recId],
                ["quote", "author", "role", "company_name"]
            )
        );
        this.rec = recs && recs[0];
    }

    start() {
        if (!this.target || !this.rec) {
            return;
        }
        const r = this.rec;
        const role = r.role || "";
        let footer = esc(r.author);
        if (role) {
            footer += ", " + esc(role);
        }
        if (r.company_name) {
            footer += " at " + esc(r.company_name);
        }
        this.target.innerHTML =
            '<blockquote class="blockquote"><p class="h4">' + esc(r.quote) + "</p></blockquote>" +
            '<footer class="blockquote-footer">' + footer + "</footer>";
    }
}

registry.category("public.interactions").add("cap_web_quote.client_quote", ClientQuote);
registry.category("public.interactions.preview").add("cap_web_quote.client_quote", {
    Interaction: ClientQuote,
});
