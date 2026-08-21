# Pilote de 100 décisions — 2026-08-21

## Résultat mesuré

- Source : `OpenDataMoroccanLaw/morocco-cassation-court-decisions`.
- Décisions exportées : 100.
- Fichiers produits : 100 JSON bruts, 100 Markdown normalisés, 100 JSON de métadonnées et
  1 manifeste JSONL.
- Taille locale totale : 2,6 Mo.
- Décisions portant un signal automatique de revue : 10.

Le nombre de signaux ne constitue pas un taux d'anonymisation. Les règles automatiques ne
détectent pas exhaustivement les noms de personnes, notamment en arabe. Les 100 décisions
doivent donc rester privées jusqu'à validation humaine.

## Stockage

Le corpus local est ignoré par Git. Le pipeline GCS refuse tout bucket sans prévention de
l'accès public `enforced` et sans accès uniforme au niveau du bucket. Les objets sont créés
avec `if_generation_match=0`, ce qui interdit leur écrasement silencieux.

## Preuve Google Cloud

- Projet : `gti-secure-vault`.
- Bucket : `gs://gti-secure-vault-2026` (`EUROPE-WEST1`).
- Préfixe : `jurisprudence/pilots/2026-08-21/`.
- Prévention d'accès public : `enforced`.
- Accès uniforme au niveau du bucket : activé.
- Suppression douce : sept jours.
- Objets distants : 301.
- Volume distant annoncé : 1,88 MiB.
- SHA-256 local et distant du manifeste :
  `01b77f56492af91e53c4135e22adc21396ddaae1571c239fb1eb85a77b052b6e`.

Le pilote a été envoyé avec `gcloud storage` et une précondition de génération nulle afin de
refuser l'écrasement d'un objet existant. Les identifiants Application Default restent à
renouveler pour utiliser directement le client Python `google-cloud-storage`.
