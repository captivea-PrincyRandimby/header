# Captivea snippets — blocks and use cases

The theme's snippets are grouped into **6 blocks** in the builder panel. The first five are declared
in [views/snippets.xml:694-700](cap_web_captivea_theme/views/snippets.xml#L694-L700), the sixth
(dynamic) in [views/customer_references_templates.xml:48](cap_web_captivea_theme/views/customer_references_templates.xml#L48).

| Block | Key (`group=`) | Snippets |
|---|---|---|
| Captivea — General | `cap_general` | 10 |
| Captivea — Sectors & Business functions | `cap_sectors` | 11 |
| Captivea — Product & Odoo | `cap_product` | 18 |
| Captivea — Company & Local | `cap_company` | 10 |
| Captivea — Offers & Case studies | `cap_offers` | 4 |
| Captivea Dynamic | `captivea_dynamic` | 4 |

**Total: 57 snippets** (53 static ones in the theme + 4 dynamic, two of which come from `cap_web_quote`).

The "Pages" column lists the template pages that use the snippet (compositions defined in
[tools/gen_pages.py:34-69](cap_web_captivea_theme/tools/gen_pages.py#L34-L69)).

---

## 1. Captivea — General (`cap_general`)

Structural sections, present on nearly every page.

| Snippet | Builder label | Use case | Pages |
|---|---|---|---|
| `s_cap_page_header` | Captivea: Page header | Opening hero: eyebrow capsule (editorial breadcrumb), H1, intro and a button to the form. **Always the first section of a page.** | All 17 |
| `s_cap_context` | Captivea: Context | Two framing paragraphs: the stakes of the subject, then Captivea's approach. Place it right after the hero to set context before the arguments. | 9 pages |
| `s_cap_solution` | Captivea: Solution | "Our solution" in 3 parts (h3): the answer being delivered, without cards. For explaining *how* the problem is solved. | About, ISV, Benefit, Case study |
| `s_cap_references` | Captivea: References | Strip of client logos for the sector (visual social proof, static). | 8 pages |
| `s_cap_testimonials` | Captivea: Testimonials | 3 testimonial cards **hardcoded in the page** (≠ the dynamic version, see block 6). | 8 pages |
| `s_cap_faq` | Captivea: FAQ | Question/answer accordion. The most reused SEO section of the theme (15 pages out of 17). | 15 pages |
| `s_cap_cta` | Captivea: CTA contact | Closing CTA **carrying the contact form** (`crm.lead`, `#form` anchor). Forced to be the last section of every page by the generator. | All 17 |
| `s_cap_mid_cta` | Captivea: Mid CTA | Mid-page CTA (title + button, no form), to capture intent before the bottom of a long page. | *none* |
| `s_cap_stats` | Captivea: Key figures | Key figures ("Captivea in numbers"): credibility through numbers. | About, Country, Product, Case study |
| `s_cap_methodology` | Captivea: Methodology | 4 project-phase cards + buttons: how a rollout unfolds, to reassure on delivery. | Home, Team, Product, Offer |

## 2. Captivea — Sectors & Business functions (`cap_sectors`)

The argument sections of sector / sub-sector / business-function pages.

| Snippet | Builder label | Use case | Pages |
|---|---|---|---|
| `s_cap_subsectors_index` | Captivea: Sub-sectors index | 6 sub-sector cards: internal linking from a sector hub down to its verticals. | Sub-sector, Sector |
| `s_cap_gains` | Captivea: What you gain | 9 cards split into 3 groups (h3): the concrete gains. The densest "benefits" section. | Sub-sector, Sector, Team, Partner |
| `s_cap_before_after` | Captivea: Before / After | 2 facing cards (before / after): make the pain and the outcome tangible. | Team |
| `s_cap_pain_points` | Captivea: Pain points | 5 cards of daily irritants: an empathetic hook near the top of a business-function page. | Team |
| `s_cap_key_features` | Captivea: Key features | 4 feature cards (no icons): the "what" of an app or an add-on. | App Odoo, Add-on, ISV |
| `s_cap_expertise` | Captivea: Expertise | 5 cards ERP · Web · AI · BI: show the integrated offer on a given subject. | Sub-sector, Sector, Team, Partner |
| `s_cap_sectors` | Captivea: Sectors | 5 sector cards + links: cross-navigation "by industry". | Home, Industries, App Odoo |
| `s_cap_teams` | Captivea: Teams / functions | 8 business-function cards + links: cross-navigation "by team". | Home, Industries, Sector, App Odoo, Case study |
| `s_cap_ai` | Captivea: AI use cases | Text block on the sector's AI use cases: a differentiator, without cards. | Sub-sector, Sector |
| `s_cap_blog` | Captivea: Blog teaser | 3 article cards **written by hand** (≠ the dynamic `s_cap_blog_posts`, block 6). | Sub-sector, Sector, Team, Country, Partner |
| `s_cap_related` | Captivea: Related links | "Go further" link list: internal linking at the bottom of a page. | Industries, Sub-sector, Sector, Team, Case study |

## 3. Captivea — Product & Odoo (`cap_product`)

Product pages, apps, ERP comparisons and software-vendor (ISV) pages. The largest block.

| Snippet | Builder label | Use case | Pages |
|---|---|---|---|
| `s_cap_definition` | Captivea: Definition | "What is X?": SEO definition at the top of a pillar page. | Product |
| `s_cap_why_odoo` | Captivea: Why Odoo | 3 "one unified ERP" cards: the generic Odoo argument. | Product, Comparison |
| `s_cap_hosting` | Captivea: Hosting | 3 hosting-option cards (Online / SH / On-premise). | Product |
| `s_cap_gold_partner` | Captivea: Gold Partner credibility | "Odoo Gold Partner" credibility banner (certification). | Partner, Product |
| `s_cap_comparison_teaser` | Captivea: Comparison teaser | "Odoo vs other ERPs" teaser + button: drive traffic to the comparison pages. | *none* |
| `s_cap_comparison_table` | Captivea: Comparison table | Comparison **table**, Odoo vs a named competitor. | Product, Comparison |
| `s_cap_erp_contenders` | Captivea: ERP contenders | 2 "who is who?" cards: introduce both compared ERPs on equal footing. | *none* |
| `s_cap_decision_criteria` | Captivea: Decision criteria | 3 parts, "the questions to ask yourself": guide the decision without selling. | *none* |
| `s_cap_comparison_verdict` | Captivea: Comparison verdict | Clear verdict + CTA: the conclusion of a comparison page. | *none* |
| `s_cap_more_comparisons` | Captivea: More comparisons | Links to the other comparisons: internal linking between "Odoo vs X" pages. | *none* |
| `s_cap_odoo_apps` | Captivea: Odoo apps | 8 cards of relevant Odoo apps + links: show functional coverage. | 7 pages |
| `s_cap_app_definition` | Captivea: App definition | Presentation of one specific Odoo app (name, role, scope). | App Odoo |
| `s_cap_use_cases` | Captivea: Use cases | 3 cards of concrete use cases for an app or an add-on. | App Odoo, Add-on |
| `s_cap_addon` | Captivea: Captivea add-on | Presentation of a Captivea module (what it brings, who it is for). | Add-on |
| `s_cap_isv_intro` | Captivea: ISV presentation | "Who is {Partner}?" with a visual: the opening of a third-party vendor page. | ISV |
| `s_cap_isv_benefits` | Captivea: ISV user benefits | 3 cards of end-user benefits of the integration. | ISV |
| `s_cap_isv_integration` | Captivea: ISV integration by Captivea | The integration Captivea builds between the third-party product and Odoo. | *none* |
| `s_cap_erp_compatibility` | Captivea: ERP compatibility | Compatibility **table** for Odoo versions / editions. | ISV |

## 4. Captivea — Company & Local (`cap_company`)

Corporate pages and geographic pages (country, office, market).

| Snippet | Builder label | Use case | Pages |
|---|---|---|---|
| `s_cap_story` | Captivea: Story | The company's story (long-form text). | Home, About |
| `s_cap_values` | Captivea: Values | 3 value cards: what guides every project. | About |
| `s_cap_conviction` | Captivea: Conviction | Positioning statement, short and wide declarative format. | About |
| `s_cap_leadership` | Captivea: Leadership | 4 leadership cards: put faces to the company. | About |
| `s_cap_country_presence` | Captivea: Country presence | 4 cards of international presence: "one team, wherever you are". | About |
| `s_cap_offices` | Captivea: Offices | 4 office cards: geographic proximity, local SEO. | Home, Country |
| `s_cap_coverage` | Captivea: Coverage areas | Areas served (icon list): local SEO on cities/regions. | Country, Office, Partner |
| `s_cap_market_spotlight` | Captivea: Market spotlight | Spotlight on a market / country: the local context of a geographic page. | Home, Country, Office |
| `s_cap_leader_odoo` | Captivea: Odoo leader argument | "The worldwide leader in Odoo integration": authority argument, homepage. | Home |
| `s_cap_services` | Captivea: Services | 5 cards of delivered services: the offer in one screen. | Home, Country, Office, Partner |

## 5. Captivea — Offers & Case studies (`cap_offers`)

| Snippet | Builder label | Use case | Pages |
|---|---|---|---|
| `s_cap_offer_detail` | Captivea: Offer detail | Detail of a packaged offer (contents, scope, deliverables). | Offer |
| `s_cap_benefit_positioning` | Captivea: Benefit positioning | The customer benefit stated in one strong sentence: the opening of a benefit page. | Benefit |
| `s_cap_case_context` | Captivea: Client context | The client of a case study: who they are, their challenge. | Case study |
| `s_cap_timeline` | Captivea: Project timeline | 3 milestone cards: how the project unfolded, chronologically. | Case study |

## 6. Captivea Dynamic (`captivea_dynamic`)

Snippets **fed from the database** (no content typed into the page): they update themselves whenever
the records change.

| Snippet | Builder label | Data source | Use case |
|---|---|---|---|
| `s_customer_references` | Customer References | Published `res.partner` records with `assigned_partner_id` set, sorted by `complete_name`, limit 16 ([data/customer_references_filter.xml](cap_web_captivea_theme/data/customer_references_filter.xml)) | Grid of real customer references, with tag filtering and a link to `/customers`. Prefer it over `s_cap_references` (static) as soon as the partners are entered in Odoo. |
| `s_cap_blog_posts` | Captivea Blog Posts | `blog.post` (snippet filter), link to `/blog` | Latest articles, with tag filtering available from the builder. Prefer it over `s_cap_blog` (static). |
| `s_captivea_testimonials` | Testimonials | `quote.testimonial` (`cap_web_quote` module) | Carousel of testimonials managed in the back office. Prefer it over `s_cap_testimonials` (static). |
| `s_cap_client_quote` | Captivea: Client quote | Published `quote.testimonial` (the first one by `sequence`), selectable in the builder | One highlighted customer quote in the middle of a page. Used by the Team, About and Case study pages. |

---

## Things to know

**Static vs dynamic.** Three pairs overlap functionally: `s_cap_references` /
`s_customer_references`, `s_cap_testimonials` / `s_captivea_testimonials`, `s_cap_blog` /
`s_cap_blog_posts`. The *General* / *Sectors* versions carry hardcoded content (handy for
mock-ups); the *Dynamic* ones read the database (use these in production).

**7 snippets are not used by any generated page**: `s_cap_mid_cta`, `s_cap_comparison_teaser`,
`s_cap_erp_contenders`, `s_cap_decision_criteria`, `s_cap_comparison_verdict`,
`s_cap_more_comparisons`, `s_cap_isv_integration`. They remain available to drop by hand in the
builder. The four comparison snippets belong to the `/template-comparison-cms` page, which exists in
`data/pages.xml` but **no longer in `tools/gen_pages.py`**: the generator has drifted from the file it
generates, so re-running it as-is would delete that page.

**Cross-module coupling.** The `captivea_dynamic` group is declared by the theme, yet
`cap_web_quote` puts its two snippets in it without depending on the theme in its manifest: installed
on its own, its snippets point at a group that does not exist.

**The contact form lives in `s_cap_cta`.** Any form fix (see [error.md](error.md)) goes through that
snippet, i.e. through `views/snippets.xml`, then a regeneration of `data/pages.xml`.
