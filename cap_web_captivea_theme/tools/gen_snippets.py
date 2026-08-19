# -*- coding: utf-8 -*-
# Authoritative Captivea snippet generator (v3).
# Includes: accordion FAQ (schema.org), Odoo apps family cards, and the v2 rules:
#  - every card has a card-footer link (href="#" by default; real v4 URLs for
#    industries / expertises / metiers sections)
#  - CTA links point to #form
#  - a dedicated contact-form section (s_cap_form) owns the #form anchor
import os
_HERE=os.path.dirname(os.path.abspath(__file__))
_BASE=os.path.abspath(os.path.join(_HERE,".."))
OUT=os.path.join(_BASE,"views","snippets.xml")

CTA = "Learn more →"

# ---- Lucide inline-SVG icons (served via the theme sprite) --------------------
# FA -> Lucide map + sprite are produced by tools/build_lucide_sprite.py.
try:
    from lucide_map import FA2LU, SVGS
except Exception:
    FA2LU, SVGS = {}, {}
# Extra FA -> Lucide mappings used by some sections (not in the base sprite map).
FA2LU.update({
    "fa-layer-group": "layers", "fa-arrow-trend-up": "chart-line",
    "fa-bullseye": "target", "fa-eye": "eye", "fa-heart": "heart",
})
def licon(fa, extra=""):
    name = FA2LU.get(fa, "circle-help")
    inner = SVGS.get(name, SVGS.get("circle-help", ""))
    cls = "o_lucide_icon o_editable_media" + ((" "+extra) if extra else "")
    # Inline SVG (reliable currentColor + hover). Kept as editable/replaceable media
    # (no contenteditable lock) so the icon can be changed again via the picker.
    return ('<span class="'+cls+'">'
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+inner+'</svg></span>')

# The CTA+form section (model crm.lead) is kept verbatim in tools/_cta_form.html.
CTA_FORM = open(os.path.join(_HERE,"_cta_form.html"), encoding="utf-8").read().strip()

def icard(col, icon, title, desc, href="#", cta=CTA, btn=False):
    # btn=True -> render the footer link as a two-line btn-secondary button;
    # `cta` is then used as raw inner HTML (may contain <small>/<br/>).
    link_cls = "o_translate_inline btn btn-secondary" if btn else "o_translate_inline"
    return ('<div class="o_colored_level '+col+' pt8 pb8 d-flex">'
      '<div class="s_card card o_cc o_cc1 o_colored_level w-100" data-snippet="s_card" data-name="Card">'
      '<div class="card-body">'+licon(icon)+
      '<h3 class="card-title h5-fs">'+title+'</h3><p class="card-text">'+desc+'</p></div>'
      '<div class="card-footer border-0 bg-transparent pt-0"><a href="'+href+'" class="'+link_cls+'">'+cta+'</a></div>'
      '</div></div>')

def head(eb, h2, lead=None):
    s='<div class="o_colored_level col-lg-12 text-center pt8 pb8"><p class="lead">'+eb+'</p><h2>'+h2+'</h2>'
    if lead: s+='<p class="lead">'+lead+'</p>'
    return s+'</div>'

def tpl(sid, name, inner, oc="o_cc1", band="", pad="pt32 pb32", base="s_text_image", secid=""):
    # Rules: never emit cap-band-* ; always add the snippet id (e.g. s_cap_cta) as a class.
    ida=' id="'+secid+'"' if secid else ''
    return ('<template id="'+sid+'" name="Captivea: '+name+'">\n'
      '    <section'+ida+' class="'+base+' '+sid+' o_cc '+oc+' o_colored_level '+pad+'" data-snippet="'+sid+'" data-name="Captivea '+name+'">\n'
      '        <div class="container"><div class="row align-items-stretch">\n            '+inner+'\n        </div></div>\n'
      '    </section>\n</template>')

def text_block(intro, h2, body, off=True):
    col='offset-lg-1 col-lg-10' if off else 'col-lg-8 offset-lg-2 text-center'
    return '<div class="o_colored_level '+col+' pt8 pb8"><p class="lead">'+intro+'</p><h2>'+h2+'</h2>'+body+'</div>'

# ---- accordion FAQ (Odoo s_accordion + schema.org microdata) ----
_FAQ_Q={1: 'What is Odoo?', 2: 'Is Odoo free?', 3: 'What are the hosting options?', 4: 'Why work with a Gold Partner?'}
_FAQ_A={1: 'Odoo is an open-source, modular ERP bringing together CRM, sales, accounting, inventory, manufacturing, HR, marketing and a website in a single platform.', 2: 'Odoo offers a free open-source Community edition, plus paid Enterprise and Odoo.sh editions; Captivea helps you choose the right one.', 3: 'Three options: Odoo Online (SaaS), Odoo.sh (cloud platform for custom code) and On-Premise on your own servers.', 4: 'With a Gold Partner like Captivea you get certified teams, a proven methodology and full support, protecting your timeline, budget and adoption.'}
def _fq(n):
    return (' — e.g. '+_FAQ_Q[n]) if n in _FAQ_Q else ''
def _fa(n):
    return (' — e.g. '+_FAQ_A[n]) if n in _FAQ_A else ''
def faq_item(n, first=False):
    show=" show" if first else ""
    coll="" if first else " collapsed"
    exp="true" if first else "false"
    return ('<div class="accordion-item position-relative z-1" data-name="Accordion Item" '
      'itemscope="itemscope" itemprop="mainEntity" itemtype="https://schema.org/Question">'
      '<button type="button" class="accordion-header accordion-button'+coll+' justify-content-between gap-2 bg-transparent h6-fs fw-bold text-decoration-none text-reset transition-none" '
      'data-bs-toggle="collapse" aria-expanded="'+exp+'" id="capFaqBtn'+str(n)+'" data-bs-target="#capFaqTab'+str(n)+'" aria-controls="capFaqTab'+str(n)+'">'
      '<span class="flex-grow-1" itemprop="name">{Question '+str(n)+_fq(n)+'}</span></button>'
      '<div class="accordion-collapse collapse'+show+'" data-bs-parent="#capFaq" role="region" id="capFaqTab'+str(n)+'" aria-labelledby="capFaqBtn'+str(n)+'" '
      'itemscope="itemscope" itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">'
      '<div class="accordion-body" itemprop="text"><p>{Answer '+str(n)+_fa(n)+'}</p></div></div></div>')

def faq_inner():
    acc=('<div data-name="Accordion" data-snippet="s_accordion" class="s_accordion">'
         '<div id="capFaq" class="accordion" itemscope="itemscope" itemtype="https://schema.org/FAQPage">'
         +faq_item(1,True)+faq_item(2)+faq_item(3)+faq_item(4)+'</div></div>')
    return (head("FAQ","Frequently asked questions")
            +'<div class="o_colored_level offset-lg-1 col-lg-10 pt8 pb8">'+acc+'</div>')

T=[]  # (group, xml)
G_GEN, G_SEC, G_PROD, G_COMP, G_OFF = "cap_general","cap_sectors","cap_product","cap_company","cap_offers"

# ===================== GENERAL =====================
T.append((G_GEN, '<template id="s_cap_page_header" name="Captivea: Page header">\n'
 '    <section class="s_cover s_cap_page_header o_cc o_cc3 o_colored_level pt64 pb72 cap-s-pageheader" data-snippet="s_cap_page_header" data-name="Captivea Page header">\n'
 '        <div class="s_allow_columns container"><div class="row"><div class="o_colored_level offset-lg-1 col-lg-7">'
 '<p class="lead">By industry · {Industry name}</p><h1>{Page Title}</h1>'
 '<p class="lead">{Intro paragraph: frame the industry and the value Captivea brings.}</p>'
 '<p><a href="#form" class="btn btn-primary o_translate_inline">Let\'s speak about your project</a></p>'
 '</div></div></div>\n    </section>\n</template>'))
T.append((G_GEN, tpl("s_cap_context","Context",
  '<div class="o_colored_level offset-lg-1 col-lg-10 pt8 pb8"><p class="lead">Context</p>'
  '<h2>{Context title — e.g. An American Odoo partner, rooted in local markets}</h2>'
  '<p>{Context paragraph 1 — e.g. Captivea supports SMBs, mid-market and enterprise groups in digitalizing their operations with Odoo. Our difference: an organization by industry vertical and a regional presence, combining the proximity of a local partner with the power of an international network.}</p>'
  '<p>{Context paragraph 2 — e.g. From strategic scoping to post-go-live support, our consultants, business analysts and developers cover the full project lifecycle: ERP, website and e-commerce, Business Intelligence and artificial intelligence.}</p></div>')))
T.append((G_GEN, tpl("s_cap_solution","Solution",
  '<div class="o_colored_level offset-lg-1 col-lg-10 pt8 pb8"><p class="lead">Our solution</p>'
  '<h2>{Solution title — e.g. A unified Odoo foundation, enhanced by BI and AI}</h2><p>{How Captivea solves it, benefit-first — e.g. Captivea deploys Odoo as the single system connecting manufacturing, purchasing, inventory and accounting, with BI dashboards and an AI demand-forecasting module for accurate planning.}</p></div>')))
T.append((G_GEN, tpl("s_cap_references","References",
  head("References","Companies in {Industry — e.g. manufacturing} that trust Captivea")+
  '<div class="o_colored_level col-6 col-md-3 text-center pt8 pb8"><img src="/web/image/website.s_references_default_image_1" class="img img-fluid mx-auto" alt="{Client name}"/></div>'
  '<div class="o_colored_level col-6 col-md-3 text-center pt8 pb8"><img src="/web/image/website.s_references_default_image_2" class="img img-fluid mx-auto" alt="{Client name}"/></div>'
  '<div class="o_colored_level col-6 col-md-3 text-center pt8 pb8"><img src="/web/image/website.s_references_default_image_3" class="img img-fluid mx-auto" alt="{Client name}"/></div>'
  '<div class="o_colored_level col-6 col-md-3 text-center pt8 pb8"><img src="/web/image/website.s_references_default_image_4" class="img img-fluid mx-auto" alt="{Client name}"/></div>',
  oc="o_cc1", base="s_references")))
T.append((G_GEN, tpl("s_cap_testimonials","Testimonials",
  head("Testimonials","What our clients say")+
  icard("col-lg-4","fa-quote-left","","{Client quote 1} — {Author}, {Role} at {Company}").replace('<h3 class="card-title h5-fs"></h3>','')+
  icard("col-lg-4","fa-quote-left","","{Client quote 2} — {Author}, {Role} at {Company}").replace('<h3 class="card-title h5-fs"></h3>','')+
  icard("col-lg-4","fa-quote-left","","{Client quote 3} — {Author}, {Role} at {Company}").replace('<h3 class="card-title h5-fs"></h3>',''),
  oc="o_cc2")))
T.append((G_GEN, tpl("s_cap_faq","FAQ", faq_inner(), base="s_faq_list")))
# CTA + contact form (model crm.lead). Mandatory final section on every page, owns #form.
T.append((G_GEN, '<template id="s_cap_cta" name="Captivea: CTA contact">\n    '+CTA_FORM+'\n</template>'))
T.append((G_GEN, tpl("s_cap_stats","Key figures",
  head("Key figures","Captivea in numbers")+
  '<div class="o_colored_level col-6 col-lg-3 text-center pt8 pb8"><h2 class="display-3">{N1 — e.g. 18+}</h2><p class="lead">{Label 1 — e.g. years of expertise}</p></div>'
  '<div class="o_colored_level col-6 col-lg-3 text-center pt8 pb8"><h2 class="display-3">{N2 — e.g. 12}</h2><p class="lead">{Label 2 — e.g. countries and offices}</p></div>'
  '<div class="o_colored_level col-6 col-lg-3 text-center pt8 pb8"><h2 class="display-3">{N3 — e.g. 250}</h2><p class="lead">{Label 3 — e.g. talented professionals}</p></div>'
  '<div class="o_colored_level col-6 col-lg-3 text-center pt8 pb8"><h2 class="display-3">{N4 — e.g. 800+}</h2><p class="lead">{Label 4 — e.g. clients served}</p></div>',
  oc="o_cc2")))
# Methodology: 4 steps (2x2), icons search / configure / launch / target, + a CTA.
def _method_card(icon, title, text):
    return ('<div class="o_colored_level col-lg-6 pt8 pb8 d-flex"><div class="s_card card o_cc o_cc1 o_colored_level w-100" data-snippet="s_card" data-name="Card"><div class="card-body">'
            +licon(icon)+'<h3 class="card-title h5-fs">'+title+'</h3><p class="card-text">'+text+'</p></div></div></div>')
T.append((G_GEN, tpl("s_cap_methodology","Methodology",
  '<div class="o_colored_level col-lg-12 text-center pt8 pb8"><p class="lead">How it works</p>'
  '<h2>{A phased deployment, designed for adoption}</h2>'
  '<p>{The success of a project depends less on technology than on team adoption. Our method limits risk through short iterations.}</p></div>'
  +_method_card("fa-magnifying-glass","1. {Step — e.g. Mapping your process}","{What happens in this step. e.g. We map your current process and pain points before touching the tool.}")
  +_method_card("fa-screwdriver-wrench","2. {Step — e.g. Configuration and automation}","{What happens in this step. e.g. Pipeline, fields, follow-ups, quotes and e-signatures are configured to match your practices.}")
  +_method_card("fa-rocket","3. {Step — e.g. Training and change management}","{What happens in this step. e.g. Your teams are trained on their own real-world cases. The tool becomes second nature.}")
  +_method_card("fa-bullseye","4. {Step — e.g. Data-driven steering}","{What happens in this step. e.g. BI dashboards measure the gains and guide continuous optimizations.}")
  +'<div class="o_colored_level col-lg-12 text-center pt8 pb8"><a href="#" class="btn btn-lg btn-primary o_translate_inline">Discover our project methodology to transform your everyday</a></div>')))

# ===================== SECTORS & METIERS =====================
T.append((G_SEC, tpl("s_cap_subsectors_index","Sub-sectors index",
  head("Sub-sectors","Expertise in every vertical")+
  icard("col-6 col-lg-4","fa-folder-open","{Sub-sector 1 — e.g. Automotive}","{Short line about this sub-sector — e.g. Dedicated Odoo expertise, with the vocabulary and use cases of your vertical.}","#")+
  icard("col-6 col-lg-4","fa-folder-open","{Sub-sector 2 — e.g. Chemical}","{Short line about this sub-sector — e.g. Dedicated Odoo expertise, with the vocabulary and use cases of your vertical.}","#")+
  icard("col-6 col-lg-4","fa-folder-open","{Sub-sector 3 — e.g. Electronics}","{Short line about this sub-sector — e.g. Dedicated Odoo expertise, with the vocabulary and use cases of your vertical.}","#")+
  icard("col-6 col-lg-4","fa-folder-open","{Sub-sector 4 — e.g. Fashion and textile}","{Short line about this sub-sector — e.g. Dedicated Odoo expertise, with the vocabulary and use cases of your vertical.}","#")+
  icard("col-6 col-lg-4","fa-folder-open","{Sub-sector 5 — e.g. Construction}","{Short line about this sub-sector — e.g. Dedicated Odoo expertise, with the vocabulary and use cases of your vertical.}","#")+
  icard("col-6 col-lg-4","fa-folder-open","{Sub-sector 6 — e.g. Aerospace and defense}","{Short line about this sub-sector — e.g. Dedicated Odoo expertise, with the vocabulary and use cases of your vertical.}","#"))))
# What you gain: 3 audience columns (col-lg-4), each 3 cards
GAINS_COLS=[
 ("Your company","your company",[
   ("fa-chart-line","Reliable forecasts","Forecasting and sales dashboards in real time — no more manual reporting."),
   ("fa-handshake","Controlled pipeline","Full visibility on opportunities, margins, and conversion timelines."),
   ("fa-rocket","Accelerated growth","More deals closed thanks to a team focused on selling, not administration."),]),
 ("Your teams","your teams",[
   ("fa-layer-group","Unified tools","CRM, quotes, orders and invoicing in a single environment — zero double entry."),
   ("fa-robot","AI every day","Lead scoring, next best action and call summaries generated automatically."),
   ("fa-bullseye","Focus on selling","Less admin, more quality time with the leads that truly matter."),]),
 ("Your customers","your customers",[
   ("fa-eye","Transparent follow-up","Every customer can see the progress of their file, from request to delivery."),
   ("fa-bolt","Maximum responsiveness","Faster personalized offers, deadlines met, less waiting between exchanges."),
   ("fa-heart","Lasting relationship","A contact who is always informed, delivering a consistent experience at every interaction."),]),
]
def _gain_card(icon, title, text, aud):
    return ('<div class="s_card card o_cc o_cc1 o_colored_level" data-snippet="s_card" data-name="Card"><div class="card-body">'
            +licon(icon)+'<h4 class="card-title">{Benefit — e.g. '+title+'}</h4>'
            '<p class="card-text">{Concrete gain for '+aud+'. e.g. '+text+'}</p></div>'
            '<div class="card-footer border-0 bg-transparent pt-0"><a href="#" class="o_translate_inline">Learn more about {Benefit}</a></div></div>')
def _gain_col(label, aud, cards):
    return '<div class="o_colored_level col-lg-4 pt8 pb8"><h3>'+label+'</h3>'+''.join(_gain_card(i,t,x,aud) for i,t,x in cards)+'</div>'
T.append((G_SEC, tpl("s_cap_gains","What you gain",
  head("The concrete gains","What you gain")+''.join(_gain_col(l,a,c) for l,a,c in GAINS_COLS),
  oc="o_cc2")))
# Before / After: two cards, each with an icon, a title and a 3-item bullet list.
_ba_before="".join("<li>{The painful situation today.}</li>" for _ in range(3))
_ba_after="".join("<li>{The situation once transformed with Captivea.}</li>" for _ in range(3))
T.append((G_SEC, tpl("s_cap_before_after","Before / After",
  head("Before / After","From friction to flow")+
  '<div class="o_colored_level col-lg-6 pt8 pb8 d-flex"><div class="s_card card o_cc o_cc1 o_colored_level w-100" data-snippet="s_card" data-name="Card"><div class="card-body">'
  +licon("fa-circle-xmark")+'<h3 class="h5-fs">Before</h3><ul>'+_ba_before+'</ul></div></div></div>'
  '<div class="o_colored_level col-lg-6 pt8 pb8 d-flex"><div class="s_card card o_cc o_cc1 o_colored_level w-100" data-snippet="s_card" data-name="Card"><div class="card-body">'
  +licon("fa-circle-check")+'<h3 class="h5-fs">After</h3><ul>'+_ba_after+'</ul></div></div></div>',
  oc="o_cc2")))
# Pain points -> solution mapping: one full-width row per pain, an arrow, then
# the matching Captivea solution (Business Consulting / ERP / Web / AI / BI).
_pp_arrow=licon("fa-arrow-right","lucide-arrow-right m-auto")
def _pp_row(sol_title, sol_text):
    return ('<div class="o_colored_level col-lg-12 pt8 pb8 d-flex">'
            '<div class="s_card card o_cc o_cc1 o_colored_level w-100" data-snippet="s_card" data-name="Card"><div class="card-body">'
            '<div class="row align-items-center">'
            '<div class="o_colored_level col-5"><p class="card-title">{Painpoint}</p></div>'
            '<div class="o_colored_level col-2 text-center">'+_pp_arrow+'</div>'
            '<div class="o_colored_level col-5"><p><strong>'+sol_title+'</strong><br/>'+sol_text+'</p></div>'
            '</div></div></div></div>')
T.append((G_SEC, tpl("s_cap_pain_points","Pain points",
  head("Your daily irritants","What slows your {Team name} team down")+
  _pp_row("{Business Consulting Solution Title}","{Business Consulting Solution text}")+
  _pp_row("{ERP Solution Title}","{ERP Solution text}")+
  _pp_row("{Web &amp; Marketing Solution Title}","{Web &amp; marketing Solution text}")+
  _pp_row("{AI Solution Title}","{AI Solution text}")+
  _pp_row("{BI Solution Title}","{BI Solution text}"))))
T.append((G_SEC, tpl("s_cap_key_features","Key features",
  head("Key features","Concrete building blocks")+
  icard("col-6 col-lg-3","fa-circle-check","{Feature — e.g. Real-time inventory}","{What it does — e.g. Stock levels update automatically across every site.}")+
  icard("col-6 col-lg-3","fa-circle-check","{Feature — e.g. Automated invoicing}","{What it does — e.g. Invoices are generated and reconciled without manual re-entry.}")+
  icard("col-6 col-lg-3","fa-circle-check","{Feature — e.g. AI lead scoring}","{What it does — e.g. Opportunities are ranked so your team focuses on what converts.}")+
  icard("col-6 col-lg-3","fa-circle-check","{Feature — e.g. BI dashboards}","{What it does — e.g. Margins and service levels are visible on a single screen.}"))))
# Expertise (5 -> .col) : real v4 links
T.append((G_SEC, tpl("s_cap_expertise","Expertise",
  head("An integrated offer","ERP · Web · IA · BI for {Subject of the page}","Four areas of expertise, one team that knows your business.")+
  icard("col-6 col-lg-3","fa-cubes","ERP","{Description of the ERP (Odoo) offer for this subject — e.g. MRP, quality, maintenance and cost of goods on Odoo.}","/erp","<small>Transform your everyday with</small><br/>ERP",btn=True)+
  icard("col-6 col-lg-3","fa-globe","Web &amp; Marketing","{Description of the Web &amp; Marketing offer for this subject — e.g. Customer portals, technical catalogs and product configurators.}","/website-and-marketing","<small>Transform your everyday with</small><br/>Web &amp; Marketing",btn=True)+
  icard("col-6 col-lg-3","fa-robot","Artificial Intelligence","{Description of the AI offer for this subject — e.g. Predictive maintenance and manufacturing-order optimization.}","/artificial-intelligence","<small>Transform your everyday with</small><br/>Artificial Intelligence",btn=True)+
  icard("col-6 col-lg-3","fa-chart-line","Business Intelligence","{Description of the BI offer for this subject — e.g. OEE tracking, margins by product and service-rate dashboards.}","/business-intelligence","<small>Transform your everyday with</small><br/>Business Intelligence",btn=True))))
# Sectors (5 -> .col) : real v4 links
T.append((G_SEC, tpl("s_cap_sectors","Sectors",
  head("By sector","Organized around your industry","Teams organized by client industry. Each sector covers ERP, Web, AI and BI.")+
  icard("col","fa-building","Services &amp; Tertiary","{Short line about this industry — e.g. ERP, CRM and project management for service firms and agencies.}","/transform-your-industry/services","<small>Transform your organisation</small><br/>Services &amp; Tertiary",btn=True)+
  icard("col","fa-industry","Industry / Manufacturing","{Short line about this industry — e.g. MRP, quality and maintenance for manufacturers.}","/transform-your-industry/manufacturing","<small>Transform your organisation</small><br/>Industry / Manufacturing",btn=True)+
  icard("col","fa-truck","Distribution &amp; Logistics","{Short line about this industry — e.g. Stock, traceability and order fulfillment for wholesalers.}","/transform-your-industry/distribution","<small>Transform your organisation</small><br/>Distribution &amp; Logistics",btn=True)+
  icard("col","fa-store","Retail &amp; Point of Sale","{Short line about this industry — e.g. Omnichannel checkout, online and in-store, in one system.}","/transform-your-industry/retail","<small>Transform your organisation</small><br/>Retail &amp; Point of Sale",btn=True)+
  icard("col","fa-shield-halved","Regulated Industries","{Short line about this industry — e.g. Compliance, traceability and documentation built in.}","/transform-your-industry/regulated","<small>Transform your organisation</small><br/>Regulated Industries",btn=True))))
# Teams (8 roles -> col-6 col-lg-3), icons from source, EN names static, desc dynamic, real v4 links
roles=[("fa-handshake","Sales &amp; CRM","{e.g. Pipeline, AI scoring and quotes in a few clicks.}","/transform-your-everyday/sales-team"),
 ("fa-cart-plus","Purchasing","{e.g. Tenders, suppliers and purchase orders centralized.}","/transform-your-everyday/purchasing-team"),
 ("fa-industry","Operations &amp; Manufacturing","{e.g. MRP, work orders and real-time capacity.}","/transform-your-everyday/production-team"),
 ("fa-truck-fast","Supply Chain","{e.g. Stock, traceability and AI demand forecasting.}","/transform-your-everyday/supply-chain-team"),
 ("fa-scale-balanced","Finance &amp; Accounting","{e.g. Fast close, consolidated reporting and compliance.}","/transform-your-everyday/finance-team"),
 ("fa-users","Human Resources","{e.g. Recruitment, time off, payroll and appraisals in one tool.}","/transform-your-everyday/hr-team"),
 ("fa-bullhorn","Marketing","{e.g. Multichannel campaigns, leads and measurable ROI.}","/transform-your-everyday/marketing-team"),
 ("fa-headset","Helpdesk &amp; After-Sales","{e.g. Tickets, SLAs and customer satisfaction in real time.}","/transform-your-everyday/customer-service-team")]
T.append((G_SEC, tpl("s_cap_teams","Teams / functions",
  head("By business function","Solutions for every team","Explore how Captivea concretely improves your teams' day-to-day work, department by department.")+
  "".join(icard("col-6 col-lg-3",i,n,d,h,n+" team<br/><small>Transform their everyday</small>",btn=True) for i,n,d,h in roles))))
# AI use cases (text-block with a bullet list; no icons)
T.append((G_SEC, tpl("s_cap_ai","AI use cases",
  '<div class="o_colored_level offset-lg-1 col-lg-10 pt8 pb8"><p class="lead">Sector AI use cases</p>'
  '<h2>Artificial intelligence at the service of {your operations — e.g. the shop floor}</h2>'
  '<ul><li><strong>{AI use case 1 — e.g. Demand forecasting}</strong> — {Concrete benefit — e.g. Anticipate peaks and smooth the production load.}</li>'
  '<li><strong>{AI use case 2 — e.g. Optimized scheduling}</strong> — {Concrete benefit — e.g. Sequence manufacturing orders to reduce changeover times.}</li>'
  '<li><strong>{AI use case 3 — e.g. Predictive maintenance}</strong> — {Concrete benefit — e.g. Detect machine drift before breakdowns occur.}</li>'
  '<li><strong>{AI use case 4 — e.g. Assisted quality control}</strong> — {Concrete benefit — e.g. Identify non-conformances earlier in the process.}</li>'
  '<li><strong>{AI use case 5 — e.g. Purchasing optimization}</strong> — {Concrete benefit — e.g. Recommend quantities and suppliers based on lead times and costs.}</li></ul></div>',
  oc="o_cc2")))
# Blog teaser (static 3-article grid; can be swapped for the dynamic blog snippet)
T.append((G_SEC, tpl("s_cap_blog","Blog teaser",
  head("Resources","Articles &amp; guides on {topic}")+
  icard("col-12 col-lg-4","fa-blog","{Article title 1 — e.g. How to succeed in your Odoo ERP project}","{Category — e.g. ERP} — {Author — e.g. Captivea}, {Date — e.g. March 2025}","/blog","Read the article →")+
  icard("col-12 col-lg-4","fa-blog","{Article title 2 — e.g. 5 signs your tools are slowing your teams down}","{Category — e.g. Productivity} — {Author — e.g. Captivea}, {Date — e.g. April 2025}","/blog","Read the article →")+
  icard("col-12 col-lg-4","fa-blog","{Article title 3 — e.g. AI in manufacturing: where to start}","{Category — e.g. Artificial Intelligence} — {Author — e.g. Captivea}, {Date — e.g. May 2025}","/blog","Read the article →")+
  '<div class="o_colored_level col-12 text-center pt16"><a href="/blog" class="btn btn-secondary o_translate_inline">All articles</a></div>')))
# Related links ("Go further")
# Related links: a clean "Go further" block — centered buttons in a flex row
# (gap spacing, no &nbsp;/ZWSP), each linking to another page.
_related_btns="".join('<a href="#" class="o_translate_inline btn btn-primary">{Button link to another page}</a>' for _ in range(4))
T.append((G_SEC, tpl("s_cap_related","Related links",
  '<div class="o_colored_level col-lg-12 text-center pt8 pb8">'
  '<p class="lead">Explore</p><h2>Go further</h2>'
  '<div class="d-flex flex-wrap justify-content-center gap-2 mt-2">'+_related_btns+'</div></div>',
  oc="o_cc2")))

# ===================== PRODUCT & ODOO =====================
T.append((G_PROD, tpl("s_cap_definition","Definition",
  text_block("Definition","What is {Product / topic — e.g. Odoo}?","<p>{Clear definition in plain language — e.g. Odoo is an open-source, modular ERP that brings together every application a business needs in a single platform, from the first sales contact through to invoicing and reporting.}</p>"))))
T.append((G_PROD, tpl("s_cap_why_odoo","Why Odoo",
  head("Why Odoo","One unified ERP")+
  icard("col-lg-4","fa-cubes","{Argument — e.g. Comprehensive features}","{Why it matters for the client — e.g. Exceptional business coverage, from CRM to manufacturing.}")+
  icard("col-lg-4","fa-plug","{Argument — e.g. Competitive pricing}","{Why it matters for the client — e.g. A total cost of ownership far lower than legacy ERPs.}")+
  icard("col-lg-4","fa-chart-line","{Argument — e.g. Simple and modern}","{Why it matters for the client — e.g. An intuitive interface your teams adopt quickly.}"))))
T.append((G_PROD, tpl("s_cap_hosting","Hosting",
  head("Hosting","Choose your setup","Captivea advises you on the option best suited to your customization, cost and security requirements.")+
  icard("col-lg-4","fa-cloud","Odoo Online (SaaS)","{When to choose it — e.g. The simplest option: everything is managed by Odoo, with no infrastructure to maintain.}")+
  icard("col-lg-4","fa-server","Odoo.sh","{When to choose it — e.g. The ideal cloud platform for custom developments.}")+
  icard("col-lg-4","fa-hard-drive","On-Premise","{When to choose it — e.g. On your own servers, for total data control.}"))))
T.append((G_PROD, tpl("s_cap_gold_partner","Gold Partner credibility",
  text_block("Certified","Odoo Gold Partner","<p class=\"lead\">{Certifications, years, projects that build trust — e.g. Odoo Gold Partner, twice nominated at the Odoo Awards 2024, with 18+ years of experience and 800+ completed projects.}</p>",off=False),
  oc="o_cc2")))
T.append((G_PROD, tpl("s_cap_comparison_teaser","Comparison teaser",
  '<div class="o_colored_level col-lg-8 offset-lg-2 text-center"><p class="lead">Compare</p>'
  '<h2>Odoo vs other ERPs</h2><p class="lead">{Teaser linking to the Odoo vs [competitor] pages — e.g. More flexible, more affordable and more modern than legacy ERPs — see how Odoo compares.}</p>'
  '<p><a href="/erp/erp-comparison" class="btn btn-secondary o_translate_inline">See all comparisons</a></p></div>',
  oc="o_cc2")))
T.append((G_PROD, tpl("s_cap_comparison_table","Comparison table",
  head("Comparison","Odoo vs {Competitor — e.g. SAP Business One}","More flexible, more affordable and more modern than legacy ERPs.")+
  '<div class="o_colored_level col-lg-12 pt8 pb8"><table class="table"><thead><tr><th>Criteria</th><th>Odoo</th><th>{Competitor}</th></tr></thead>'
  '<tbody><tr><td>{Criteria 1 — e.g. Total cost of ownership}</td><td>{Odoo value — e.g. Transparent per-user pricing}</td><td>{Competitor value — e.g. High license and maintenance fees}</td></tr>'
  '<tr><td>{Criteria 2 — e.g. Deployment time}</td><td>{Odoo value — e.g. Weeks to a few months}</td><td>{Competitor value — e.g. Long, costly rollouts}</td></tr>'
  '<tr><td>{Criteria 3 — e.g. Flexibility and customization}</td><td>{Odoo value — e.g. Open source, fully adaptable}</td><td>{Competitor value — e.g. Rigid, expensive to customize}</td></tr></tbody></table></div>')))
# Odoo apps full list (47) grouped by family, real odoo.com links as small buttons
APPS=[("Sales &amp; CRM",[("fa-handshake","CRM","https://www.odoo.com/app/crm"),("fa-cart-shopping","Sales","https://www.odoo.com/app/sales"),("fa-store","Point of Sale","https://www.odoo.com/app/point-of-sale-shop"),("fa-key","Rental","https://www.odoo.com/app/rental"),("fa-screwdriver-wrench","Field Service","https://www.odoo.com/app/field-service")]),
 ("Website",[("fa-globe","Website","https://www.odoo.com/app/website"),("fa-shop","eCommerce","https://www.odoo.com/app/ecommerce"),("fa-comments","Live Chat","https://www.odoo.com/app/live-chat"),("fa-calendar-star","Events","https://www.odoo.com/app/events"),("fa-graduation-cap","eLearning","https://www.odoo.com/app/elearning"),("fa-blog","Blog","https://www.odoo.com/app/blog"),("fa-comments-question","Forum","https://www.odoo.com/app/forum")]),
 ("Inventory &amp; Manufacturing",[("fa-boxes-stacked","Inventory","https://www.odoo.com/app/inventory"),("fa-cart-plus","Purchase","https://www.odoo.com/app/purchase"),("fa-industry","Manufacturing","https://www.odoo.com/app/manufacturing"),("fa-shield-check","Quality","https://www.odoo.com/app/quality"),("fa-wrench","Maintenance","https://www.odoo.com/app/maintenance"),("fa-diagram-project","PLM","https://www.odoo.com/app/plm"),("fa-barcode","Barcode","https://www.odoo.com/app/barcode"),("fa-hammer","Repairs","https://www.odoo.com/app/repairs")]),
 ("Finance",[("fa-scale-balanced","Accounting","https://www.odoo.com/app/accounting"),("fa-file-invoice","Invoicing","https://www.odoo.com/app/invoicing"),("fa-receipt","Expenses","https://www.odoo.com/app/expenses"),("fa-signature","Sign","https://www.odoo.com/app/sign"),("fa-folder","Documents","https://www.odoo.com/app/documents"),("fa-table","Spreadsheet","https://www.odoo.com/app/spreadsheet")]),
 ("Human Resources",[("fa-users","Employees","https://www.odoo.com/app/employees"),("fa-user-plus","Recruitment","https://www.odoo.com/app/recruitment"),("fa-umbrella-beach","Time Off","https://www.odoo.com/app/time-off"),("fa-money-bill-wave","Payroll","https://www.odoo.com/app/payroll"),("fa-star","Appraisals","https://www.odoo.com/app/appraisals"),("fa-car","Fleet","https://www.odoo.com/app/fleet"),("fa-utensils","Lunch","https://www.odoo.com/app/lunch"),("fa-share-nodes","Referrals","https://www.odoo.com/app/referrals")]),
 ("Marketing",[("fa-envelope","Email Marketing","https://www.odoo.com/app/email-marketing"),("fa-mobile","SMS Marketing","https://www.odoo.com/app/sms-marketing"),("fa-thumbs-up","Social Marketing","https://www.odoo.com/app/social-marketing"),("fa-robot","Marketing Automation","https://www.odoo.com/app/marketing-automation")]),
 ("Productivity",[("fa-message","Discuss","https://www.odoo.com/app/discuss"),("fa-diagram-gantt","Project","https://www.odoo.com/app/project"),("fa-clock","Timesheets","https://www.odoo.com/app/timesheet"),("fa-sticky-note","Notes","https://www.odoo.com/app/note"),("fa-circle-check","Approvals","https://www.odoo.com/app/approvals"),("fa-phone","VoIP","https://www.odoo.com/app/voip"),("fa-book","Knowledge","https://www.odoo.com/app/knowledge")]),
 ("Technical",[("fa-paintbrush","Studio","https://www.odoo.com/app/studio"),("fa-wifi","IoT","https://www.odoo.com/app/iot")])]
apps_inner='<div class="o_colored_level col-lg-12 text-center pt8 pb8"><p class="lead">The Odoo apps relevant to you</p><h2>The complete Odoo suite</h2><p class="lead">All Odoo applications, activated at your own pace.</p></div>'
for fam,items in APPS:
    btns=""
    for ic,nm,href in items:
        btns+='<a href="'+href+'" target="_blank" rel="noopener" class="btn btn-secondary btn-sm mb-2">'+licon(ic,"me-1")+nm+'</a>\n                        '
    apps_inner+=('<div class="o_colored_level col-md-6 col-lg-4 pt8 pb8 d-flex">'
      '<div class="s_card card o_cc o_cc1 o_colored_level w-100" data-snippet="s_card" data-name="Card"><div class="card-body">'
      '<h3 class="card-title h5-fs">'+fam+'</h3>'
      '<div class="d-flex flex-wrap gap-2">\n                        '+btns.rstrip()+'\n                        </div>'
      '</div></div></div>')
T.append((G_PROD, tpl("s_cap_odoo_apps","Odoo apps",apps_inner,base="s_text_image")))
T.append((G_PROD, tpl("s_cap_app_definition","App definition",
  text_block("The app","{Odoo app name — e.g. Odoo CRM}","<p>{What this Odoo app is and what it is for — e.g. Odoo CRM centralizes your pipeline, quotes and follow-ups so nothing slips through the cracks.}</p>"))))
T.append((G_PROD, tpl("s_cap_use_cases","Use cases",
  head("Use cases","Concrete uses")+
  icard("col-lg-4","fa-circle-check","{Use case — e.g. Pipeline management}","{Description — e.g. Track every opportunity from first contact to close on a single board.}")+
  icard("col-lg-4","fa-circle-check","{Use case — e.g. Quotes and e-signature}","{Description — e.g. Send quotes clients can sign online, with no back-and-forth.}")+
  icard("col-lg-4","fa-circle-check","{Use case — e.g. Automated follow-ups}","{Description — e.g. Trigger reminders automatically so no lead goes cold.}"))))
T.append((G_PROD, tpl("s_cap_addon","Captivea add-on",
  '<div class="o_colored_level offset-lg-1 col-lg-10 pt8 pb8"><p class="lead">Captivea add-on</p>'
  '<h2>{Add-on name — e.g. Captivea Advanced Reporting}</h2><p>{Short definition of the add-on — e.g. A Captivea module that extends Odoo with ready-to-use dashboards and KPIs for your teams.}</p><div><br/></div>'
  '<p>Extends the native Odoo app: <a href="#" class="o_translate_inline">{Parent Odoo app — e.g. Odoo Accounting}</a></p></div>')))
T.append((G_PROD, tpl("s_cap_isv_intro","ISV presentation",
  text_block("Partner","Who is {Partner name — e.g. our technology partner}?","<p>{Presentation of the ISV partner and its solution — e.g. A specialized software vendor whose solution integrates natively with Odoo to cover an advanced business need.}</p>"))))
T.append((G_PROD, tpl("s_cap_isv_benefits","ISV user benefits",
  head("User benefits","What you gain")+
  icard("col-lg-4","fa-circle-check","{Benefit — e.g. Native integration}","{Description — e.g. Works seamlessly inside your Odoo, with no double entry.}")+
  icard("col-lg-4","fa-circle-check","{Benefit — e.g. Faster deployment}","{Description — e.g. Ready-to-use connectors shorten the project timeline.}")+
  icard("col-lg-4","fa-circle-check","{Benefit — e.g. Lower total cost}","{Description — e.g. One ecosystem to maintain instead of several disconnected tools.}"))))
T.append((G_PROD, tpl("s_cap_erp_compatibility","ERP compatibility",
  head("Compatibility","Works with your Odoo")+
  '<div class="o_colored_level col-lg-12 pt8 pb8"><table class="table"><thead><tr><th>Odoo edition / version</th><th>Compatibility</th></tr></thead>'
  '<tbody><tr><td>{Edition / version — e.g. Odoo 17 Enterprise}</td><td>{Yes / details — e.g. Fully compatible}</td></tr>'
  '<tr><td>{Edition / version — e.g. Odoo 16 Community}</td><td>{Yes / details — e.g. Compatible, some features require Enterprise}</td></tr></tbody></table></div>')))

# ===================== COMPANY & LOCAL =====================
T.append((G_COMP, tpl("s_cap_story","Story",
  '<div class="o_colored_level offset-lg-1 col-lg-10 pt8 pb8"><p class="lead">Our story</p><h2>{Story title — e.g. From a conviction to a global group}</h2>'
  '<div>{Chapter 1: where we come from — e.g. Captivea was born from a simple conviction: bring technology closer to business, with an obsession for client autonomy.}</div><div><br/></div><div>{Chapter 2: what drives us today — e.g. Today we are a group organized by industry vertical, closely aligned with the real challenges of each client.}</div></div>')))
T.append((G_COMP, tpl("s_cap_values","Values",
  head("Our values","What guides every project")+
  icard("col-lg-4","fa-star","{Value 1 — e.g. Client satisfaction}","{Short description with a concrete example — e.g. Respect, attentiveness and transparency: our clients' success is our only compass.}")+
  icard("col-lg-4","fa-handshake","{Value 2 — e.g. Performance}","{Short description with a concrete example — e.g. Individual, collective and client performance — we aim for measurable impact, not empty promises.}")+
  icard("col-lg-4","fa-bolt","{Value 3 — e.g. Cultural diversity}","{Short description with a concrete example — e.g. Our differences are a strength: they drive our progress and enrich every project.}"))))
T.append((G_COMP, tpl("s_cap_conviction","Conviction",
  text_block("Our conviction","{Conviction statement — e.g. A future made better by technology}","<p class=\"lead\">{Supporting paragraph — e.g. Technologies can improve our future — provided they are concretely placed in the hands of businesses. That is our role: identifying what matters and bringing it to our clients.}</p>",off=False),oc="o_cc2")))
T.append((G_COMP, tpl("s_cap_leadership","Leadership",
  head("Leadership","The people who lead Captivea","Consultants, business analysts, developers and subject-matter experts: it is the energy of our teams that turns technology into concrete results.")+
  icard("col-6 col-lg-3","fa-user","{Full name — e.g. Jane Doe}","{Role.} {One line bio — e.g. CEO. Sets the vision and keeps the company client-obsessed.}")+
  icard("col-6 col-lg-3","fa-user","{Full name — e.g. John Smith}","{Role.} {One line bio — e.g. CTO. Leads the technical teams and the Odoo practice.}")+
  icard("col-6 col-lg-3","fa-user","{Full name — e.g. Maria Garcia}","{Role.} {One line bio — e.g. COO. Ensures delivery excellence across every project.}")+
  icard("col-6 col-lg-3","fa-user","{Full name — e.g. David Chen}","{Role.} {One line bio — e.g. CFO. Keeps growth sustainable and finances transparent.}"))))
T.append((G_COMP, tpl("s_cap_country_presence","Country presence",
  head("Our presence","One team, present where you are","A structure replicated country by country, local teams and offshore competency centers — the best of both worlds.")+
  icard("col-6 col-lg-3","fa-earth-europe","{Country — e.g. United States}","{City / office — e.g. Florida headquarters.}")+
  icard("col-6 col-lg-3","fa-earth-europe","{Country — e.g. France}","{City / office — e.g. Chambery office.}")+
  icard("col-6 col-lg-3","fa-earth-europe","{Country — e.g. Singapore}","{City / office — e.g. Asia-Pacific hub.}")+
  icard("col-6 col-lg-3","fa-earth-europe","{Country — e.g. India}","{City / office — e.g. Offshore competency center.}"))))
T.append((G_COMP, tpl("s_cap_offices","Offices",
  head("Our offices","Close to you","A regional presence to support your teams wherever you are.")+
  icard("col-6 col-lg-3","fa-location-dot","{City — e.g. Florida}","{Address line — e.g. US Headquarters, Florida.}")+
  icard("col-6 col-lg-3","fa-location-dot","{City — e.g. New York}","{Address line — e.g. Northeast region.}")+
  icard("col-6 col-lg-3","fa-location-dot","{City — e.g. Chicago}","{Address line — e.g. Midwest region.}")+
  icard("col-6 col-lg-3","fa-location-dot","{City — e.g. Texas}","{Address line — e.g. South-Central region.}"))))
T.append((G_COMP, tpl("s_cap_coverage","Coverage areas",
  head("Coverage","Areas we serve","Beyond our offices, we serve clients across every region.")+
  '<div class="o_colored_level offset-lg-1 col-lg-10 text-center"><p>{List of cities / regions covered, comma separated — e.g. Southeast, Northeast, Mid-Atlantic, South-Central, Midwest, Great Lakes, Southwest, West Coast, Pacific Northwest, Mountain West.}</p></div>')))
T.append((G_COMP, tpl("s_cap_market_spotlight","Market spotlight",
  text_block("Spotlight","{Market / country name — e.g. France}","<p class=\"lead\">{Local proof and specifics for this market — e.g. Local teams, French-speaking support and full compliance with local accounting and regulatory requirements.}</p>",off=False),oc="o_cc2")))
T.append((G_COMP, tpl("s_cap_leader_odoo","Odoo leader argument",
  text_block("Odoo Gold Partner","The worldwide leader in Odoo integration","<p class=\"lead\">{Proof: years, projects, awards, offices — e.g. Odoo Gold Partner, twice nominated at the 2024 Odoo Awards in Europe and North America, with 18+ years of experience and 800+ projects.}</p>",off=False),
  oc="o_cc3",band="cap-band-red",pad="pt64 pb64")))
T.append((G_COMP, tpl("s_cap_services","Services",
  head("What we deliver","Our services","From consulting to implementation: what you gain, concretely.")+
  icard("col","fa-briefcase","Business Consulting","{Benefit-oriented description — e.g. Frame your digital transformation and optimize your processes with expert guidance.}","/business-consulting","How Business Consulting can transform my everyday")+
  icard("col","fa-cubes","ERP","{Benefit-oriented description — e.g. A single platform to run sales, projects and invoicing.}","/erp","How ERP can transform my everyday")+
  icard("col","fa-globe","Web &amp; Marketing","{Benefit-oriented description — e.g. Attract customers, get found online and sell through a connected website.}","/website-and-marketing","How Web &amp; Marketing can transform my everyday")+
  icard("col","fa-robot","Artificial Intelligence","{Benefit-oriented description — e.g. Automate repetitive tasks and anticipate demand with practical AI.}","/artificial-intelligence","How Artificial Intelligence can transform my everyday")+
  icard("col","fa-chart-line","Business Intelligence","{Benefit-oriented description — e.g. Visualize your performance and track your KPIs on clear dashboards.}","/business-intelligence","How Business Intelligence can transform my everyday"))))

# ===================== OFFERS & CASE STUDIES =====================
T.append((G_OFF, tpl("s_cap_offer_detail","Offer detail",
  '<div class="o_colored_level offset-lg-1 col-lg-10 pt8 pb8"><p class="lead">The offer</p><h2>{Offer name — e.g. Odoo Quick Start}</h2>'
  '<p>{What the offer covers — e.g. A fixed-scope package to get your core Odoo apps live fast, with configuration, data import and user training.}</p><div><br/></div>'
  '<p>{Engagement models (fixed price / time credit / pay-as-you-go) and sourcing (local / hybrid / offshore) — e.g. Available as fixed price, time credit or pay-as-you-go, delivered locally, hybrid or offshore to fit your budget.}</p></div>')))
T.append((G_OFF, tpl("s_cap_benefit_positioning","Benefit positioning",
  text_block("Benefit","{Benefit statement — e.g. Give your teams back their selling time}","<p class=\"lead\">{Who it is for and the outcome delivered — e.g. For sales-driven SMBs and mid-market companies that want less admin and more closed deals.}</p>",off=False),
  oc="o_cc3",band="cap-band-red",pad="pt64 pb64")))
T.append((G_OFF, tpl("s_cap_case_context","Client context",
  text_block("The client","{Client name — e.g. Groupe Atlas Industries}","<p>{Who they are, their sector and their situation before the project — e.g. A mechanical-equipment manufacturer running three sites with siloed tools, multiple data re-entries and no consolidated visibility.}</p>"))))
T.append((G_OFF, tpl("s_cap_timeline","Project timeline",
  head("Timeline","How the project unfolded")+
  icard("col-lg-4","fa-flag","{Phase 1 — e.g. Scoping}","{What was done — e.g. Department workshops, process modeling and definition of target KPIs.}")+
  icard("col-lg-4","fa-gears","{Phase 2 — e.g. Design and build}","{What was done — e.g. Odoo configuration, data migration and custom developments.}")+
  icard("col-lg-4","fa-circle-check","{Phase 3 — e.g. Go Live}","{What was done — e.g. Phased go-live site by site, then BI dashboards and AI forecasting.}"))))
# NOTE: s_cap_client_quote moved to the cap_web_quote module as a DYNAMIC
# snippet (select a testimonial). gen_pages.py injects it via CLIENT_QUOTE.

# ===================== BUILD FILE =====================
groups=[("cap_general","Captivea — General","s_cover"),
 ("cap_sectors","Captivea — Sectors &amp; Business functions","s_three_columns"),
 ("cap_product","Captivea — Product &amp; Odoo","s_features"),
 ("cap_company","Captivea — Company &amp; Local","s_company_team"),
 ("cap_offers","Captivea — Offers &amp; Case studies","s_text_block")]

import re
templates_xml="\n\n".join(x for _,x in T)
grp_xml=""
for gid,label,thumb in groups:
    grp_xml+=('        <t snippet-group="'+gid+'" t-snippet="website.s_snippet_group" string="'+label+'" '
              't-thumbnail="/website/static/src/img/snippets_thumbs/'+thumb+'.svg"/>\n')
reg=""
for grp,x in T:
    sid=re.search(r'template id="([^"]+)"',x).group(1)
    reg+='        <t t-snippet="cap_web_captivea_theme.'+sid+'" group="'+grp+'"/>\n'

doc='<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n<!-- AUTO-GENERATED by tools/gen_snippets.py - do not edit by hand -->\n\n'+templates_xml+'\n\n'
doc+=('<template id="cap_web_captivea_theme_snippets" inherit_id="website.snippets" name="Captivea Snippets" priority="16">\n'
 '    <xpath expr="//snippets[@id=\'snippet_groups\']/t[@snippet-group=\'custom\']" position="before">\n'+grp_xml+'    </xpath>\n'
 '    <xpath expr="//snippets[@id=\'snippet_structure\']" position="inside">\n'+reg+'    </xpath>\n'
 '</template>\n\n</odoo>\n')
open(OUT,"w",encoding="utf-8").write(doc)
print("templates:",len(T),"| groups:",len(groups))
