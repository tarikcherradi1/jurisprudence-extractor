# Journal

## 2026-08-21 — Socle d’ingestion de jurisprudence marocaine

- Ajout d’un schéma Pydantic strict et traçable pour les décisions.
- Ajout d’un connecteur public pour la Cour constitutionnelle.
- Ajout d’un import en streaming du dataset public OpenDataMoroccanLaw.
- Ajout du stockage SQLite avec déduplication SHA-256.
- Ajout de garde-fous robots.txt, débit, erreurs 401/403/429 et absence de contournement.
- Ajout de tests unitaires du parseur et de la déduplication.
- Preuve attendue en CI/local : `python -m pytest`.

## 2026-08-21 — Connecteur de métadonnées Juriscassation

- Inspection de l'interface publique et de son formulaire POST anti-CSRF.
- Ajout d'un connecteur paginé pour les métadonnées et extraits de recherche.
- Ajout du type de contenu `full_text`, `excerpt` ou `metadata`.
- Exclusion explicite du texte intégral protégé par un code de confirmation.
- Constat : Adala renvoie désormais la jurisprudence vers Juriscassation.
- Constat : l'ancien Portail des jugements est protégé par TSPD et ses filtres 2019/2018
  exposent une valeur 2017 incohérente ; aucun connecteur automatisé n'est activé.
- Preuve locale : 3 tests réussis et Ruff vert.
- Smoke test Juriscassation : arrêt sécurisé avant collecte, car la chaîne TLS du serveur
  n'est pas validée par le client Python. La vérification TLS n'est pas désactivée.
