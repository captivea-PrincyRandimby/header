import { DynamicSnippet, DynamicSnippetCached } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

/**
 * Customer references dynamic snippet. Reads the editor-set data attributes and
 * extends the search domain sent to /website/snippet/filters.
 *   data-filter-by-company-id  -> [id, child_of, companyId]
 *   data-filter-by-industry-id -> [industry_id, =, industryId]
 *   data-filter-by-tag-ids     -> [website_tag_ids, in, [ids]]
 */
export class CustomerReferences extends DynamicSnippet {
    static selector = ".s_customer_references";

    /**
     * Force the "custom layout" branch of website.s_dynamic_snippet.grid so each
     * card (one server fragment per record) is wrapped in a responsive 4-up column
     * inside a single row — instead of the default col-{12/chunkSize} grid.
     */
    getQWebRenderOptions() {
        const options = super.getQWebRenderOptions(...arguments);
        options.columnClasses =
            options.columnClasses || "col-6 col-md-4 col-lg-2 d-flex mb-4";
        return options;
    }

    getSearchDomain() {
        const domain = super.getSearchDomain(...arguments);
        const ds = this.el.dataset;
        const companyId = parseInt(ds.filterByCompanyId);
        if (companyId > 0) {
            domain.push(["id", "child_of", companyId]);
        }
        const industryId = parseInt(ds.filterByIndustryId);
        if (industryId > 0) {
            domain.push(["industry_id", "=", industryId]);
        }
        const tagIds = (ds.filterByTagIds || "")
            .split(",")
            .map((v) => parseInt(v))
            .filter((v) => v > 0);
        if (tagIds.length) {
            domain.push(["website_tag_ids", "in", tagIds]);
        }
        return domain;
    }
}

registry.category("public.interactions").add(
    "cap_web_captivea_theme.customer_references",
    CustomerReferences
);

// Also register for EDIT mode (website builder), otherwise the snippet stays
// stuck on the loading placeholder while editing the page.
registry.category("public.interactions.preview").add("cap_web_captivea_theme.customer_references", {
    Interaction: CustomerReferences,
    mixin: DynamicSnippetCached,
});
