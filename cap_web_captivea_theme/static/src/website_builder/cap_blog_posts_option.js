import { onWillStart, useState } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";

export class CapBlogPostsOption extends BaseOptionComponent {
    static template = "cap_web_captivea_theme.CapBlogPostsOption";
    static dependencies = ["capBlogPostsOption"];
    static selector = ".s_cap_blog_posts";

    setup() {
        super.setup();
        const { fetchBlogs, fetchTags, getModelNameFilter } =
            this.dependencies.capBlogPostsOption;
        this.dynamicOptionParams = useDynamicSnippetOption(getModelNameFilter());
        this.blogState = useState({ blogs: [], tags: [] });
        onWillStart(async () => {
            this.blogState.blogs.push(...(await fetchBlogs()));
            this.blogState.tags.push(...(await fetchTags()));
        });
    }
}
