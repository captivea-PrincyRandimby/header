import {
    DYNAMIC_SNIPPET,
    setDatasetIfUndefined,
} from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { CapBlogPostsOption } from "./cap_blog_posts_option";

class CapBlogPostsOptionPlugin extends Plugin {
    static id = "capBlogPostsOption";
    static dependencies = ["dynamicSnippetOption"];
    static shared = ["fetchBlogs", "fetchTags", "getModelNameFilter"];
    modelNameFilter = "blog.post";

    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET, CapBlogPostsOption),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    setup() {
        this._blogs = undefined;
        this._tags = undefined;
    }

    getModelNameFilter() {
        return this.modelNameFilter;
    }

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(CapBlogPostsOption.selector)) {
            setDatasetIfUndefined(snippetEl, "filterByBlogId", "0");
            setDatasetIfUndefined(snippetEl, "filterByTagIds", "");
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }

    async fetchBlogs() {
        if (!this._blogs) {
            this._blogs = this.services.orm.searchRead("blog.blog", [], ["id", "name"]);
        }
        return this._blogs;
    }

    async fetchTags() {
        if (!this._tags) {
            this._tags = this.services.orm.searchRead("blog.tag", [], ["id", "name"]);
        }
        return this._tags;
    }
}

registry
    .category("website-plugins")
    .add(CapBlogPostsOptionPlugin.id, CapBlogPostsOptionPlugin);
