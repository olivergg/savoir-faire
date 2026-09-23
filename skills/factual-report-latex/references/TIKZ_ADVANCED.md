# TikZ avancé -- patterns qui se sont bien passés

Apprentissages tirés d'un diagramme d'architecture d'intégration. Patterns réutilisables et subtilités découvertes.

---

## 1. Annotation fine avec ligne pointillée grise

**Objectif** : ajouter une "annotation" ou "liaison" visuelle (pas un flux directionnel) entre deux éléments.

**Pattern** : ligne pointillée fine, couleur grise pâle, pas de flèche.

```latex
% ✅ Annotation subtile (pas un flux)
\draw[line width=0.6pt, color=ruleGray!50, dashed, to path={.. controls ++(1.5,0.6) and ++(-1.2,-0.6) .. (\tikztotarget)}]
  (0.8, -0.95) to (ZBOX.south west);
```

**Différence sémantique** :
- Flèche pleine `aflow` → **flux de données** directionnel
- Ligne pointillée grise fin → **précision** ou **annotation** sur un sujet

Utile pour :
- Montrer le "format détaillé" d'un message sans confusion avec le routage
- Liens de documentation ou clarification
- Références croisées non-causales

---

## 2. Courbes Bezier avec `to path` pour éviter les occlusions

**Objectif** : faire une flèche ou ligne qui contourne des éléments sans les chevaucher.

**Pattern** : utiliser `to path={.. controls ++(dx1,dy1) and ++(dx2,dy2) .. (\tikztotarget)}`

```latex
% Courbe Bezier partant du point (0.8, -0.95) vers ZBOX.south west
\draw[dashed, to path={.. controls ++(1.5,0.6) and ++(-1.2,-0.6) .. (\tikztotarget)}]
  (0.8, -0.95) to (ZBOX.south west);
```

**Comment ça marche** :
- `..` = interpolation lisse
- `controls ++(dx1,dy1) and ++(dx2,dy2)` = points de contrôle Bezier (relatif au point de départ et d'arrivée)
- `(\tikztotarget)` = destination finale

**Réglage** :
- ↑ `dy1` = courbe monte plus
- → `dx1` = courbe s'écarte latéralement du départ
- Essayer des valeurs `(1.5, 0.6)` et `(-1.2, -0.6)` comme point de départ

---

## 3. Boîtes TikZ compactes pour zoom/annotation

**Objectif** : créer une petite boîte d'annotation (format, détail, légende) sans surcharger.

**Pattern** :

```latex
\node[rectangle, draw=tealPrimary, fill=tealPale, line width=0.8pt, rounded corners=2pt,
       inner sep=3pt, font=\tiny\ttfamily] (ZBOX) at (10.0, 0.5) {%
\begin{tabular}[c]{@{}l@{}}
champ1, \\
champ2, \\
\textcolor{newRed}{\bfseries +\ nouveau}
\end{tabular}};
```

**Points clés** :
- `font=\tiny\ttfamily` → très petit, monospace
- `inner sep=3pt` → padding serré
- `tabular[c]{@{}l@{}}` → pas d'espaces extra, une colonne gauche
- `\textcolor{newRed}{\bfseries +\ nouveau}` → highlight le nouveau champ en rouge+bold

---

## 4. Labels flottants avec node sur arête

**Objectif** : placer un petit label (ex. "publish") sur une arête sans interfère.

**Pattern** :

```latex
\draw[aflow] (PROD)--(TOUT) node[tag,midway,right]{publish};
```

**Variantes** :
- `node[...,midway,right]` → label à droite du point milieu
- `node[...,pos=0.42,above]` → label à 42% du chemin, au-dessus
- `\texttt{provider}=B` → monospace pour les identifiants

---

## 5. Boîtes de style `app`, `topic`, `proc` -- réutiliser les styles partagés

**Objectif** : diagramme cohérent avec couleurs et apparence uniformes.

**Pattern** : définir une fois dans `\tikzset`, réutiliser partout.

```latex
\tikzset{
  app/.style   ={rectangle, rounded corners=2pt, draw=tealDark, fill=white,
                 line width=0.8pt, align=center, text width=33mm, minimum height=10mm, inner sep=3pt},
  topic/.style ={rectangle, rounded corners=7pt, draw=tealAccent, fill=tealBand,
                 line width=0.8pt, align=center, text width=40mm, minimum height=9mm, inner sep=3pt},
  proc/.style  ={rectangle, rounded corners=2pt, draw=tealPrimary, fill=tealPale,
                 line width=0.8pt, align=center, text width=38mm, minimum height=10mm, inner sep=3pt},
  new1/.style  ={rectangle, rounded corners=2pt, draw=newRed, fill=white,
                 line width=1pt, align=center, text width=35mm, minimum height=10mm, inner sep=3pt},
}

\node[app] (P) at (0,0) {Producteurs};
\node[topic] (T) at (0,-1.9) {messages-out (Avro)};
\node[new1] (N) at (4.8,-1.9) {Adaptateur REST B};
```

**Avantage** : cohérence visuelle + maintenance facile (changement globale = une seule édition).

---

## 6. Arêtes avec styles nommés

**Objectif** : flux directionnel (fournisseur A vs fournisseur B) distincts visuellement.

**Pattern** :

```latex
\tikzset{
  aflow/.style ={-{Stealth[length=2.2mm]}, line width=1pt, draw=tealPrimary},
  nflow/.style ={-{Stealth[length=2.2mm]}, line width=1pt, draw=newRed},
  bflow/.style ={-{Stealth[length=2.2mm]}, line width=1pt, draw=tealAccent},
  rlink/.style ={-{Stealth[length=2.2mm]}, line width=0.8pt, draw=warnAmber},
}

\draw[aflow] (TOUT)--(KAN);  % flux fournisseur A : teal
\draw[nflow] (TOUT)--(REST); % flux fournisseur B : red
```

---

## 7. Position relative + `\phantom` pour alignement tabular-like

**Objectif** : boîtes zooms avec plusieurs lignes alignées sans tabular lourd.

**Pattern** : `\phantom{}` pour ajouter espace invisible, puis contenu.

```latex
\node[infobox] at (9.5, 0.5) {%
\ttfamily\small
\{ \\
\phantom{xx}gateway : string | null, \\
\phantom{xx}timestamp : long, \\
\phantom{xx}\textcolor{newRed}{provider : string | null} \\
\}
};
```

**Pourquoi** : `\phantom{xx}` ajoute largeur d'indentation sans afficher le texte. Propre et compact.

---

## 8. Gestion des Z-layers et occlusion

**Objectif** : s'assurer qu'une courbe Bezier ne passe pas *sous* une boîte.

**Pattern** : dessiner les arêtes avant les boîtes de destination, ou utiliser `behind` / `in front of` paths.

```latex
% Order importera : boîtes d'abord (fond), puis arêtes (dessus)
% OU
\begin{scope}[behind path]
\draw[dashed] (A) to (B);
\end{scope}
\node[box] at (C) {…};
```

**Astuce** : en général, dans TikZ SVG-like, l'ordre de déclaration = ordre de dessin. Déclarer les éléments de fond d'abord.

---

## 9. Positionner des boîtes dans le coin supérieur sans dépasser

**Objectif** : annotation en haut à droite, sans se chevaucher le reste du diagramme.

**Pattern** : utiliser coordonnées absolues hors du "centre" du diagram.

```latex
% Zoom box en haut à droite, loin du flux principal
\node[rectangle, ..] (ZBOX) at (10.0, 0.5) {…};

% Puis lier depuis le flux principal
\draw[dashed, to path={.. controls ++(1.5,0.6) and ++(-1.2,-0.6) .. (\tikztotarget)}]
  (0.8, -0.95) to (ZBOX.south west);
```

Avantage : boîte "flotte" à l'écart, visible et non-occluse.

---

## 10. Bandeaux texte rotatés (rotate=90)

**Objectif** : ajouter une légende verticale (ex. "EXISTANT (réutilisé)").

**Pattern** :

```latex
\node[font=\footnotesize\sffamily\bfseries, text=tealPrimary, rotate=90] 
  at (-2.0,-6.0) {EXISTANT (réutilisé)};
```

**Attention** : le `rotate=90` tourne le texte sur place. Positionner avec `at (x,y)` et vérifier le placement visuel.

---

## Checklist pour le prochain diagramme TikZ complexe

- [ ] Définir `\tikzset` styles au début (app, topic, proc, new1, aflow, nflow)
- [ ] Noeuds d'abord, sans arêtes (fond)
- [ ] Arêtes ensuite (dessus)
- [ ] Vérifier les occlusions : faire une courbe Bezier si une arête traverse une boîte
- [ ] Pour annotation (pas flux) : ligne grise fin pointillée, sans flèche
- [ ] Petites boîtes de détail/format : `\tiny\ttfamily`, tabular compact
- [ ] Tester le rendu PDF et zoomer pour vérifier lisibilité
- [ ] Pas de label chevauchant : utiliser `node[...,midway,right/above]` ou décaler

