# -*- coding: utf-8 -*-
import re, os
_HERE=os.path.dirname(os.path.abspath(__file__))
_BASE=os.path.abspath(os.path.join(_HERE,".."))
SNIP=os.path.join(_BASE,"views","snippets.xml")
OUT=os.path.join(_BASE,"data","pages.xml")
src=open(SNIP,encoding="utf-8").read()

# extract the full inner markup of each s_cap_* template (handles nested <section>,
# e.g. the CTA form which embeds an inner s_website_form section)
sections={}
for m in re.finditer(r'<template id="(s_cap_[^"]+)"[^>]*>(.*?)</template>', src, re.S):
    sections[m.group(1)]=m.group(2).strip()
print("sections extracted:",len(sections))

# s_cap_client_quote now lives in the cap_web_quote module as a DYNAMIC snippet
# (pick a testimonial). It server-renders a default testimonial (SEO) and the JS
# swaps to the one selected via data-testimonial-id. Injected here so pages that
# reference it still compose even though it is no longer in the theme snippets.
CLIENT_QUOTE = (
 '<section class="s_text_image s_cap_client_quote o_cc o_cc2 o_colored_level pt40 pb40" data-snippet="s_cap_client_quote" data-name="Captivea Client quote">'
 "<t t-set=\"_cq\" t-value=\"env['quote.testimonial'].sudo().search([('is_published', '=', True)], order='sequence, id desc', limit=1)\"/>"
 '<div class="container"><div class="row align-items-stretch"><div class="o_colored_level col-lg-8 offset-lg-2 text-center pt16 pb16">'
 '<div class="s_cap_cq_target">'
 '<t t-if="_cq"><blockquote class="blockquote"><p class="h4" t-out="_cq.quote"/></blockquote>'
 '<footer class="blockquote-footer"><span t-out="_cq.author"/><t t-if="_cq.role_id">, <span t-out="_cq.role_id.name"/></t><t t-if="_cq.company_name"> at <span t-out="_cq.company_name"/></t></footer></t>'
 '<t t-else=""><blockquote class="blockquote"><p class="h4">{Client quote}</p></blockquote><footer class="blockquote-footer">{Author}, {Role} at {Client}</footer></t>'
 '</div></div></div></div></section>'
)
sections.setdefault("s_cap_client_quote", CLIENT_QUOTE)

# page compositions: (key, url, title, [section ids])
H="s_cap_page_header"
PAGES=[
 ("home","/template-home","Template - Home",
   [H,"s_cap_leader_odoo","s_cap_services","s_cap_teams","s_cap_sectors","s_cap_market_spotlight","s_cap_story","s_cap_offices","s_cap_methodology","s_cap_testimonials"]),
 ("industries","/template-industries","Template - Industries",
   [H,"s_cap_context","s_cap_sectors","s_cap_teams","s_cap_references","s_cap_testimonials","s_cap_faq","s_cap_related"]),
 ("subsector","/template-subsector","Template - Sub-sector (Industry)",
   [H,"s_cap_context","s_cap_gains","s_cap_expertise","s_cap_ai","s_cap_subsectors_index","s_cap_references","s_cap_testimonials","s_cap_odoo_apps","s_cap_blog","s_cap_faq","s_cap_related"]),
 ("sector","/template-sector","Template - Sector hub",
   [H,"s_cap_context","s_cap_gains","s_cap_expertise","s_cap_ai","s_cap_subsectors_index","s_cap_teams","s_cap_references","s_cap_testimonials","s_cap_odoo_apps","s_cap_blog","s_cap_faq","s_cap_related"]),
 ("team","/template-team","Template - Team (Business function)",
   [H,"s_cap_context","s_cap_before_after","s_cap_pain_points","s_cap_gains","s_cap_methodology","s_cap_client_quote","s_cap_expertise","s_cap_references","s_cap_testimonials","s_cap_odoo_apps","s_cap_blog","s_cap_faq","s_cap_related"]),
 ("about","/template-about","Template - About",
   [H,"s_cap_solution","s_cap_stats","s_cap_story","s_cap_values","s_cap_conviction","s_cap_conviction","s_cap_client_quote","s_cap_country_presence","s_cap_leadership"]),
 ("country","/template-country","Template - Country",
   [H,"s_cap_context","s_cap_stats","s_cap_offices","s_cap_market_spotlight","s_cap_coverage","s_cap_references","s_cap_testimonials","s_cap_services","s_cap_blog","s_cap_faq"]),
 ("office","/template-office","Template - Office",
   [H,"s_cap_context","s_cap_services","s_cap_coverage","s_cap_market_spotlight","s_cap_faq"]),
 ("partner","/template-partner","Template - Odoo Partner (country)",
   [H,"s_cap_context","s_cap_gold_partner","s_cap_gains","s_cap_expertise","s_cap_services","s_cap_coverage","s_cap_references","s_cap_testimonials","s_cap_blog","s_cap_faq"]),
 ("product","/template-product","Template - Product pillar (Odoo)",
   [H,"s_cap_definition","s_cap_stats","s_cap_why_odoo","s_cap_odoo_apps","s_cap_hosting","s_cap_comparison_table","s_cap_gold_partner","s_cap_methodology","s_cap_faq"]),
 ("app_odoo","/template-app-odoo","Template - Odoo app",
   [H,"s_cap_app_definition","s_cap_key_features","s_cap_use_cases","s_cap_teams","s_cap_sectors","s_cap_odoo_apps","s_cap_references","s_cap_faq"]),
 ("app_captivea","/template-app-captivea","Template - Captivea add-on",
   [H,"s_cap_addon","s_cap_key_features","s_cap_use_cases","s_cap_faq"]),
 ("isv","/template-isv","Template - ISV partner",
   [H,"s_cap_isv_intro","s_cap_solution","s_cap_key_features","s_cap_isv_benefits","s_cap_erp_compatibility","s_cap_odoo_apps","s_cap_faq"]),
 ("comparison","/template-comparison","Template - Comparison",
   [H,"s_cap_context","s_cap_comparison_table","s_cap_why_odoo","s_cap_faq"]),
 ("offer","/template-offer","Template - Offer",
   [H,"s_cap_context","s_cap_offer_detail","s_cap_methodology","s_cap_faq"]),
 ("benefit","/template-benefit","Template - Customer benefit",
   [H,"s_cap_benefit_positioning","s_cap_solution","s_cap_references","s_cap_testimonials","s_cap_faq"]),
 ("case_study","/template-case-study","Template - Case study",
   [H,"s_cap_case_context","s_cap_solution","s_cap_timeline","s_cap_stats","s_cap_client_quote","s_cap_teams","s_cap_odoo_apps","s_cap_faq","s_cap_related"]),
]

# Per-page header context: personalise the hero capsule / H1 / intro to the page
# subject (give real context in the placeholder texts, not a generic "By industry").
CTX={
 "home":      ("Odoo Gold Partner", "{Your everyday, transformed with Odoo}", "{Intro: what Captivea does and the concrete value it brings to your business.}"),
 "industries":("By industry · {Industry name}", "{Industry} — transform your organisation", "{Intro: frame this industry's stakes and the value Captivea brings to it.}"),
 "subsector": ("By sub-sector · {Sub-sector name}", "{Sub-sector} — your Odoo experts", "{Intro: the specific challenges of this sub-sector and how Captivea answers them.}"),
 "sector":    ("By sector · {Sector name}", "{Sector} — transform your organisation", "{Intro: the sector's stakes and the value Captivea brings to it.}"),
 "team":      ("By business function · {Team name}", "Transform your {Team} everyday", "{Intro: the daily pains of this team and how Captivea &amp; Odoo solve them.}"),
 "about":     ("About Captivea", "{Who we are}", "{Intro: Captivea's mission, story and what makes us different.}"),
 "country":   ("Captivea in · {Country}", "{Your Odoo integrator in {Country}}", "{Intro: local presence, team and value delivered in this country.}"),
 "office":    ("Our office · {City}", "{Captivea {City}}", "{Intro: this office, its team, expertise and coverage.}"),
 "partner":   ("Odoo Gold Partner · {Country}", "{Your Odoo partner in {Country}}", "{Intro: why choose Captivea as your Odoo partner here.}"),
 "product":   ("Odoo product · {Product name}", "{Product}, delivered by Captivea", "{Intro: what this product does and Captivea's expertise on it.}"),
 "app_odoo":  ("Odoo app · {App name}", "{App} — configured by Captivea", "{Intro: what this Odoo app does and typical use cases.}"),
 "app_captivea":("Captivea add-on · {App name}", "{App} — a Captivea app for Odoo", "{Intro: what this add-on brings and who it is for.}"),
 "isv":       ("For software vendors · ISV", "{Publish your app on Odoo with Captivea}", "{Intro: the ISV integration/compatibility value Captivea provides.}"),
 "comparison":("Comparison · Odoo vs {Competitor}", "{Odoo vs {Competitor}}", "{Intro: how Odoo compares and where Captivea makes the difference.}"),
 "offer":     ("Our offer · {Offer name}", "{Offer}", "{Intro: what this offer includes and the outcome for the client.}"),
 "benefit":   ("Customer benefit · {Benefit}", "{Benefit} with Captivea", "{Intro: the concrete benefit and how Captivea delivers it.}"),
 "case_study":("Case study · {Client name}", "{Client name} — {result in one line}", "{Intro: the client, the challenge and the measurable outcome.}"),
}
_GEN_EYE='<p class="lead">By industry · {Industry name}</p>'
_GEN_H1 ='<h1>{Page Title}</h1>'
_GEN_INT='<p class="lead">{Intro paragraph: frame the industry and the value Captivea brings.}</p>'

def personalise_header(sec, key):
    """Replace the generic hero capsule / H1 / intro with the page's context."""
    if key not in CTX:
        return sec
    eye, h1, intro = CTX[key]
    sec = sec.replace(_GEN_EYE, '<p class="lead">%s</p>' % eye, 1)
    sec = sec.replace(_GEN_H1,  '<h1>%s</h1>' % h1, 1)
    sec = sec.replace(_GEN_INT, '<p class="lead">%s</p>' % intro, 1)
    return sec

# Per-page subject: (token used for {Subject of the page}, prose word for "this <word>").
# Used to contextualise the subject-referring tokens of the framing sections
# (context / gains / expertise) to the page's actual subject.
SUBJ={
 "home":("{your business}","business"), "industries":("{Industry}","industry"),
 "subsector":("{Sub-sector}","sub-sector"), "sector":("{Sector}","sector"),
 "team":("{Team}","team"), "about":("{Captivea}","company"),
 "country":("{Country}","market"), "office":("{City}","office"),
 "partner":("{your organisation}","organisation"), "product":("{Product}","product"),
 "app_odoo":("{App}","app"), "app_captivea":("{App}","app"),
 "isv":("{your software}","software"), "comparison":("{your business}","business"),
 "offer":("{Offer}","offer"), "benefit":("{your business}","business"),
 "case_study":("{Client name}","project"),
}

def personalise_body(sec, key):
    """Contextualise the subject-referring tokens of framing sections."""
    if key not in SUBJ:
        return sec
    t, w = SUBJ[key]
    for old, new in [
        ("{Subject of the page}", t),
        ("offer for this subject.", "offer for this %s." % w),
        ("{Context paragraph 1: challenges the sector faces.}",
         "{Context paragraph 1: the challenges this %s faces today.}" % w),
        ("{Context paragraph 2: Captivea's approach.}",
         "{Context paragraph 2: Captivea's approach for this %s.}" % w),
        ("{Concrete gain for this audience.}", "{Concrete gain for this %s.}" % w),
    ]:
        sec = sec.replace(old, new)
    return sec

def indent(block,n):
    pad=" "*n
    return "\n".join(pad+l if l.strip() else l for l in block.split("\n"))

def set_cc(sec, n):
    # override the outer <section> color combination (first o_ccN in the string)
    return re.sub(r'o_cc[1-5]', 'o_cc'+str(n), sec, count=1)

recs=[]
for key,url,title,ids in PAGES:
    # Rule: the last section is always the CTA+form section (s_cap_cta, o_cc3, #form).
    # De-duplicate any s_cap_cta then force it to be the single, final section.
    ids=[s for s in ids if s!="s_cap_cta"]
    ids.append("s_cap_cta")
    last=len(ids)-1
    body=""
    for i,sid in enumerate(ids):
        if sid not in sections:
            print("MISSING",sid); continue
        sec=sections[sid]
        # Rule: section 1 (hero) keeps its own style but is personalised to the
        # page subject; the final form stays o_cc3; every section in between
        # alternates o_cc1 / o_cc2.
        if i==0 and sid==H:
            sec=personalise_header(sec, key)
        # Contextualise subject-referring tokens of every section to the page.
        sec=personalise_body(sec, key)
        if i!=0 and i!=last:
            sec=set_cc(sec, 1 if (i-1)%2==0 else 2)
        body+=indent(sec,20)+"\n"
    rec=('    <record id="page_'+key+'" model="website.page">\n'
         '        <field name="name">'+title+'</field>\n'
         '        <field name="is_published" eval="True"/>\n'
         '        <field name="key">cap_web_captivea_theme.page_'+key+'</field>\n'
         '        <field name="url">'+url+'</field>\n'
         '        <field name="type">qweb</field>\n'
         '        <field name="arch" type="xml">\n'
         '            <t t-name="cap_web_captivea_theme.page_'+key+'">\n'
         '                <t t-call="website.layout">\n'
         '                    <t t-set="additional_title">'+title+'</t>\n'
         '                    <div id="wrap" class="oe_structure">\n'
         +body+
         '                    </div>\n'
         '                </t>\n'
         '            </t>\n'
         '        </field>\n'
         '    </record>')
    recs.append(rec)

doc='<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n<!-- AUTO-GENERATED by tools/gen_pages.py - do not edit by hand -->\n\n'+ "\n\n".join(recs) +'\n\n</odoo>\n'
open(OUT,"w",encoding="utf-8").write(doc)
print("pages generated:",len(PAGES))
