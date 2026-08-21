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
    static shared = ["fetchTags", "getModelNameFilter"];
    modelNameFilter = "quote.testimonial";

    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET, TestimonialsOption),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    setup() {
        this._tags = undefined;
    }

    getModelNameFilter() {
        return this.modelNameFilter;
    }

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(TestimonialsOption.selector)) {
            setDatasetIfUndefined(snippetEl, "filterByTagIds", "");
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }

    /**
     * Testimonials have their own tag list (quote.tag). Customer references use
     * the partner website tags, the blog uses blog.tag: three separate lists.
     */
    async fetchTags() {
        if (!this._tags) {
            this._tags = this.services.orm.searchRead("quote.tag", [], ["id", "name"]);
        }
        return this._tags;
    }
}

registry.category("website-plugins").add(TestimonialsOptionPlugin.id, TestimonialsOptionPlugin);
