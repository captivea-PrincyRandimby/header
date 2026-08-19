import { onWillStart, useState } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";

export class CustomerReferencesOption extends BaseOptionComponent {
    static template = "cap_web_captivea_theme.CustomerReferencesOption";
    static dependencies = ["customerReferencesOption"];
    static selector = ".s_customer_references";

    setup() {
        super.setup();
        const { fetchIndustries, fetchTags, fetchCompanies, getModelNameFilter } =
            this.dependencies.customerReferencesOption;
        this.dynamicOptionParams = useDynamicSnippetOption(getModelNameFilter());
        this.refState = useState({ industries: [], tags: [], companies: [] });
        onWillStart(async () => {
            this.refState.companies.push(...(await fetchCompanies()));
            this.refState.industries.push(...(await fetchIndustries()));
            this.refState.tags.push(...(await fetchTags()));
        });
    }
}
