import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * Make baked-in Lucide icons double-click editable.
 *
 * Native Odoo only treats `span.fa/.fab/.fad/.far/.oi` (MEDIA_SELECTOR) as
 * double-click editable media, so a `.o_lucide_icon` span authored inside a
 * snippet template is invisible to the builder's media dblclick handler
 * (MediaWebsitePlugin). This plugin adds the missing recognition: a
 * double-click on a `.o_lucide_icon.o_editable_media` that sits in an editable
 * region reopens the MediaDialog, which routes to the "Lucide" tab via its
 * static `mediaSpecificClasses = ["o_lucide_icon"]`.
 */
export class LucideDblclickPlugin extends Plugin {
    static id = "lucide_dblclick";
    static dependencies = ["media"];

    setup() {
        this.addDomListener(this.editable, "dblclick", (ev) => {
            const iconEl = ev.target.closest(".o_lucide_icon.o_editable_media");
            if (!iconEl) {
                return;
            }
            // Replaceable if the icon is directly editable, or marked
            // o_editable_media inside an .o_editable region (same rule the
            // native MediaWebsitePlugin uses for media inside non-editable snippets).
            const editable =
                iconEl.parentElement?.isContentEditable || iconEl.closest(".o_editable");
            if (!editable) {
                return;
            }
            this.dependencies.media.openMediaDialog({ node: iconEl });
        });
    }
}

registry.category("website-plugins").add(LucideDblclickPlugin.id, LucideDblclickPlugin);
