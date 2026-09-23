# Pièges accumulés -- factual-report-latex

Liste des erreurs rencontrées en production et leur correction. Lire avant de
rédiger un nouveau rapport.

---

## 1. Guillemets français rendus en caractères polonais

**Symptôme** : dans le PDF, `« mot »` apparaît comme `ń mot ż`.

**Cause** : en LM Sans bold à grande taille (titres, sous-titres,
`\Huge\sffamily\bfseries`), les slots `0xAB`/`0xBB` de la police courante ne
sont pas mappés. Tectonic substitue depuis une police où ces slots tombent sur
`ń`/`ż` (latin-2).

**Correction** : utiliser systématiquement les macros babel français :

```latex
% ❌ Bug : caractères bruts
Pourquoi un ticket « fait en quelques jours » paraît avoir pris des semaines

% ✅ OK : macros babel
Pourquoi un ticket \og fait en quelques jours\fg{} paraît avoir pris des semaines
```

**Sweep préventif** :

```bash
grep -n '«\|»' *.tex   # doit retourner 0 résultat
```

Si des « » sont introduits par erreur (copier-coller depuis un .md), un
remplacement global :

```python
import re, pathlib
pat = re.compile(r'«\s*(.+?)\s*»', re.DOTALL)
for f in pathlib.Path('.').glob('*.tex'):
    s = f.read_text()
    if pat.search(s):
        f.write_text(pat.sub(r'\\og \1\\fg{}', s))
```

---

## 2. Tableau `l r` -- overflow de la colonne droite

**Symptôme** : dans un `\begin{tabular}{l r}`, une ligne dont la valeur droite
est longue déborde au-delà du cadre `tcolorbox`.

**Cause** : la colonne `r` est right-aligned non wrappée. LaTeX ne casse pas
le texte long en plusieurs lignes -- il l'écrit en une seule ligne qui
dépasse.

**Correction** : sortir les lignes longues hors du tabular, en lignes pleine
largeur sous le tableau.

```latex
% ❌ Bug : overflow
\begin{tabular}{@{}l@{\hspace{2em}}r@{}}
Période          & janv.\ -- juin \\
Éléments         & 25 \\
Catégories       & catégorie A, catégorie B, catégorie C, catégorie D \\
\end{tabular}

% ✅ OK : sortir la ligne longue
\begin{tabular}{@{}l@{\hspace{2em}}r@{}}
Période   & janv.\ -- juin \\
Éléments  & 25 \\
\end{tabular}\\[6pt]
\textbf{Catégories} : catégorie A, catégorie B, catégorie C, catégorie D.
```

Alternative si tu veux garder le tableau : utiliser `tabularx` ou une colonne
`p{...}`. Mais la solution ci-dessus est plus lisible et plus robuste.

---

## 3. `tcolorbox` avec virgule dans le titre

**Symptôme** : erreur de compilation
`Package pgfkeys Error: I do not know the key '/tcb/X'`.

**Cause** : `tcolorbox` parse l'argument titre via `pgfkeys` qui interprète
les virgules comme séparateurs de clés. Donc
`\begin{ticketbox}{4 éléments (2 ouverts, 2 fermés)}` casse.

**Correction** : dans la définition de la boîte, encadrer `#2` par des
braces.

```latex
% ❌ Bug : virgule prise comme séparateur
\newtcolorbox{ticketbox}[2][]{
  title=#2,
  ...
}

% ✅ OK : braces autour de #2
\newtcolorbox{ticketbox}[2][]{
  title={#2},
  ...
}
```

Déjà appliqué dans `preamble_teal.tex` fourni avec ce skill.

---

## 4. Floats pgfplots qui dérivent + pages blanches

**Symptôme** : une figure pgfplots apparaît 3 pages plus loin que sa
section, ou crée une page blanche.

**Cause** : `[!h]` est trop restrictif. Si LaTeX ne peut pas placer ici, il
empile. À l'inverse, sans contrainte, une figure peut sauter sa section.

**Correction** :

1. Utiliser `[!htbp]` -- laisse plus de marges de placement.
2. Charger `placeins[section]` -- ajoute un `\FloatBarrier` implicite à
   chaque `\section` (figures confinées à leur section).
3. Pour les transitions entre blocs sensibles, préférer
   `\FloatBarrier\needspace{12\baselineskip}` à `\clearpage`.

```latex
\usepackage[section]{placeins}
\usepackage{needspace}

% Avant une nouvelle section longue :
\FloatBarrier
\needspace{12\baselineskip}
\section*{Année 2024}
```

---

## 5. Em-dash Unicode manquant

**Symptôme** : warning compile `Missing character: There is no — ("2014) in
font ec-lmr10`. Le caractère apparaît mal ou pas du tout.

**Cause** : T1/EC ne contient pas systématiquement l'em-dash Unicode
`U+2014`.

**Correction** : remplacer `—` (caractère Unicode) par `---` (séquence
LaTeX). En français on utilise plus souvent `--` (en-dash) pour les
incises.

```latex
% ❌
Pour ce module — qui est ancien

% ✅
Pour ce module --- qui est ancien
```

---

## 6. Images via chemin relatif ambigu

**Symptôme** : `! LaTeX Error: File 'foo.png' not found.`

**Cause** : tectonic résout les chemins relatifs au `.tex` -- mais si les
images sont dans un autre dossier (ex.\ `~/Documents/NOTES/X/`), il faut le
déclarer.

**Correction** :

```latex
\graphicspath{{/Users/me/Documents/NOTES/incident-X/}}
% puis
\includegraphics[width=0.8\textwidth]{schema.png}
```

Chemin absolu, double-braces autour. Ne pas oublier le `/` final.

---

## 7. Page de garde + `fancyhdr` warning duplicate `@page.1`

**Symptôme** : warning compile `Object @page.1 already defined`.

**Cause** : interaction `titlepage` + `fancyhdr`. Cosmétique, n'affecte pas
le rendu.

**Correction** : ignorer. Si génant, supprimer le `\thispagestyle{empty}` à
l'intérieur du `titlepage` -- mais ça repermet le footer sur la garde.

---

## 8. Cohérence des guillemets après replace global

**Symptôme** : après un sweep `«…»` → `\og…\fg{}`, certaines occurrences
restent (titres `\newcommand{\reportTitle}{...}` non scannés par la regex
non-greedy).

**Correction** : vérifier après chaque sweep :

```bash
grep -rn '«\|»' .
```

Doit retourner 0 résultat.

---

## 9. Score / Lorenz -- métriques sans sens

**Symptôme** : on inclut "mois actifs" dans un score composite ou une
Lorenz.

**Cause** : "mois actifs" est cumulatif et dépend de la fenêtre d'analyse,
pas de la concentration d'effort. Aucune information utile n'en sort.

**Correction** : pour un score d'activité ou une Lorenz, retenir uniquement
des métriques de **production** (commits, tickets, dépôts touchés). Pas le
temps de présence.

---

## 10. "Conclusion" parachutée

**Symptôme** : on termine un rapport par "Conclusion" / "Ce qu'il faudrait
faire" -- ton moralisateur, lecture comme prescription.

**Correction** : ne pas ajouter de section "Conclusion" ni de plan
d'action par défaut. La synthèse est dans la première section. Le lecteur
tire les conclusions à partir des faits. Si l'utilisateur veut un plan
d'action, il le demandera explicitement.
