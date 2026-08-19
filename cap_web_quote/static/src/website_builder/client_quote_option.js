import { onWillStart, useState } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class ClientQuoteOption extends BaseOptionComponent {
    static template = "cap_web_quote.ClientQuoteOption";
    static selector = ".s_cap_client_quote";
    static dependencies = ["clientQuoteOption"];

    setup() {
        super.setup();
        const plugin = this.dependencies.clientQuoteOption;
        this.state = useState({ testimonials: [] });
        onWillStart(async () => {
            this.state.testimonials.push(...(await plugin.fetchTestimonials()));
        });
    }
}
