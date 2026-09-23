# Conventions de ton -- factual-report-latex

Le style de rapport produit par ce skill est **factuel, neutre, sourcé**. Il
peut défendre une thèse, mais la charge est portée par les faits, pas par
l'adjectif.

---

## Principes

### 1. Sourcer chaque chiffre

Tout nombre cité dans un rapport doit être traçable :

- API Jira (changelog, worklog, transitions) -- mentionner le ticket.
- API GitHub (PRs, reviews, commits) -- mentionner repo + PR number.
- Fichier source local -- mentionner le nom.
- Slack -- mentionner que c'est issu d'une conversation et la fenêtre
  temporelle.

Un rapport sans source est un rapport non défendable.

### 2. Préférer la description factuelle au qualificatif

| ❌ Évite                             | ✅ Préfère                                          |
|-------------------------------------|----------------------------------------------------|
| "trompeur"                          | "intermittent et difficile à reproduire"           |
| "tests trompeurs"                   | "couverture de test inopérante"                    |
| "fausse confiance"                  | "validait le comportement défectueux comme attendu"|
| "communication décalée"             | "écart entre la communication et le comportement"  |
| "factuellement incorrect"           | "non vérifié par les faits ci-dessus"              |
| "le plus préoccupant"               | (supprimer le superlatif)                          |
| "ne fonctionne pas"                 | "conduit régulièrement à [observation chiffrée]"   |
| "stagne"                            | "n'a pas progressé sur la fenêtre observée"        |
| "il faut ABSOLUMENT"                | "le sujet mérite d'être tranché"                   |

### 3. Pas de jugement sur les individus

Les rapports décrivent **des situations, des processus, des décisions** -- pas
des personnes.

- ❌ "X ne comprend pas l'architecture"
- ✅ "Sur N tickets, le pattern Y existant n'a pas été utilisé"

Quand un nom doit apparaître (rapporteur, assignee, auteur d'un commit), c'est
factuel et sourcé -- pas une accusation.

### 4. Pas de référence externe à charge

- ❌ Lien vers une vidéo polémique avec titre négatif.
- ❌ Citation d'un influenceur tech qui partage l'opinion défendue.
- ✅ Référence bibliographique académique (livre, article de recherche).

Exemple acceptable : *How to Solve It* de Polya, en référence sur la
reformulation des problèmes.

### 5. Pas de "Conclusion" ni "Plan d'action" par défaut

Ne pas clôturer un rapport par :

- Une section "Conclusion" qui répète la synthèse.
- Une section "Ce qu'il faudrait faire" / "Recommandations".

**Pourquoi** : ces sections transforment le rapport en prescription. Or le
rapport doit présenter des faits ; les décisions appartiennent à son
destinataire. La synthèse est dans la première section (encart titre + section
de tête).

Exception : si l'utilisateur demande explicitement un plan d'action.

### 6. Mises en garde maîtrisées

Le `warnbox` (cadre ambre) doit être réservé aux points qui **doivent**
ressortir visuellement, et leur formulation doit rester factuelle.

- ❌ "ATTENTION : cette pratique aggrave le problème !"
- ✅ "Constat : les exemples ci-dessus montrent que cette pratique conduit
     à [observations chiffrées]."

### 7. Cadrer ce que le rapport n'est PAS

Sur les sujets sensibles (organisation, processus contestés), inclure une section ou un paragraphe **"Ce que ce rapport n'est pas"** :

- Évite que le lecteur projette une interprétation maximaliste.
- Renforce la crédibilité (l'auteur a anticipé les contre-arguments).
- Permet de défendre la thèse sans tomber dans l'attaque.

Exemple :

```latex
\section*{Ce que ce rapport n'est pas}
\begin{itemize}
\item Pas une évaluation individuelle.
\item Pas une demande de changement d'outil.
\item Pas un événement isolé.
\end{itemize}
```

### 8. Cohérence entre rapports d'un même corpus

Si plusieurs rapports défendent une argumentation commune, les rapports se
réfèrent l'un à l'autre par leur nom court (ex.\ "voir rapport A",
"complémentaire du rapport B"). Cela renforce la cohérence sans
dupliquer le contenu.

---

## Anti-modèles concrets observés

### Anti-modèle 1 -- la note polémique

Une section qui :

- Pointe nommément la pratique d'une personne ou d'une équipe.
- Cite un contenu populaire à titre négatif.
- Conclut sur un superlatif émotionnel.

À refondre en : exposé des observations + explication structurelle (ce qui,
dans le processus, produit ce résultat) + extension au moyen terme.

### Anti-modèle 2 -- la conclusion moralisatrice

```latex
% ❌
\section*{Conclusion}
Ces chiffres montrent clairement que l'approche actuelle est un échec et
qu'il faut absolument la revoir...
```

À supprimer. Le constat est porté par la section "Récurrence des problèmes"
qui précède, avec ses chiffres.

### Anti-modèle 3 -- l'asymétrie comme dévalorisation

```latex
% ❌
\section*{Constat -- contraste avec les sujets "rapides"}
Le sujet B, lui, a été traité sans difficulté.
% (sous-entend que le sujet B est un mauvais sujet, ce qui n'est pas le propos)
```

À refondre en :

```latex
% ✅
\section*{Constat -- asymétrie de traitement}
Le point n'est pas de dire qu'un autre sujet (comme B) n'est pas important.
Il l'est. L'observation porte sur le fait que, dans l'absolu, tous les sujets
ne reçoivent pas le même traitement.
```

---

## Checklist avant publication

- [ ] Aucun `«` ou `»` brut (uniquement `\og\fg{}`).
- [ ] Aucun em-dash `—` (uniquement `---` ou `--`).
- [ ] Chaque chiffre cité a une source identifiable.
- [ ] Aucune section "Conclusion" ni "Plan d'action" non demandée.
- [ ] Aucun jugement nominatif sur un individu.
- [ ] Aucun superlatif émotionnel ("le plus préoccupant", "totalement
      inadapté", "absolument").
- [ ] Le rapport inclut une section "Ce que ce rapport n'est pas" si le sujet
      est sensible.
- [ ] Les tables `l r` n'ont pas de texte long en colonne droite.
