# cap_website_header

Replaces the standard Odoo header with the three-row Captivea header:

1. **Top bar** — secondary menus and the language selector (hidden below `lg`).
2. **Main row** — logo, search bar, "Contact us" call to action.
3. **Mega menu bar** — the four wide panels (hidden below `lg`).

Below `lg`, the native burger and offcanvas (`website.template_header_mobile`)
are used as they are.

## Enabling it

The header is a regular *header template*: a view inheriting `website.layout`,
inactive by default, enabled **per website** through the copy-on-write of
`ir.ui.view`. Two ways to turn it on:

- Website ‣ Configuration ‣ Settings ‣ *Captivea Header*;
- the builder's Header ‣ Template option.

## The two buttons

Both live in the website settings, under the *Captivea Header* toggle.

**Create the Captivea menus** — creates the menus missing on the selected
website. Idempotent: existing menus are matched by name under the same parent and
are never renamed, re-targeted or deleted. One exception, for websites
provisioned before the descriptions existed: an entry whose `cap_menu_description`
is **empty** gets the reference one. A description already filled in is never
overwritten.

**Reset the mega menu panels** — destructive on purpose. Rewrites the content of
the Captivea panels with the reference designs, so any builder edit on them is
lost. It also deletes the submenus a panel replaces (listed in
`superseded_children`) — those only. If a Captivea menu carries a submenu added
by hand, the action stops and names it instead of deleting it silently.

## Which row a menu lands in

One menu tree (`website.menu_id.child_id`), split on the added field
`website.menu.cap_header_row`:

| `cap_header_row` | Row |
|---|---|
| `top` | row 1 |
| `mega` | row 3 |

**Not on `is_mega_menu`**, deliberately: a row 1 menu may carry a mega menu panel
— that is how *About* gets its free content while staying at the top.
`is_mega_menu` now only decides the *shape* of the dropdown: a link list or a
free panel.

`cap_header_row` is a stored computed field with `readonly=False`, the standard
Odoo idiom for an overridable default. It is initialised from `is_mega_menu` (so
a mega menu created from the builder lands in row 3) and never rewritten
afterwards. Worth knowing: turning an existing row 1 menu into a mega menu does
**not** move it to row 3 — set `cap_header_row` by hand. This is intended.

The small uppercase line under a row 3 label comes from the added field
`website.menu.cap_mega_subtitle`.

## The three row 1 designs

| Mock-up | Menu | Mechanism |
|---|---|---|
| Line1Template1 | Resources | menu tree + `cap_menu_description` |
| Line1Template3 | Careers | same |
| Line1Template2 | About | `s_mega_menu_cap_about` snippet in `mega_menu_content` |

*About* is only created as a panel if it does not exist yet. An *About* already
present as a plain dropdown is left intact — converting it means deleting its
submenus, which belongs to *Reset the mega menu panels*.

## Language selector

Odoo lists every published language, current one included, and only puts
`.active` on it. `website.scss` then forces the **header** text colour on
`.js_language_selector span` with `!important` — a colour made for the bar, not
for a white dropdown, which leaves the entries unreadable on a light theme (Odoo
says as much in the TODO above the rule). The entries therefore restate their own
colours, `!important` included, and the active one is marked in red with a check.
The result no longer depends on the theme's `header-text-color`.

## Search panel

The search itself stays **native** — route `/website/snippet/autocomplete`,
`.o_searchbar_form` interaction, no AI. Only its presentation and the moment it
answers are ours.

| Action | Result |
|---|---|
| typing | nothing: live suggestion is off on this bar |
| `Enter` or click on the button | the modal opens **at once** with a spinner, then fills in |
| "All results" | the only submit that still navigates, to `/website/search` |
| close button, `Escape`, outside click | native closing |

So the default results page is no longer where a search ends: the modal is.

`cap_search_bar.js` patches `SearchBar` and takes over three methods only —
`onKeydown`, `onSearch`, `onInput`. All three set `limit = 0` natively ("we are
leaving the page, stop suggesting"), which here would switch the bar off for
good. The `fetch`, the rendering and the concurrency (`keepLast`) stay native.
The patch is **scoped to `.cap_search_form`**: the mobile header bar, the
`/website/search` one and any search snippet keep Odoo's behaviour.

`cap_search_modal.js` moves the panel into the `<body>`. A header that scrolls
carries a `transform`, which makes it the containing block of any
`position: fixed` descendant — the "full screen" overlay would then be the size
of the header. Odoo moves its own `#o_search_modal` for the same reason
(`website/static/src/js/content/adapt_content.js`).

The panel template is `website.s_searchbar.autocomplete.all`, inherited in
`primary` mode: that is the native extension point, `search_bar.js` picks a
template by search type. **Scope worth knowing:** the template is shared by
*every* search bar whose scope is "All", on every website of the database, not
only the header one. It is therefore written as a plain dropdown card, and
`cap_search_modal.js` is what turns it into the centered modal — for the Captivea
header only.

Note: adding a **new asset file** requires a server restart (the manifest is
cached per process). CSS and templates are refreshed without one.

## Languages

**The source language of the module is English (US)**: panel content, field
labels, error messages, provisioned menu names, builder option titles and code
comments. No exception. Translations live in `i18n/`.

| File | Scope |
|---|---|
| `cap_website_header.pot` | template, regenerated, never edited by hand |
| `fr.po` | loaded for `fr_FR`, `fr_CA`, `fr_LU` |
| `es.po` | loaded for `es_ES` |

English variants (`en_US`, `en_CA`, `en_IN`, `en_SG`) have no file: they read the
source. Odoo logs it on upgrade (`no translation for language en_CA`), which is
not an anomaly.

Provisioned menus are records, not templates, so nothing would translate them:
*Create the Captivea menus* writes the per-language values from the `.po` files
itself. A value that no longer matches the English source has been translated by
hand and is left alone. Panels are translated by *Reset the mega menu panels*,
since their content has to be rewritten for that.
