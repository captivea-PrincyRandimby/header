# -*- coding: utf-8 -*-
# Builds a curated Lucide SVG sprite for the theme and resolves the FA->Lucide map.
# Requires the npm package `lucide-static` reachable via ICONS_DIR.
# Outputs:
#   - <theme>/static/lib/lucide/lucide-sprite.svg   (the <symbol> sprite)
#   - <theme>/tools/lucide_map.py                   (FA2LU dict used by gen_snippets.py)
import os, re, json

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.abspath(os.path.join(_HERE, ".."))
# lucide-static icons dir: override with env LUCIDE_ICONS_DIR if needed.
ICONS_DIR = os.environ.get("LUCIDE_ICONS_DIR",
    "/sessions/affectionate-adoring-shannon/mnt/outputs/node_modules/lucide-static/icons")
SPRITE_OUT = os.path.join(_BASE, "static", "lib", "lucide", "lucide-sprite.svg")
MAP_OUT = os.path.join(_HERE, "lucide_map.py")
JS_OUT = os.path.join(_BASE, "static", "src", "js", "editor", "lucide_icons.js")

# FA (Font Awesome) name -> ordered list of Lucide candidates (first existing wins)
FA2LU = {
    "fa-barcode": ["barcode"],
    "fa-blog": ["newspaper", "rss"],
    "fa-bolt": ["zap"],
    "fa-book": ["book"],
    "fa-boxes-stacked": ["boxes", "package"],
    "fa-briefcase": ["briefcase"],
    "fa-building": ["building", "building-2"],
    "fa-bullhorn": ["megaphone"],
    "fa-calendar-star": ["calendar-star", "calendar-days", "calendar"],
    "fa-car": ["car"],
    "fa-cart-plus": ["shopping-cart"],
    "fa-cart-shopping": ["shopping-cart"],
    "fa-chart-line": ["chart-line", "line-chart", "trending-up"],
    "fa-circle-check": ["circle-check", "check-circle"],
    "fa-circle-xmark": ["circle-x", "x-circle"],
    "fa-clock": ["clock"],
    "fa-cloud": ["cloud"],
    "fa-comments": ["messages-square", "message-square"],
    "fa-comments-question": ["message-circle-question", "message-circle-more", "message-circle"],
    "fa-cubes": ["blocks", "boxes", "package"],
    "fa-diagram-gantt": ["chart-gantt", "gantt-chart", "list-todo"],
    "fa-diagram-project": ["workflow", "git-branch"],
    "fa-earth-europe": ["earth", "globe"],
    "fa-envelope": ["mail"],
    "fa-file-invoice": ["file-text", "receipt"],
    "fa-flag": ["flag"],
    "fa-folder": ["folder"],
    "fa-folder-open": ["folder-open"],
    "fa-gears": ["settings-2", "cog", "settings"],
    "fa-globe": ["globe"],
    "fa-graduation-cap": ["graduation-cap"],
    "fa-hammer": ["hammer"],
    "fa-handshake": ["handshake"],
    "fa-hard-drive": ["hard-drive"],
    "fa-headset": ["headset", "headphones"],
    "fa-industry": ["factory"],
    "fa-key": ["key"],
    "fa-life-ring": ["life-buoy"],
    "fa-location-dot": ["map-pin"],
    "fa-magnifying-glass": ["search"],
    "fa-message": ["message-square"],
    "fa-mobile": ["smartphone"],
    "fa-money-bill-wave": ["banknote"],
    "fa-paintbrush": ["paintbrush", "brush"],
    "fa-pen-ruler": ["pencil-ruler", "pen-tool"],
    "fa-phone": ["phone"],
    "fa-plug": ["plug", "plug-2"],
    "fa-quote-left": ["quote"],
    "fa-receipt": ["receipt"],
    "fa-robot": ["bot"],
    "fa-rocket": ["rocket"],
    "fa-scale-balanced": ["scale"],
    "fa-screwdriver-wrench": ["wrench", "settings"],
    "fa-server": ["server"],
    "fa-share-nodes": ["share-2", "share"],
    "fa-shield-check": ["shield-check"],
    "fa-shield-halved": ["shield-half", "shield"],
    "fa-shop": ["store"],
    "fa-signature": ["signature", "pen-line"],
    "fa-star": ["star"],
    "fa-sticky-note": ["sticky-note"],
    "fa-store": ["store"],
    "fa-table": ["table"],
    "fa-thumbs-up": ["thumbs-up"],
    "fa-triangle-exclamation": ["triangle-alert", "alert-triangle"],
    "fa-truck": ["truck"],
    "fa-truck-fast": ["truck", "truck-fast"],
    "fa-umbrella-beach": ["palmtree", "umbrella"],
    "fa-user": ["user"],
    "fa-user-plus": ["user-plus"],
    "fa-users": ["users"],
    "fa-utensils": ["utensils"],
    "fa-wifi": ["wifi"],
    "fa-wrench": ["wrench"],
}

# A curated common set to also ship in the sprite (for the future Lucide picker tab).
EXTRA = [
    "activity","arrow-right","arrow-up-right","award","badge-check","bell","bookmark",
    "box","calendar","calendar-check","check","chevron-right","circle-help","clipboard-list",
    "coins","compass","credit-card","database","download","external-link","eye","filter",
    "gauge","gift","git-merge","grid-2x2","heart","home","image","inbox","info","layers",
    "layout-dashboard","link","list","lock","map","menu","monitor","moon","package-check",
    "pen","percent","pie-chart","play","printer","refresh-cw","rotate-cw","save","send",
    "settings","share","shield","shopping-bag","sliders-horizontal","sparkles","split",
    "sun","tag","target","thumbs-down","trash-2","trending-down","upload","users-round",
    "video","wallet","warehouse","zap-off","building-2","clipboard-check","file-check",
    "handshake","lightbulb","rocket","shield-check","trophy","users","wrench",
]

def _icon_path(name):
    return os.path.join(ICONS_DIR, name + ".svg")

def resolve(name_or_candidates):
    cands = name_or_candidates if isinstance(name_or_candidates, list) else [name_or_candidates]
    for c in cands:
        if os.path.isfile(_icon_path(c)):
            return c
    return None

def inner_and_viewbox(name):
    svg = open(_icon_path(name), encoding="utf-8").read()
    vb = re.search(r'viewBox="([^"]+)"', svg)
    inner = re.search(r'<svg[^>]*>(.*)</svg>', svg, re.S)
    return (vb.group(1) if vb else "0 0 24 24"), inner.group(1).strip()

def main():
    resolved = {}     # fa-name -> lucide-name
    missing = []
    for fa, cands in FA2LU.items():
        lu = resolve(cands)
        if lu:
            resolved[fa] = lu
        else:
            missing.append(fa)
    if missing:
        raise SystemExit("UNRESOLVED FA icons (fix candidates): " + ", ".join(missing))

    # union of icons to embed: those actually used + curated extras that exist
    used = sorted(set(resolved.values()))
    extra = sorted(set(n for n in EXTRA if resolve(n)))
    all_icons = sorted(set(used) | set(extra))

    symbols = []
    inners = {}   # name -> inner svg markup (for inline embedding in snippets)
    for name in all_icons:
        vb, inner = inner_and_viewbox(name)
        inners[name] = inner
        symbols.append(
            '  <symbol id="lucide-%s" viewBox="%s" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">%s</symbol>'
            % (name, vb, inner))
    sprite = ('<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">\n'
              + "\n".join(symbols) + "\n</svg>\n")
    os.makedirs(os.path.dirname(SPRITE_OUT), exist_ok=True)
    open(SPRITE_OUT, "w", encoding="utf-8").write(sprite)

    with open(MAP_OUT, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n# AUTO-GENERATED by tools/build_lucide_sprite.py - do not edit by hand\n")
        f.write("FA2LU = " + json.dumps(resolved, indent=4, ensure_ascii=False) + "\n")
        # Inner SVG markup per icon, for inline embedding (reliable currentColor across browsers).
        f.write("SVGS = " + json.dumps(inners, ensure_ascii=False) + "\n")

    # JS icon list for the Lucide media-dialog picker tab (full inline SVG per icon)
    os.makedirs(os.path.dirname(JS_OUT), exist_ok=True)
    js_data = [{"name": n,
                "svg": ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                        + inners[n] + '</svg>')} for n in all_icons]
    with open(JS_OUT, "w", encoding="utf-8") as f:
        f.write("// AUTO-GENERATED by tools/build_lucide_sprite.py - do not edit by hand\n")
        f.write("export const LUCIDE_ICONS = " + json.dumps(js_data, ensure_ascii=False) + ";\n")

    print("resolved FA icons:", len(resolved))
    print("icons in sprite (used+extra):", len(all_icons))
    print("sprite:", SPRITE_OUT)
    print("map:", MAP_OUT)
    print("js:", JS_OUT)

if __name__ == "__main__":
    main()
