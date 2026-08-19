# Plan d'implémentation — Onglet « Lucide » dans le sélecteur de médias (Odoo 19)

Objectif : ajouter un onglet **Lucide** dans le média-dialog du website builder (à côté de *Images* et *Icons*), qui insère des **icônes Lucide en SVG**, servies via un **sprite** référencé par `<use>`. Aucune modification du set Font Awesome existant.

Approche validée : **SVG sprite + `<use>` externe**, onglet ajouté via le hook **officiel** `media_dialog_extra_tabs` (pas d'override du composant `MediaDialog`).

---

## 1. Faits établis sur Odoo 19 (source vérifiée)

- Le rich-text editor vit désormais dans le module **`html_editor`** (plus `web_editor`).
- Média-dialog : `addons/html_editor/static/src/main/media/media_dialog/media_dialog.js`, template OWL `html_editor.MediaDialog` (rend les onglets via `<Notebook>` → un nouvel onglet est pris en compte automatiquement, **pas de `t-inherit`** nécessaire).
- Sélecteur d'icônes : composant **`IconSelector`** (`.../media_dialog/icon_selector.js`, template `html_editor.IconSelector`). Il insère un `<span class="fa fa-...">`.
- Les onglets de base sont un objet exporté `TABS` (`IMAGES`, `ICONS`). Le `MediaDialog` accepte une prop `extraTabs` et le **plugin** `media_plugin.js` expose la ressource :

  ```
  media_dialog_extra_tabs : { id, title, Component, sequence }[]
  ```

  → La façon supportée d'ajouter un onglet est de fournir cette ressource depuis un **Plugin** de l'éditeur. Aucun override.
- Chaque composant d'onglet définit un `static createElements(selectedMedia, {orm})` qui construit et retourne les éléments DOM insérés (appelé par `MediaDialog.renderMedia()`), plus des statiques : `mediaSpecificClasses`, `mediaExtraClasses`, `mediaSpecificStyles`, `tagNames` (utilisés par la logique de nettoyage inter-onglets).
- Bundle dédié : **`html_editor.assets_media_dialog`** (inclus dans `web.assets_frontend`, `web.assets_backend`, `html_editor.assets_editor`). Nos fichiers JS/XML de l'onglet doivent être inclus dans ce bundle.
- **Point de vigilance** : `MediaDialog.save()` a un cas particulier codé en dur pour `TABS.ICONS` (`initialIconChanged`), et `clean_for_save` / `isIconElement` (`html_editor/static/src/utils/dom_info.js`) traite spécialement les « éléments icône » (force `​` + `contenteditable=false`). Un `<svg>` inline ne correspond pas à `isIconElement` → il faut **vérifier que le SVG survit à la sauvegarde** (voir §6).

---

## 2. Où héberger le code

Dans **`cap_web_captivea_theme`** (pas de module séparé nécessaire).

- Ajouter `'html_editor'` à `depends` du manifest (déjà tiré transitivement par `website`, mais on l'explicite car on cible ses bundles/registres).

---

## 3. Fichiers à créer

```
cap_web_captivea_theme/
├── static/
│   ├── lib/lucide/
│   │   └── lucide-sprite.svg              # sprite généré (<symbol id="lucide-*">)
│   └── src/
│       ├── js/editor/
│       │   ├── lucide_icons.js            # liste des noms d'icônes (métadonnées grille)
│       │   ├── lucide_selector.js         # composant OWL LucideSelector
│       │   └── lucide_media_tab_plugin.js # Plugin -> resource media_dialog_extra_tabs
│       ├── xml/editor/
│       │   └── lucide_selector.xml         # template t-name="cap_web_captivea_theme.LucideSelector"
│       └── scss/
│           └── lucide.scss                 # style .o_lucide_icon (frontend + éditeur)
├── tools/
│   └── build_lucide_sprite.py             # script de génération du sprite (hors module)
└── docs/lucide_icons_plan.md
```

---

## 4. Génération du sprite (`tools/build_lucide_sprite.py`)

Source des SVG : package npm **`lucide-static`** (SVG officiels, un fichier par icône, `stroke="currentColor"`, `fill="none"`, `stroke-width="2"`, `viewBox="0 0 24 24"`).

Le script :
1. lit chaque `*.svg` de `lucide-static/icons/`,
2. extrait le contenu interne + le `viewBox`,
3. émet un `<symbol id="lucide-<nom>" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">…paths…</symbol>`,
4. concatène tout dans `static/lib/lucide/lucide-sprite.svg` enveloppé d'un `<svg xmlns=... style="display:none">`.

Optionnel : ne garder qu'un **sous-ensemble** d'icônes (celles utiles au site) pour alléger le sprite. Décision produit : partir sur un sous-ensemble curé (~150) plutôt que les ~1 500 Lucide, pour limiter le poids et la latence du picker.

---

## 5. Le composant `LucideSelector` (OWL)

Calqué sur `IconSelector`. Props reçues du `MediaDialog` : `selectMedia`, `save`, `media`, `errorMessages`, etc.

Statics requis (pour la logique de nettoyage du dialog) :

```js
static mediaSpecificClasses = ["o_lucide_icon"];
static mediaSpecificStyles  = ["color"];
static mediaExtraClasses     = [/^text-\S+$/, /^bg-\S+$/];
static tagNames              = ["SPAN"];
static template = "cap_web_captivea_theme.LucideSelector";
```

`createElements` — construit le markup inséré (span wrapper + svg + use externe) :

```js
static createElements(selectedMedia) {
    return selectedMedia.map((icon) => {
        const span = document.createElement("span");
        span.className = "o_lucide_icon";
        span.setAttribute("contenteditable", "false");   // protège le SVG à l'édition
        span.innerHTML =
          `<svg aria-hidden="true"><use href="/cap_web_captivea_theme/static/lib/lucide/lucide-sprite.svg#lucide-${icon.name}"/></svg>`;
        return span;
    });
}
```

Comportement UI : champ de recherche (comme `SearchMedia`), grille cliquable ; `onClickIcon(icon)` appelle `this.props.selectMedia({ name: icon.name, fontBase: "o_lucide_icon" })` puis `this.props.save()`.

Template `cap_web_captivea_theme.LucideSelector` : reprend la structure de `html_editor.IconSelector` (panneau recherche + grille `t-foreach` sur les icônes filtrées, chaque cellule affiche le SVG via `<use>` et gère le clic).

---

## 6. Survie à la sauvegarde (risque principal)

Le sanitizer `clean_for_save` peut altérer/supprimer du SVG inline non reconnu. Mitigations, par ordre de préférence :

1. **`contenteditable="false"`** sur le wrapper `.o_lucide_icon` (le contenu protégé est généralement préservé tel quel).
2. Si insuffisant, ajouter la classe `o_not_editable` et/ou `data-oe-protected="true"` sur le wrapper.
3. En dernier recours : contribuer une ressource au plugin `clean_for_save`/aux allow-list du sanitizer du `html_editor` pour whitelister `svg`/`use`.

**À valider impérativement sur Odoo.sh** : insérer → sauvegarder → recharger la page publique → le `<svg><use>` doit persister à l'identique.

---

## 7. SCSS (`lucide.scss`) — frontend + éditeur

```scss
.o_lucide_icon {
    display: inline-flex;
    vertical-align: -0.125em;
    svg { width: 1em; height: 1em; stroke: currentColor; }
}
```

Réutiliser le design « cercle rouge + halo » actuel : dans `theme.scss`, ajouter `.o_lucide_icon` **à côté** de `.fa` dans les règles concernées (`main .fa`, `%fa-hover`, hover carte, et le reset `.btn .fa`). Ainsi les icônes Lucide héritent du même style que les FA sans duplication.

`lucide.scss` va dans `web.assets_frontend` (rendu public) ET dans `html_editor.assets_media_dialog` (aperçu grille dans le picker).

---

## 8. Manifest — assets

```python
'depends': ['website', 'html_editor'],
'assets': {
    'html_editor.assets_media_dialog': [
        'cap_web_captivea_theme/static/src/js/editor/**/*',
        'cap_web_captivea_theme/static/src/xml/editor/**/*',
        'cap_web_captivea_theme/static/src/scss/lucide.scss',
    ],
    'web.assets_frontend': [
        'cap_web_captivea_theme/static/src/scss/lucide.scss',
    ],
},
```

(Le plugin s'enregistre dans le registre des plugins de l'éditeur via son import ; s'assurer que `lucide_media_tab_plugin.js` fait bien le `registry.category("...").add(...)` attendu par `html_editor`.)

---

## 9. Rendu public / SEO

- Markup final : `<span class="o_lucide_icon"><svg aria-hidden="true"><use href="/cap_web_captivea_theme/static/lib/lucide/lucide-sprite.svg#lucide-camera"/></svg></span>`.
- Sprite servi en statique (cacheable, une seule requête, partagée entre pages) → HTML léger, pas de police bloquante, pas de CLS, net en retina.
- `aria-hidden="true"` car décoratif ; si une icône porte du sens, prévoir `role="img"` + `<title>` dans le `<symbol>`.
- Référence `<use>` externe même origine : OK navigateurs modernes ; `currentColor` fonctionne via la couleur CSS héritée.

---

## 10. Risques & dépendance de version

- Les internes de `html_editor` (objet `TABS`, ressource `media_dialog_extra_tabs`, signature `createElements`) sont **spécifiques à 19.0** ; à revérifier à chaque montée de version majeure. Le hook `media_dialog_extra_tabs` est néanmoins le point d'extension prévu → risque bien plus faible qu'un patch de composant.
- Impossible de tester le patch OWL ici : la validation se fait sur Odoo.sh (build + éditeur).

---

## 11. Chantier connexe (à trancher séparément)

L'onglet Lucide **ne corrige pas** les icônes déjà cassées des snippets (noms Font Awesome 6 non reconnus par le FA 4.7 d'Odoo). Deux options, indépendantes de ce plan :

- **A.** Migrer les icônes des snippets `s_cap_*` vers Lucide une fois l'onglet/sprite prêts (table de correspondance FA→Lucide dans le générateur).
- **B.** Remapper immédiatement les noms FA6 → FA4.7 dans le générateur, en attendant.

Recommandation : **B en dépannage court terme**, puis **A** comme cible.

---

## 12. Séquencement proposé

1. `build_lucide_sprite.py` + génération du sprite (sous-ensemble curé).
2. `LucideSelector` (JS + XML) + `lucide_icons.js`.
3. Plugin `media_dialog_extra_tabs`.
4. `lucide.scss` + hooks dans `theme.scss` + entrées manifest.
5. Build Odoo.sh + tests éditeur/sauvegarde/rendu public (§6, §9).
6. (Connexe) décision A/B pour les snippets.
