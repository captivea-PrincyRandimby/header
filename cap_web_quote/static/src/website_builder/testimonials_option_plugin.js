import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { TestimonialsOption } from "./testimonials_option";

class TestimonialsOptionPlugin extends Plugin {
    static id = "testimonialsOption";
    static dependencies = ["dynamicSnippetOption"];
    static shared = ["fetchCompanies", "fetchIndustries", "fetchRoles", "fetchTags", "getModelNameFilter"];
    modelNameFilter = "quote.testimonial";

    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET, TestimonialsOption),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    setup() {
        this._companies = undefined;
        this._industries = undefined;
        this._roles = undefined;
        this._tags = undefined;
    }

    getModelNameFilter() {
        return this.modelNameFilter;
    }

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(TestimonialsOption.selector)) {
            setDatasetIfUndefined(snippetEl, "filterByCompanyId", "0");
            setDatasetIfUndefined(snippetEl, "filterByIndustryId", "0");
            setDatasetIfUndefined(snippetEl, "filterByRoleId", "0");
            setDatasetIfUndefined(snippetEl, "filterByTagIds", "");
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }

    async fetchCompanies() {
        if (!this._companies) {
            this._companies = this.services.orm.searchRead("res.company", [], ["id", "name"]);
        }
        return this._companies;
    }
    async fetchIndustries() {
        if (!this._industries) {
            this._industries = this.services.orm.searchRead("res.partner.industry", [], ["id", "name"]);
        }
        return this._industries;
    }
    async fetchRoles() {
        if (!this._roles) {
            this._roles = this.services.orm.searchRead("quote.role", [], ["id", "name"]);
        }
        return this._roles;
    }
    async fetchTags() {
        if (!this._tags) {
            this._tags = this.services.orm.searchRead("quote.tag", [], ["id", "name"]);
        }
        return this._tags;
    }
}

registry.category("website-plugins").add(TestimonialsOptionPlugin.id, TestimonialsOptionPlugin);
