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

L'envoi n'a pas été exécuté : la session Google Cloud configurée demande le mot de passe du
compte `admin@lovemaroc.org`. Une fois la session renouvelée, il faudra identifier le bucket
privé existant avant de relancer la commande avec `--bucket`.
