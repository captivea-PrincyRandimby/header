# Les 17 design templates du thème

Ils viennent de [`cap_web_captivea_theme/data/pages.xml`](../cap_web_captivea_theme/data/pages.xml).

Ce sont des `website.page` dont la clé commence par `cap_web_captivea_theme.page_`. Le module les propose automatiquement dans le champ **Design Template** — un template ajouté au thème apparaît au prochain upgrade, sans rien changer dans le code.

## Rappel : à quoi sert un template

Quand tu en choisis un, **le template EST la page**. Son markup est copié tel quel, et l'IA ne remplit que les trous `{...}`.

Elle ne peut donc ni supprimer, ni réordonner, ni inventer une section — elle ne voit jamais le markup.

## C'est quoi un « trou »

Un texte entre accolades que le thème a laissé dans son markup, et que l'IA doit remplacer.

Avant :

```html
<h2>{Context title - e.g. An American Odoo partner}</h2>
```

Après :

```html
<h2>Odoo Inventory Management</h2>
```

Ce n'est pas du vrai texte, c'est une **consigne** du designer du thème : « ici il faut un titre de ce genre ».

Le nombre de trous mesure donc **la quantité de texte que l'IA doit écrire**. Ce n'est pas le nombre de sections : une seule section peut contenir 10 trous — un titre, un chapeau, et trois cartes avec chacune un titre et une description.

Dans le code, on les appelle *placeholders* (`PLACEHOLDER_RE` dans `theme_snippets.py`) ou *slots* (`text_slots()` dans `page_writer.py`).

---

## Tableau récapitulatif

| Template | Pour quoi | Trous |
|---|---|---|
| **Home** | La page d'accueil du site | 54 |
| **About** | Qui est Captivea : histoire, valeurs, dirigeants | 54 |
| **Sector hub** | Un grand secteur d'activité (l'industrie, le retail…) | 93 |
| **Sub-sector (Industry)** | Un sous-secteur précis dans un secteur | 85 |
| **Team (Business function)** | Un métier : finance, achats, production… | 92 |
| **Country** | Votre présence dans un pays | 47 |
| **Office** | Une agence précise | 26 |
| **Odoo Partner (country)** | « Partenaire Odoo en France » — page de conquête locale | 58 |
| **Product pillar (Odoo)** | Odoo en général : pourquoi Odoo, hébergement, comparatif | 57 |
| **Odoo app** | Une app Odoo : Inventory, CRM, Accounting… | 45 |
| **Captivea add-on** | Un module développé par Captivea | 33 |
| **ISV partner** | Un éditeur partenaire et son intégration Odoo | 53 |
| **Comparison** | Odoo contre un concurrent ERP | 37 |
| **Comparison (CMS)** | Odoo contre un concurrent CMS / e-commerce | 37 |
| **Offer** | Une offre commerciale packagée | 32 |
| **Customer benefit** | Un bénéfice client précis, angle marketing | 20 |
| **Case study** | Un cas client : contexte, projet, résultats | 51 |

Tous tiennent en **un seul appel IA** — les trous représentent 1 600 à 5 800 caractères, largement sous le budget de 8 000 par lot.

---

## Structure du site

### Template - Home
La page d'accueil.

Sections : argument leader Odoo, services, équipes, secteurs, actualité marché, histoire, bureaux, méthodologie, témoignages.

C'est le seul qui présente tout le site d'un coup.

### Template - About
La page « qui sommes-nous ».

Sections : solution, chiffres clés, histoire, valeurs, convictions, citation client, présence par pays, dirigeants.

Le seul avec une section **Leadership**.

---

## Marchés et métiers

### Template - Sector hub
Un grand secteur. Le template le plus complet du thème (93 trous).

Sections : contexte, ce que vous gagnez, expertise, cas d'usage IA, index des sous-secteurs, équipes, références clients, témoignages, apps Odoo, articles de blog, FAQ, liens connexes.

À utiliser pour la page chapeau d'un secteur, qui renvoie vers ses sous-secteurs.

### Template - Sub-sector (Industry)
Un sous-secteur précis. Quasi identique au Sector hub, sans la section Équipes.

À utiliser pour les pages filles d'un secteur.

### Template - Team (Business function)
Un métier plutôt qu'un secteur : direction financière, achats, production…

Sections spécifiques : **Avant / Après**, **Points de douleur**, méthodologie, citation client.

C'est le seul template construit autour d'un problème métier à résoudre.

---

## Géographie

### Template - Country
Votre présence dans un pays.

Sections : contexte, chiffres clés, bureaux, actualité marché, zones couvertes, références, services, FAQ.

### Template - Office
Une agence précise. Le plus léger avec **Customer benefit** (26 trous).

Sections : contexte, services, zones couvertes, actualité marché, FAQ.

### Template - Odoo Partner (country)
Page de conquête : « Partenaire Odoo en France ».

Sections spécifiques : **crédibilité Gold Partner**, ce que vous gagnez, expertise, services, zones couvertes.

À utiliser pour les mots-clés du type `odoo partner france`.

---

## Produit

### Template - Product pillar (Odoo)
Odoo dans son ensemble.

Sections : définition, chiffres clés, **pourquoi Odoo**, apps Odoo, **hébergement**, **tableau comparatif**, crédibilité Gold Partner, méthodologie.

Le seul avec une section Hébergement. À utiliser pour les mots-clés larges type `odoo erp`.

### Template - Odoo app
Une app Odoo précise.

Sections : **définition de l'app**, fonctionnalités clés, cas d'usage, équipes concernées, secteurs, autres apps, références, FAQ.

Le plus utilisé en pratique : une page par app.

### Template - Captivea add-on
Un module que vous avez développé.

Sections : présentation de l'add-on, fonctionnalités clés, cas d'usage, FAQ.

Léger et ciblé (33 trous).

### Template - ISV partner
Un éditeur logiciel partenaire.

Sections : présentation de l'éditeur (avec image), solution, fonctionnalités, **intégration ISV**, **bénéfices utilisateurs**, **compatibilité ERP**, apps Odoo.

Le seul qui garde une image dans son markup.

---

## Comparaison

### Template - Comparison
Odoo face à un concurrent ERP.

Sections : **concurrents ERP en présence**, **critères de décision**, **tableau comparatif**, **verdict**, crédibilité Gold Partner, **autres comparatifs**.

Pour les mots-clés `odoo vs sap`, `odoo vs dynamics`.

### Template - Comparison (CMS)
Structure identique, mais orientée CMS et e-commerce.

Pour `odoo vs shopify`, `odoo vs wordpress`.

---

## Commercial

### Template - Offer
Une offre packagée.

Sections : contexte, **détail de l'offre**, méthodologie, FAQ.

### Template - Customer benefit
Un bénéfice client précis, angle marketing. **Le plus léger du thème** (20 trous).

Sections : **positionnement du bénéfice**, solution, références, témoignages, FAQ.

Le plus rapide et le moins cher à générer.

### Template - Case study
Un cas client.

Sections : **contexte client**, solution, **planning projet**, chiffres clés, citation client, équipes, apps Odoo, liens connexes.

Le seul avec un planning projet. Attention : un cas client contient des faits réels — remplis la **Description** et les **Instructions**, sinon l'IA n'a rien de vrai à mettre.

---

## Ce que tous ont en commun

Chaque template porte les mêmes blocs d'encadrement :

| Bloc | Rôle |
|---|---|
| Page header | le titre et l'accroche |
| Mid CTA | un appel à l'action au milieu |
| CTA + Form | le formulaire de contact final |

Le formulaire porte un `{Short title of the page}` dans un **attribut**, pas dans du texte. Le module le remplit séparément via `_fill_attribute_placeholders()`.

---

## Aucun ne porte d'instructions de build

`cap_builder_prompt` est **vide sur les 17 templates**.

Conséquence : `_get_system_prompt()` utilise toujours le prompt du **modèle IA**. Le mécanisme de remplacement par template existe dans le code mais n'est pas utilisé aujourd'hui.

C'est une opportunité : tu pourrais écrire des instructions propres à chaque template — « une page Case study commence toujours par le contexte client, jamais par la solution » — sans toucher au code, directement dans l'interface.

---

## XML IDs pour l'import

À utiliser dans une colonne `template_page_id/id`. Plus fiable que le nom, qui peut devenir ambigu si le site a personnalisé une page du thème.

| Template | XML ID |
|---|---|
| Home | `cap_web_captivea_theme.page_home` |
| Sector hub | `cap_web_captivea_theme.page_sector` |
| Sub-sector (Industry) | `cap_web_captivea_theme.page_subsector` |
| Team (Business function) | `cap_web_captivea_theme.page_team` |
| About | `cap_web_captivea_theme.page_about` |
| Country | `cap_web_captivea_theme.page_country` |
| Office | `cap_web_captivea_theme.page_office` |
| Odoo Partner (country) | `cap_web_captivea_theme.page_partner` |
| Product pillar (Odoo) | `cap_web_captivea_theme.page_product` |
| Odoo app | `cap_web_captivea_theme.page_app_odoo` |
| Captivea add-on | `cap_web_captivea_theme.page_app_captivea` |
| ISV partner | `cap_web_captivea_theme.page_isv` |
| Comparison | `cap_web_captivea_theme.page_comparison` |
| Comparison (CMS) | `cap_web_captivea_theme.page_comparison_cms` |
| Offer | `cap_web_captivea_theme.page_offer` |
| Customer benefit | `cap_web_captivea_theme.page_benefit` |
| Case study | `cap_web_captivea_theme.page_case_study` |

---

## Comment choisir

| Ton mot-clé ressemble à | Prends |
|---|---|
| `odoo inventory`, `odoo crm` | Odoo app |
| `odoo erp`, `odoo software` | Product pillar (Odoo) |
| `odoo partner france` | Odoo Partner (country) |
| `odoo vs sap` | Comparison |
| `odoo manufacturing`, `odoo retail` | Sub-sector (Industry) |
| `odoo pour directeur financier` | Team (Business function) |
| un nom de client | Case study |
| un bénéfice (`réduire les stocks`) | Customer benefit |
