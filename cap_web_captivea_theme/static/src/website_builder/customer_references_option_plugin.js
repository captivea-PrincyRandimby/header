import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { CustomerReferencesOption } from "./customer_references_option";

class CustomerReferencesOptionPlugin extends Plugin {
    static id = "customerReferencesOption";
    static dependencies = ["dynamicSnippetOption"];
    static shared = ["fetchIndustries", "fetchTags", "fetchCompanies", "getModelNameFilter"];
    modelNameFilter = "res.partner";

    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET, CustomerReferencesOption),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    setup() {
        this._industries = undefined;
        this._tags = undefined;
        this._companies = undefined;
    }

    getModelNameFilter() {
        return this.modelNameFilter;
    }

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(CustomerReferencesOption.selector)) {
            setDatasetIfUndefined(snippetEl, "filterByCompanyId", "0");
            setDatasetIfUndefined(snippetEl, "filterByIndustryId", "0");
            setDatasetIfUndefined(snippetEl, "filterByTagIds", "");
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }

    async fetchIndustries() {
        if (!this._industries) {
            this._industries = this.services.orm.searchRead("res.partner.industry", [], ["id", "name"]);
        }
        return this._industries;
    }

    async fetchTags() {
        if (!this._tags) {
            this._tags = this.services.orm.searchRead("res.partner.tag", [], ["id", "name"]);
        }
        return this._tags;
    }

    async fetchCompanies() {
        if (!this._companies) {
            this._companies = this.services.orm.searchRead(
                "res.partner",
                [["is_company", "=", true], ["assigned_partner_id", "!=", false]],
                ["id", "display_name"]
            );
        }
        return this._companies;
    }
}

registry
    .category("website-plugins")
    .add(CustomerReferencesOptionPlugin.id, CustomerReferencesOptionPlugin);
