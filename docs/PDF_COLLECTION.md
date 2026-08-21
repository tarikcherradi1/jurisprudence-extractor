# Collecte des PDF judiciaires

## Résultat initial

| Source | Statut | PDF | Pages | Octets |
|---|---|---:|---:|---:|
| Cour constitutionnelle | officielle | 2 | 1 264 | 9 398 350 |
| MarocDroit | secondaire | 4 | 23 | 1 792 362 |

Les deux recueils officiels couvrent respectivement les décisions du Conseil constitutionnel de
2016 et du début de 2017, puis les décisions de la Cour constitutionnelle de 2019 à 2023.

## Google Cloud Storage

- Officiel : `gs://gti-secure-vault-2026/jurisprudence/pdf/official/cour-constitutionnelle/`.
- Secondaire : `gs://gti-secure-vault-2026/jurisprudence/pdf/secondary/marocdroit/`.
- SHA-256 du manifeste officiel :
  `ed60ef82fe0a65db48f2184359e229300012239401ea1a8a5b5c895c942e0e4d`.
- SHA-256 du manifeste secondaire :
  `33ffda45a6c867daa8e7e4453857a7a82c09ebba7817def29a7372463293cd8e`.

## Limites respectées

- `jurisprudence.ma` interdit explicitement les URL `?pdf=` dans `robots.txt` : aucune collecte.
- Juriscassation impose un code avant le texte intégral : aucune automatisation de ce contrôle.
- Les PDF de MarocDroit restent qualifiés de republications secondaires, même quand ils reproduisent
  une décision de la Cour de cassation.

L'inventaire doit maintenant être étendu aux sitemaps et pages publiques autorisées des autres
institutions et éditeurs, avec déduplication par SHA-256.
