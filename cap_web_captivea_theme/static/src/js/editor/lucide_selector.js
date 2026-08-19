import { Component, useState, markup } from "@odoo/owl";
import { LUCIDE_ICONS } from "@cap_web_captivea_theme/js/editor/lucide_icons";

// Pre-compute rendered markup for the grid; keep the raw string for insertion.
const ICONS = LUCIDE_ICONS.map((i) => ({ name: i.name, raw: i.svg, markup: markup(i.svg) }));

/**
 * "Lucide" tab for the html_editor MediaDialog. Inserts a Lucide icon as inline
 * SVG wrapped in <span class="o_lucide_icon lucide-NAME" contenteditable="false">.
 */
export class LucideSelector extends Component {
    static template = "cap_web_captivea_theme.LucideSelector";
    static props = ["*"];

    // --- statics used by MediaDialog for tab detection / cross-tab class cleanup ---
    static mediaSpecificClasses = ["o_lucide_icon"];
    static mediaExtraClasses = [/^lucide-\S+$/];
    static mediaSpecificStyles = ["color", "width", "height"];
    static tagNames = ["SPAN"];

    setup() {
        this.state = useState({ needle: "" });
    }

    get icons() {
        const n = this.state.needle.trim().toLowerCase();
        return n ? ICONS.filter((i) => i.name.includes(n)) : ICONS;
    }

    async onClickIcon(icon) {
        this.props.selectMedia({ id: icon.name, name: icon.name, svg: icon.raw });
        await this.props.save();
    }

    static createElements(selectedMedia) {
        return selectedMedia.map((sel) => {
            const el = document.createElement("span");
            // o_editable_media keeps the icon selectable/replaceable via the picker.
            el.className = "o_lucide_icon o_editable_media lucide-" + sel.name;
            el.setAttribute("aria-hidden", "true");
            el.innerHTML = sel.svg || "";
            return el;
        });
    }
}
