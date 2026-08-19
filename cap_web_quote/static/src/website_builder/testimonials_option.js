import { onWillStart, useState } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";

export class TestimonialsOption extends BaseOptionComponent {
    static template = "cap_web_quote.TestimonialsOption";
    static dependencies = ["testimonialsOption"];
    static selector = ".s_captivea_testimonials";

    setup() {
        super.setup();
        const p = this.dependencies.testimonialsOption;
        this.dynamicOptionParams = useDynamicSnippetOption(p.getModelNameFilter());
        this.state = useState({ companies: [], industries: [], roles: [], tags: [] });
        onWillStart(async () => {
            this.state.companies.push(...(await p.fetchCompanies()));
            this.state.industries.push(...(await p.fetchIndustries()));
            this.state.roles.push(...(await p.fetchRoles()));
            this.state.tags.push(...(await p.fetchTags()));
        });
    }
}
