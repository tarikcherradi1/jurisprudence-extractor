# Journal

## 2026-08-21 — Socle d’ingestion de jurisprudence marocaine

- Ajout d’un schéma Pydantic strict et traçable pour les décisions.
- Ajout d’un connecteur public pour la Cour constitutionnelle.
- Ajout d’un import en streaming du dataset public OpenDataMoroccanLaw.
- Ajout du stockage SQLite avec déduplication SHA-256.
- Ajout de garde-fous robots.txt, débit, erreurs 401/403/429 et absence de contournement.
- Ajout de tests unitaires du parseur et de la déduplication.
- Preuve attendue en CI/local : `python -m pytest`.
