# Registre des sources

| Source | Statut | Mode | Limite connue |
|---|---|---|---|
| Cour constitutionnelle | active | HTML public, texte intégral | pagination à surveiller |
| OpenDataMoroccanLaw | active | dataset public en streaming, CC-BY-4.0 | republication secondaire, pas d'URL par décision |
| Juriscassation | expérimentale | parseur métadonnées/extraits | TLS non validé hors navigateur, texte derrière code |
| Adala | catalogue | renvoi vers Juriscassation | pas de corpus distinct identifié |
| Portail des jugements | suspendue | ancien endpoint JSON | protection TSPD et filtres incohérents |
| Cour constitutionnelle - PDF | active | recueils officiels publics | 2 recueils découverts sur la page institutionnelle |
| MarocDroit - PDF | secondaire | pièces jointes publiques | 4 décisions initiales, inventaire à étendre |
| MarocDroit - recherche PDF | active | recherche publique paginée, articles, pièces jointes | filtre décisions/recueils ; revue secondaire obligatoire |
| jurisprudence.ma - PDF | interdite | routes PDF privées | `robots.txt` interdit explicitement `?pdf=` |

Le statut `suspendue` signifie que le connecteur ne doit pas être activé tant qu'une interface
publique stable ou une autorisation institutionnelle n'est pas disponible.

## Audit OpenDataMoroccanLaw du 2026-08-21

- Révision publiée : `7090abd00cf7e2a4ce7d5a9b1b5debb5bee3e7aa`.
- 29 000 lignes et 8 colonnes annoncées par l'API Hugging Face.
- Période annoncée : du 1997-07-22 au 2026-06-26.
- Aucun numéro de décision, numéro de dossier ou date manquant selon les statistiques publiées.
- Formation (`bench`) manquante sur 28 604 lignes ; chambre renseignée sur toutes les lignes.
- Longueur des textes annoncée : 410 à 124 181 caractères.
- L'échantillon inspecté contient encore des noms et des éléments familiaux ou médicaux : une
  anonymisation automatique suivie d'une revue humaine est requise avant diffusion publique.

Ces nombres proviennent de l'API du dataset et peuvent évoluer. La commande
`jurisprudence-extractor huggingface-audit` les recalcule sans télécharger tout le corpus.

## Politique PDF

La collecte suit la RFC 9309 : une réponse `4xx` sur `/robots.txt` signifie que les règles sont
indisponibles et permet l'accès, tandis qu'une erreur réseau ou `5xx` entraîne un refus complet.
Une règle `Disallow` applicable reste bloquante. Les codes de confirmation, CAPTCHA, comptes et
routes interdites ne sont jamais contournés.

## Vérification du 2026-08-21

- MarocDroit renvoie `robots.txt` en HTTP 200 ; `/search/`, les articles et `/attachment/` ne sont
  pas interdits par les règles publiées.
- Le site ne publie pas de sitemap XML fonctionnel : la découverte passe par sa recherche publique
  paginée, avec cinq expressions judiciaires bornées.
- Adala renvoie HTTP 404 pour `robots.txt`, ce qui est traité selon la RFC 9309, mais son entrée
  « jurisprudence » redirige vers Juriscassation et aucun corpus judiciaire distinct n'a été trouvé.
- Le crawl exhaustif des cinq recherches a parcouru toute la file et archivé huit ressources PDF
  uniques. Sept sont des décisions ou candidats judiciaires ; une pièce explicitement doctrinale a
  été repérée lors de l'audit final et reste à reclasser hors du corpus de décisions.
