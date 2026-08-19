import { DynamicSnippet, DynamicSnippetCached } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

/**
 * Captivea Blog Posts dynamic snippet. Independent from Odoo's native blog
 * snippet. Extends the search domain from editor-set data attributes:
 *   data-filter-by-blog-id  -> [blog_id, =, id]
 *   data-filter-by-tag-ids  -> [tag_ids, in, [ids]]
 * (is_published is auto-applied server-side by website.snippet.filter.)
 */
export class CapBlogPosts extends DynamicSnippet {
    static selector = ".s_cap_blog_posts";

    /**
     * Force the "custom layout" branch of website.s_dynamic_snippet.grid so each
     * card (one server fragment per record) is wrapped in a responsive 3-up
     * column inside a single row.
     */
    getQWebRenderOptions() {
        const options = super.getQWebRenderOptions(...arguments);
        options.columnClasses =
            options.columnClasses || "col-12 col-sm-6 col-lg-4 d-flex mb-4";
        return options;
    }

    getSearchDomain() {
        const domain = super.getSearchDomain(...arguments);
        const ds = this.el.dataset;
        const blogId = parseInt(ds.filterByBlogId);
        if (blogId > 0) {
            domain.push(["blog_id", "=", blogId]);
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
}

registry.category("public.interactions").add(
    "cap_web_captivea_theme.cap_blog_posts",
    CapBlogPosts
);

// Also register for EDIT mode (website builder), otherwise the snippet stays
// stuck on the loading placeholder while editing the page.
registry.category("public.interactions.preview").add("cap_web_captivea_theme.cap_blog_posts", {
    Interaction: CapBlogPosts,
    mixin: DynamicSnippetCached,
});
