import { patch } from "@web/core/utils/patch";
import { useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { OptimizeSEODialog } from "@website/components/dialog/seo";

// Add a JSON-LD (schema.org) code field to the Optimize SEO dialog and persist it.
patch(OptimizeSEODialog.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.jsonLd = useState({ value: "" });
        // Runs after the base onWillStart (which fills this.data via get_seo_data).
        onWillStart(() => {
            this.jsonLd.value = (this.data && this.data.website_meta_json_ld) || "";
        });
    },

    async save() {
        // Validate JSON before saving; abort with a message if it is invalid.
        const raw = (this.jsonLd.value || "").trim();
        if (raw) {
            try {
                JSON.parse(raw);
            } catch (err) {
                this.notification.add(`${_t("Fix it before saving.")} (${err.message})`, {
                    type: "danger",
                    title: _t("Invalid JSON-LD"),
                });
                return;
            }
        }
        if (this.canEditSeo) {
            // Write our field first: super.save() navigates away at the end.
            await this.orm.write(
                this.object.model,
                [this.object.id],
                { website_meta_json_ld: this.jsonLd.value || false },
                {
                    context: {
                        lang: this.website.currentWebsite.metadata.lang,
                        website_id: this.website.currentWebsite.id,
                    },
                }
            );
        }
        return super.save(...arguments);
    },
});
