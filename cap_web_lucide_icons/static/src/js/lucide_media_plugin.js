import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { LucideSelector } from "./lucide_selector";

/**
 * Adds a "Lucide" tab to the editor MediaDialog via the media_dialog_extra_tabs
 * resource read by html_editor's MediaPlugin.
 */
export class LucideMediaPlugin extends Plugin {
    static id = "lucide_media";

    resources = {
        media_dialog_extra_tabs: withSequence(30, {
            id: "LUCIDE",
            title: _t("Lucide"),
            Component: LucideSelector,
            sequence: 30,
        }),
    };
}

registry.category("website-plugins").add(LucideMediaPlugin.id, LucideMediaPlugin);
