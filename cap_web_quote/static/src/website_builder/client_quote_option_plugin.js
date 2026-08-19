import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { ClientQuoteOption } from "./client_quote_option";

/**
 * Options for the Client quote snippet: exposes the list of published
 * testimonials (shared with the option component) so a specific one can be
 * selected (writes data-testimonial-id).
 */
class ClientQuoteOptionPlugin extends Plugin {
    static id = "clientQuoteOption";
    static shared = ["fetchTestimonials"];

    resources = {
        builder_options: withSequence(SNIPPET_SPECIFIC_END, ClientQuoteOption),
    };

    setup() {
        this._testimonials = undefined;
    }

    async fetchTestimonials() {
        if (!this._testimonials) {
            this._testimonials = this.services.orm.searchRead(
                "quote.testimonial",
                [["is_published", "=", true]],
                ["id", "name", "author"],
                { order: "sequence, id desc" }
            );
        }
        return this._testimonials;
    }
}

registry.category("website-plugins").add(ClientQuoteOptionPlugin.id, ClientQuoteOptionPlugin);
