# Corpus OpenDataMoroccanLaw complet sur Google Cloud

## Emplacement

- Bucket : `gs://gti-secure-vault-2026`.
- Préfixe :
  `jurisprudence/corpus/opendatamoroccanlaw/7090abd00cf7e2a4ce7d5a9b1b5debb5bee3e7aa/`.
- Région : `EUROPE-WEST1`.
- Prévention d'accès public : `enforced`.
- Accès uniforme : activé.

## Inventaire vérifié

- `raw/` : 29 000 JSON individuels.
- `normalized/` : 29 000 Markdown individuels.
- `metadata/` : 2 523 JSON individuels avant mise en attente du client sous quota.
- `bundles/train.jsonl` : source complète de 29 000 lignes.
- `bundles/metadata.tar.gz` : archive complète des 29 000 métadonnées.
- `manifests/opendatamoroccanlaw.jsonl` : manifeste complet de 29 000 décisions.
- Volume distant total annoncé : 686,78 MiB.

L'archive des métadonnées évite 29 000 écritures de petits objets et constitue la copie complète
de référence. Les métadonnées individuelles pourront être matérialisées plus tard par lots si un
consommateur l'exige.

## Empreintes SHA-256 vérifiées local/distant

- Manifeste : `af0e08a25d1259a0d83462adbad91c1585b455296fbb8023641ab14eee05913a`.
- JSONL source : `3c0a2dfdecd85d15ba52a579a9989a62b93730534ea3e5b7a9f815c3cb277cd1`.
- Archive métadonnées : `e4afbd3fd050d3494856aa6c6cb5c732ba299084d7e82481c9fe0e20cfd6636b`.

## Confidentialité

Les données brutes et les Markdown peuvent contenir des noms, des informations familiales et
des données médicales. Les 3 663 signaux automatiques servent uniquement à prioriser la revue ;
aucune décision ne doit être rendue publique avant une anonymisation nominative validée.
