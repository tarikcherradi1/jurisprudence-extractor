# Registre des sources

| Source | Statut | Mode | Limite connue |
|---|---|---|---|
| Cour constitutionnelle | active | HTML public, texte intégral | pagination à surveiller |
| OpenDataMoroccanLaw | active | dataset public en streaming, CC-BY-4.0 | republication secondaire, pas d'URL par décision |
| Juriscassation | expérimentale | parseur métadonnées/extraits | TLS non validé hors navigateur, texte derrière code |
| Adala | catalogue | renvoi vers Juriscassation | pas de corpus distinct identifié |
| Portail des jugements | suspendue | ancien endpoint JSON | protection TSPD et filtres incohérents |

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
