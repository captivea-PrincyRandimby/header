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
        this.state = useState({ tags: [] });
        onWillStart(async () => {
            this.state.tags.push(...(await p.fetchTags()));
        });
    }
}
