import { Component, useState, markup, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

function fullSvg(inner) {
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        (inner || "") +
        "</svg>"
    );
}

/**
 * "Lucide" tab for the html_editor MediaDialog. The selectable icons come from
 * the lucide.icon model (extend the set via Website > Configuration > Import
 * Lucide Icons). Inserts a Lucide icon as inline SVG in a
 * <span class="o_lucide_icon o_editable_media lucide-NAME">.
 */
export class LucideSelector extends Component {
    static template = "cap_web_lucide_icons.LucideSelector";
    static props = ["*"];

    static mediaSpecificClasses = ["o_lucide_icon"];
    static mediaExtraClasses = [/^lucide-\S+$/];
    static mediaSpecificStyles = ["color", "width", "height"];
    static tagNames = ["SPAN"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({ needle: "", icons: [] });
        onWillStart(async () => {
            const recs = await this.orm.searchRead(
                "lucide.icon",
                [["active", "=", true]],
                ["name", "svg"]
            );
            this.state.icons = recs.map((r) => {
                const full = fullSvg(r.svg);
                return { name: r.name, full, markup: markup(full) };
            });
        });
    }

    get filtered() {
        const n = this.state.needle.trim().toLowerCase();
        return n ? this.state.icons.filter((i) => i.name.includes(n)) : this.state.icons;
    }

    async onClickIcon(icon) {
        this.props.selectMedia({ id: icon.name, name: icon.name, svg: icon.full });
        await this.props.save();
    }

    static createElements(selectedMedia) {
        return selectedMedia.map((sel) => {
            const el = document.createElement("span");
            el.className = "o_lucide_icon o_editable_media lucide-" + sel.name;
            el.setAttribute("aria-hidden", "true");
            el.innerHTML = sel.svg || "";
            return el;
        });
    }
}
