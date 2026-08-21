# Customer benefits by sector × expertise

Source dataset for generating page content: **144 customer benefits** = 4 sectors × 6 expertises ×
6 benefits. Each benefit is a short, action-oriented promise written from the customer's point of
view, plus a **relevance score** telling how sector-specific it is.

Use this file as the vocabulary for any page that has to say *what the customer gains*: sector pages,
sub-sector pages, business-function pages and partner pages. Do not invent new benefit lines while
an unused one exists for that sector × expertise pair.

---

## 1. Taxonomy

### Sectors

| Code | Sector (EN) | Original label (FR) |
|---|---|---|
| `SVC` | Services & Professional Services | Services & tertiaire |
| `IND` | Industry & Manufacturing | Industrie & Manufacturing |
| `DIS` | Distribution & Logistics | Distribution & logistique |
| `RET` | Retail & Point of Sale | Retail & Point de vente |

### Expertises

| Code | Expertise | Original label (FR) |
|---|---|---|
| `BC` | Business Consulting | Business Consulting |
| `ERP` | ERP / Odoo | ERP / Odoo |
| `WEB` | Web Agency | Web Agency |
| `MKT` | Marketing | Marketing |
| `AI` | Artificial Intelligence | Artificial Intelligence |
| `BI` | Business Intelligence | Business Intelligence |

### Relevance score

| Score | Label | Meaning | How to use it |
|---|---|---|---|
| **3** | Sector-dedicated | Only makes sense for this sector; names its own vocabulary (OEE, BOM, click & collect, shrinkage). | **First choice** on a sector or sub-sector page. This is what makes the page rank and convert. |
| **2** | Adapted | Generic promise re-worded for this sector. | Filler once the score-3 lines are used, or for a business-function page. |
| **1** | Generalist | True for any company, interchangeable between sectors. | **Last resort.** Never open a section with one; two on the same page already reads as filler. |

### Coverage per sector

| Sector | Score 3 | Score 2 | Score 1 | Total |
|---|---|---|---|---|
| `SVC` Services | 16 | 14 | 6 | 36 |
| `IND` Industry | 23 | 8 | 5 | 36 |
| `DIS` Distribution | 24 | 10 | 2 | 36 |
| `RET` Retail | 25 | 11 | 0 | 36 |
| **All** | **88** | **43** | **13** | **144** |

`SVC` is the weakest sector in the dataset (16 dedicated lines only, 6 generalist): a Services page
written from this data will need more original copy than a Retail page.

---

## 2. How this data maps to the theme

| Where | Snippet | What it consumes |
|---|---|---|
| Sector, Sub-sector, Team, Partner pages | [`s_cap_expertise`](snippets-2.md) | **1 description per expertise card**, built from the benefits of that sector × expertise pair. |
| Sector, Sub-sector, Team, Partner pages | [`s_cap_gains`](snippets-2.md) | **9 benefits** = 3 audiences (your company / your teams / your customers) × 3 cards, each with a title + a sentence. |
| Benefit page | [`s_cap_benefit_positioning`](snippets-2.md) | **1 benefit** promoted to the page's H1, plus its audience and outcome. |

**Watch out — 6 expertises here, 5 cards in the snippet.** `s_cap_expertise` ships five hardcoded
cards: *Business Consulting*, *ERP*, *Web & Marketing*, *Artificial Intelligence*,
*Business Intelligence*. `WEB` and `MKT` therefore have to be **merged into the single
"Web & Marketing" card**, or a sixth card must be added to the snippet. Pick the merge unless the
snippet is changed.

**Selection rules when filling a page**

1. One benefit is used **once per page**. Repeating a line across two sections wastes it.
2. Order by score: all the score-3 lines first, then score 2, then score 1.
3. For `s_cap_gains`, spread the 9 picks across the three audiences — company benefits tend to come
   from `BC`/`BI`, team benefits from `ERP`/`AI`, customer benefits from `WEB`/`MKT`.
4. The benefit text below is the **title** (3-7 words, imperative, addressed as "your"). The
   supporting sentence is to be written from it, never copied from another sector.
5. Keep the imperative + "your" pattern when writing new lines: *Optimize your…*, *Track your…*,
   *Anticipate…*. No superlatives, no "best-in-class", no vendor name except Odoo.

---

## 3. `SVC` — Services & Professional Services

### `SVC-BC` Business Consulting

| ID | Customer benefit | Score |
|---|---|---|
| `SVC-BC-1` | Optimize the profitability of your engagements | 3 |
| `SVC-BC-2` | Structure your delivery processes | 3 |
| `SVC-BC-3` | Speed up your decision-making | 2 |
| `SVC-BC-4` | Anticipate your budget-overrun risks | 3 |
| `SVC-BC-5` | Improve your client satisfaction | 2 |
| `SVC-BC-6` | Standardize your project methodologies | 2 |

### `SVC-ERP` ERP / Odoo

| ID | Customer benefit | Score |
|---|---|---|
| `SVC-ERP-1` | Centralize your tools in Odoo | 3 |
| `SVC-ERP-2` | Automate your rebilling | 3 |
| `SVC-ERP-3` | Track your margin per engagement | 3 |
| `SVC-ERP-4` | Simplify timesheet entry | 3 |
| `SVC-ERP-5` | Streamline your client invoicing | 3 |
| `SVC-ERP-6` | Gain autonomy over your tools | 2 |

### `SVC-WEB` Web Agency

| ID | Customer benefit | Score |
|---|---|---|
| `SVC-WEB-1` | Showcase your expertise online | 2 |
| `SVC-WEB-2` | Generate qualified leads | 1 |
| `SVC-WEB-3` | Convert more visitors | 1 |
| `SVC-WEB-4` | Strengthen your online credibility | 2 |
| `SVC-WEB-5` | Improve your organic search ranking | 1 |
| `SVC-WEB-6` | Modernize your showcase website | 1 |

### `SVC-MKT` Marketing

| ID | Customer benefit | Score |
|---|---|---|
| `SVC-MKT-1` | Attract qualified prospects | 1 |
| `SVC-MKT-2` | Automate your campaigns | 2 |
| `SVC-MKT-3` | Measure your marketing ROI | 2 |
| `SVC-MKT-4` | Grow your brand awareness | 1 |
| `SVC-MKT-5` | Segment your B2B audiences | 2 |
| `SVC-MKT-6` | Optimize your advertising budgets | 2 |

### `SVC-AI` Artificial Intelligence

| ID | Customer benefit | Score |
|---|---|---|
| `SVC-AI-1` | Eliminate duplicate data entry | 3 |
| `SVC-AI-2` | Automate your repetitive tasks | 2 |
| `SVC-AI-3` | Increase your productivity | 2 |
| `SVC-AI-4` | Make your deliverables more reliable with AI | 3 |
| `SVC-AI-5` | Speed up the writing of your reports | 3 |
| `SVC-AI-6` | Detect your invoicing anomalies | 3 |

### `SVC-BI` Business Intelligence

| ID | Customer benefit | Score |
|---|---|---|
| `SVC-BI-1` | Visualize your margins live | 3 |
| `SVC-BI-2` | Make your decisions more reliable | 2 |
| `SVC-BI-3` | Anticipate your resourcing needs | 3 |
| `SVC-BI-4` | Track profitability per consultant | 3 |
| `SVC-BI-5` | Consolidate your multi-site KPIs | 3 |
| `SVC-BI-6` | Share real-time dashboards | 2 |

---

## 4. `IND` — Industry & Manufacturing

### `IND-BC` Business Consulting

| ID | Customer benefit | Score |
|---|---|---|
| `IND-BC-1` | Structure your production flows | 3 |
| `IND-BC-2` | Make your cost prices reliable | 3 |
| `IND-BC-3` | Frame your industrial transformation | 2 |
| `IND-BC-4` | De-risk your production ramp-up | 3 |
| `IND-BC-5` | Optimize your plant layout | 3 |
| `IND-BC-6` | Strengthen your continuous-improvement culture | 2 |

### `IND-ERP` ERP / Odoo

| ID | Customer benefit | Score |
|---|---|---|
| `IND-ERP-1` | Schedule your shop floor in real time | 3 |
| `IND-ERP-2` | Trace your production lots | 3 |
| `IND-ERP-3` | Track your margin per product | 2 |
| `IND-ERP-4` | Manage your multi-level bills of materials | 3 |
| `IND-ERP-5` | Automate your manufacturing orders | 3 |
| `IND-ERP-6` | Synchronize purchasing and production | 3 |

### `IND-WEB` Web Agency

| ID | Customer benefit | Score |
|---|---|---|
| `IND-WEB-1` | Digitalize your order intake | 2 |
| `IND-WEB-2` | Showcase your industrial know-how | 3 |
| `IND-WEB-3` | Connect your supplier portal | 1 |
| `IND-WEB-4` | Publish your technical catalogue online | 2 |
| `IND-WEB-5` | Highlight your quality certifications | 3 |
| `IND-WEB-6` | Simplify your online quote requests | 1 |

### `IND-MKT` Marketing

| ID | Customer benefit | Score |
|---|---|---|
| `IND-MKT-1` | Open up new markets | 1 |
| `IND-MKT-2` | Promote your quality certifications | 3 |
| `IND-MKT-3` | Generate qualified B2B leads | 1 |
| `IND-MKT-4` | Strengthen your industrial brand image | 2 |
| `IND-MKT-5` | Target your international prospects | 1 |
| `IND-MKT-6` | Showcase your customer references | 2 |

### `IND-AI` Artificial Intelligence

| ID | Customer benefit | Score |
|---|---|---|
| `IND-AI-1` | Optimize your planning (MRP) | 3 |
| `IND-AI-2` | Anticipate your machine breakdowns | 3 |
| `IND-AI-3` | Reduce your quality scrap | 3 |
| `IND-AI-4` | Automate your visual quality controls | 3 |
| `IND-AI-5` | Optimize your energy consumption | 3 |
| `IND-AI-6` | Forecast your raw-material needs | 3 |

### `IND-BI` Business Intelligence

| ID | Customer benefit | Score |
|---|---|---|
| `IND-BI-1` | Visualize your OEE live | 3 |
| `IND-BI-2` | Track your cost prices | 3 |
| `IND-BI-3` | Monitor your delivery lead times | 2 |
| `IND-BI-4` | Analyze your machine downtime | 3 |
| `IND-BI-5` | Compare your performance line by line | 3 |
| `IND-BI-6` | Track your scrap rate | 3 |

---

## 5. `DIS` — Distribution & Logistics

### `DIS-BC` Business Consulting

| ID | Customer benefit | Score |
|---|---|---|
| `DIS-BC-1` | Optimize your logistics flows | 3 |
| `DIS-BC-2` | Make your service levels reliable | 3 |
| `DIS-BC-3` | Structure your multichannel strategy | 2 |
| `DIS-BC-4` | Rationalize your warehouse network | 3 |
| `DIS-BC-5` | Reduce your transport costs | 3 |
| `DIS-BC-6` | Frame your digital transformation plan | 2 |

### `DIS-ERP` ERP / Odoo

| ID | Customer benefit | Score |
|---|---|---|
| `DIS-ERP-1` | Synchronize your multichannel stock | 3 |
| `DIS-ERP-2` | Automate your order picking | 3 |
| `DIS-ERP-3` | Track your logistics costs | 2 |
| `DIS-ERP-4` | Optimize your warehouse locations | 3 |
| `DIS-ERP-5` | Automate your carrier invoicing | 3 |
| `DIS-ERP-6` | Handle your returns more simply | 2 |

### `DIS-WEB` Web Agency

| ID | Customer benefit | Score |
|---|---|---|
| `DIS-WEB-1` | Boost your e-commerce sales | 3 |
| `DIS-WEB-2` | Connect your marketplaces | 3 |
| `DIS-WEB-3` | Let your customers track parcels online | 2 |
| `DIS-WEB-4` | Optimize your checkout funnel | 3 |
| `DIS-WEB-5` | Synchronize your product catalogues | 3 |
| `DIS-WEB-6` | Improve your online customer follow-up | 2 |

### `DIS-MKT` Marketing

| ID | Customer benefit | Score |
|---|---|---|
| `DIS-MKT-1` | Grow your multichannel audience | 2 |
| `DIS-MKT-2` | Build loyalty with your e-commerce customers | 2 |
| `DIS-MKT-3` | Generate qualified traffic | 1 |
| `DIS-MKT-4` | Automate your abandoned-cart reminders | 3 |
| `DIS-MKT-5` | Segment your campaigns by channel | 2 |
| `DIS-MKT-6` | Grow your online B2B sales | 1 |

### `DIS-AI` Artificial Intelligence

| ID | Customer benefit | Score |
|---|---|---|
| `DIS-AI-1` | Forecast your demand | 3 |
| `DIS-AI-2` | Optimize your delivery routes | 3 |
| `DIS-AI-3` | Reduce your stock-outs | 3 |
| `DIS-AI-4` | Optimize the load rate of your trucks | 3 |
| `DIS-AI-5` | Automate your parcel sorting | 3 |
| `DIS-AI-6` | Prevent your overstock risks | 3 |

### `DIS-BI` Business Intelligence

| ID | Customer benefit | Score |
|---|---|---|
| `DIS-BI-1` | Visualize your service levels | 3 |
| `DIS-BI-2` | Track your delivery lead times | 3 |
| `DIS-BI-3` | Monitor your cost per parcel | 3 |
| `DIS-BI-4` | Analyze your fill rate | 3 |
| `DIS-BI-5` | Compare your performance per warehouse | 3 |
| `DIS-BI-6` | Track your return rate | 2 |

---

## 6. `RET` — Retail & Point of Sale

### `RET-BC` Business Consulting

| ID | Customer benefit | Score |
|---|---|---|
| `RET-BC-1` | Harmonize your store network | 3 |
| `RET-BC-2` | Optimize your shopping experience | 3 |
| `RET-BC-3` | Structure your omnichannel strategy | 2 |
| `RET-BC-4` | Standardize your in-store processes | 3 |
| `RET-BC-5` | Optimize your shelf layout | 3 |
| `RET-BC-6` | Strengthen the training of your sales teams | 2 |

### `RET-ERP` ERP / Odoo

| ID | Customer benefit | Score |
|---|---|---|
| `RET-ERP-1` | Unify checkout and stock (Odoo POS) | 3 |
| `RET-ERP-2` | Synchronize your stores in real time | 3 |
| `RET-ERP-3` | Track your margin per store | 2 |
| `RET-ERP-4` | Automate your store replenishment | 3 |
| `RET-ERP-5` | Run your loyalty programs | 3 |
| `RET-ERP-6` | Centralize your multi-brand data | 2 |

### `RET-WEB` Web Agency

| ID | Customer benefit | Score |
|---|---|---|
| `RET-WEB-1` | Grow your click & collect | 3 |
| `RET-WEB-2` | Connect your store and your e-commerce | 3 |
| `RET-WEB-3` | Showcase your storefronts online | 2 |
| `RET-WEB-4` | Optimize your mobile experience | 3 |
| `RET-WEB-5` | Promote your points of sale online | 3 |
| `RET-WEB-6` | Improve your in-store appointment booking | 2 |

### `RET-MKT` Marketing

| ID | Customer benefit | Score |
|---|---|---|
| `RET-MKT-1` | Build loyalty with your in-store customers | 3 |
| `RET-MKT-2` | Run your local promotions | 2 |
| `RET-MKT-3` | Drive footfall to your stores | 3 |
| `RET-MKT-4` | Personalize your offers by segment | 2 |
| `RET-MKT-5` | Run your local social media | 2 |
| `RET-MKT-6` | Measure the impact of your local campaigns | 3 |

### `RET-AI` Artificial Intelligence

| ID | Customer benefit | Score |
|---|---|---|
| `RET-AI-1` | Forecast your sales per store | 3 |
| `RET-AI-2` | Optimize your replenishment | 3 |
| `RET-AI-3` | Personalize your recommendations | 2 |
| `RET-AI-4` | Detect your shrinkage | 3 |
| `RET-AI-5` | Optimize your prices in real time | 3 |
| `RET-AI-6` | Forecast your store footfall | 2 |

### `RET-BI` Business Intelligence

| ID | Customer benefit | Score |
|---|---|---|
| `RET-BI-1` | Visualize your sales per point of sale | 3 |
| `RET-BI-2` | Track your average basket | 3 |
| `RET-BI-3` | Steer your network performance | 3 |
| `RET-BI-4` | Compare performance across your stores | 3 |
| `RET-BI-5` | Analyze your in-store conversion rate | 3 |
| `RET-BI-6` | Track your revenue per square meter | 3 |

---

## 7. Worked example

Target: the **Sector page for Industry & Manufacturing**.

`s_cap_expertise` — one description per card, built from the score-3 lines of that sector:

| Card | Benefits used | Description to write |
|---|---|---|
| Business Consulting | `IND-BC-1`, `IND-BC-2`, `IND-BC-4` | Structure your production flows, make your cost prices reliable and de-risk your ramp-up. |
| ERP | `IND-ERP-1`, `IND-ERP-2`, `IND-ERP-4` | Real-time shop-floor scheduling, lot traceability and multi-level bills of materials in Odoo. |
| Web & Marketing | `IND-WEB-2`, `IND-WEB-5`, `IND-MKT-2` | Showcase your industrial know-how and your quality certifications where your buyers look. |
| Artificial Intelligence | `IND-AI-2`, `IND-AI-3`, `IND-AI-1` | Anticipate breakdowns, cut quality scrap and optimize your MRP planning. |
| Business Intelligence | `IND-BI-1`, `IND-BI-4`, `IND-BI-5` | Live OEE, machine downtime and line-by-line performance in one dashboard. |

`s_cap_gains` — 9 remaining benefits spread across the three audiences:

- **Your company**: `IND-BC-5`, `IND-BI-2`, `IND-BC-3`
- **Your teams**: `IND-ERP-5`, `IND-ERP-6`, `IND-AI-4`
- **Your customers**: `IND-BI-3`, `IND-WEB-1`, `IND-WEB-4`

No benefit is used twice, and the two generalist lines (`IND-WEB-3`, `IND-MKT-1`) stay unused.
