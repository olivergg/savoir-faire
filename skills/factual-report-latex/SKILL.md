---
name: factual-report-latex
description: >-
  Use this skill when générant des rapports PDF français au style teal via
  LaTeX/tectonic — préambule partagé, macros (infobox/warnbox/ticketbox), ton factuel,
  garde-fous typographiques. Also triggers for: rapport PDF, rapport factuel, LaTeX,
  tectonic, compte-rendu, document PDF, rapport manager, rapport incident.
compatibility: Requires tectonic (LaTeX engine); install with brew install tectonic
metadata:
  author: Olivier G
---

# Factual Report -- LaTeX (style teal)

Workflow rapide pour produire des rapports PDF français avec un style cohérent,
neutre, factuel. Rédiger en français sauf demande contraire. Ne pas modifier le
préambule pour un seul rapport : il est partagé.

`SKILL_DIR` ci-dessous = dossier de ce skill.

## Quand l'utiliser

- L'utilisateur demande un rapport PDF / un rapport pour managers / un compte
  rendu factuel / un argumentaire structuré.
- Plusieurs rapports doivent partager la même identité visuelle.
- L'utilisateur a des données sourcées (notes Markdown, tickets Jira, PRs
  GitHub) et veut une sortie polished.

## Choix de thème

Deux thèmes disponibles. Si l'utilisateur n'en précise pas, demander en
proposant Teal par défaut (Vite Dark si le sujet est technique/sécu/archi).

| Thème | Fichier préambule | Quand l'utiliser |
|---|---|---|
| **Teal** (défaut) | `preamble_teal.tex` | Rapports internes courants, documents partagés en réunion, ton professionnel neutre |
| **Vite Dark** | `preamble_vite_dark.tex` | Rapports techniques, sécurité, architecture — fond sombre `#1b1b1f`, accent violet `#646cff`, magenta `#bd34fe`, cyan `#47caff` |

## Stack technique

- **Moteur LaTeX** : `tectonic` (à installer une fois via `brew install
  tectonic` sur macOS). Pas de TeX Live requis.
- **Compilation** : `tectonic <fichier>.tex` -- sortie `<fichier>.pdf` dans le
  même dossier.
- **Préambule partagé** : `preamble_teal.tex` (thème clair) ou
  `preamble_vite_dark.tex` (thème sombre) -- à copier dans le dossier de
  travail et inclure via `\input{preamble_teal.tex}` ou
  `\input{preamble_vite_dark.tex}`.

## Workflow

1. **Vérifier tectonic** : `which tectonic`. S'il manque, proposer
   `brew install tectonic`.
2. **Préparer le dossier** : copier le préambule du thème dans le dossier de
   sortie (typiquement `~/Desktop/<projet>/` ou un dossier de travail dédié).
3. **Pour chaque rapport** :
   - Définir `\reportTitle` et `\reportSubtitle` (utilisés en en-tête).
   - Appeler `\makeTealTitle{Titre}{Sous-titre}{Encart périmètre}` pour la page
     de garde.
   - Structurer en `\section*{...}` (sections numérotées non utilisées --
     palette propre).
   - Utiliser les boîtes selon l'intention (voir ci-dessous).
4. **Compiler** : `tectonic <fichier>.tex`. Ouvrir avec `open <fichier>.pdf`.

## Boîtes disponibles (préambule teal)

| Boîte         | Couleur cadre         | Usage                                  |
|---------------|-----------------------|----------------------------------------|
| `infobox`     | teal `tealPrimary`    | Synthèse, chiffres clés, observations  |
| `warnbox`     | ambre `warnAmber`     | Mise en garde, point qui doit ressortir|
| `ticketbox`   | teal `tealAccent`     | Cartouche pour un ticket / un sujet    |

```latex
\begin{infobox}
\sffamily Texte neutre ou tableau de chiffres.
\end{infobox}

\begin{warnbox}
\sffamily Point important / nuance à ne pas manquer.
\end{warnbox}

\begin{ticketbox}{PROJ-123 -- Titre du sujet}
Détail du sujet.
\end{ticketbox}
```

## Conventions de ton

Voir `references/TONE.md` pour le détail. En bref :

- **Factuel et sourcé** : chaque chiffre cité doit être traçable (API Jira,
  GitHub, fichier source, Slack identifiable).
- **Neutre** : pas de jugement personnel sur les individus. La charge est
  portée par les faits, pas par l'adjectif.
- **Pas de "Conclusion" par défaut** : ne pas clôturer par une conclusion
  moralisatrice ni par un "ce qu'il faudrait faire" sauf demande explicite de
  l'utilisateur. La synthèse est portée par la première section.
- **Pas de référence externe à charge** (vidéos polémiques, citations
  d'opinion). Une référence bibliographique académique est en revanche
  bienvenue (ex.\ Polya, *How to Solve It*).

## Pièges à éviter (impérieux)

Voir `references/GOTCHAS.md` pour le détail. Liste courte :

1. **Guillemets français** : toujours `\og X\fg{}` -- jamais les
   caractères bruts `«` et `»`. En LM Sans bold à grande taille, certains
   slots ne sont pas mappés et tectonic substitue depuis une police où
   `0xAB`/`0xBB` tombent sur `ń`/`ż`.
2. **Tableaux `l r`** : ne pas mettre de texte long dans la colonne droite
   (pas de wrap, overflow garanti). Sortir les lignes longues sous le tableau.
3. **`ticketbox` avec virgule dans le titre** : déjà géré dans le préambule
   via `title={#2}`. Si tu redéfinis la boîte ailleurs, garde les braces.
4. **Floats pgfplots** : utiliser `[!htbp]`, pas `[!h]` seul. Le package
   `placeins[section]` est chargé pour confiner les floats à leur section.
5. **Sections risquant d'être orphelines** : préférer
   `\FloatBarrier\needspace{12\baselineskip}` à `\clearpage` (sauf avant un
   environnement `landscape`).
6. **Em-dash `—`** : utiliser `---` (compatibilité T1), pas le caractère
   Unicode.
7. **Images** : `\graphicspath{{/absolute/path/}}` avec chemin absolu --
   tectonic ne résout pas les chemins relatifs ambigus.

## Templates

- `references/templates/minimal.tex` -- squelette minimal d'un rapport (les deux thèmes).
- `references/templates/timeline.tex` -- modèle avec longtable de chronologie (teal uniquement : couleurs `teal*`).
- `references/templates/stats.tex` -- modèle avec infobox de chiffres + tabular zebra (teal uniquement).
- `references/TIKZ_ADVANCED.md` -- patterns TikZ réutilisables pour diagrammes/annotations avancées, à charger si le rapport a besoin d'un schéma custom.

## Bootstrap rapide

**Thème teal (défaut) :**
```bash
cp "$SKILL_DIR"/references/preamble_teal.tex .
cp "$SKILL_DIR"/references/templates/minimal.tex mon_rapport.tex
tectonic mon_rapport.tex && open mon_rapport.pdf
```

**Thème Vite Dark :**
```bash
cp "$SKILL_DIR"/references/preamble_vite_dark.tex .
cp "$SKILL_DIR"/references/templates/minimal.tex mon_rapport.tex
# Dans mon_rapport.tex : remplacer \input{preamble_teal.tex}
#                    par \input{preamble_vite_dark.tex}
# Remplacer \makeTealTitle{...} par \makeViteDarkTitle{Titre}{Sous-titre}{encart}
tectonic mon_rapport.tex && open mon_rapport.pdf
```

**Macros par thème :**

| Teal | Vite Dark | Rôle |
|---|---|---|
| `\makeTealTitle{T}{ST}{encart}` | `\makeViteDarkTitle{T}{ST}{encart}` | Page de titre |
| `infobox warnbox ticketbox{titre}` | idem + `successbox notebox` | Boîtes |
| -- | `\verfrom{x}` / `\verto{x}` | Version avant (grisé) / après (coloré) |
| -- | `\cA \cB \cC \cG \cO \cT`, `\kw`, `\mono` | Accents inline |
| -- | `\crit \ok \warn`, `\badge \badgecrit \badgeok` | Statuts |
| -- | `zebratable`, `\headrow`, `\thd` | Tableaux |

## Sources de données complémentaires

Lorsqu'un rapport doit s'appuyer sur des données externes vérifiables, ce skill
combine bien avec :

- API Jira -- changelogs, transitions, worklogs, détails d'un ticket.
- `gh` CLI (GitHub) -- pour les PRs, reviews, commits, line comments.
- Métriques / logs de prod -- pour les rapports d'incident.

Citer la source dans chaque rapport (encart de tête : `\og Source : ...\fg{}`).
