# jurisprudence-extractor

Pipeline traçable de collecte de jurisprudence marocaine rendue publiquement accessible.

## Sources livrées

- **Cour constitutionnelle du Maroc** : collecte des pages publiques, sans contournement.
- **OpenDataMoroccanLaw** : import en streaming du dataset public de décisions de la Cour de cassation.

Les portails Juriscassation, Adala et Portail des jugements seront ajoutés seulement après
validation de leurs conditions d'utilisation et de leurs interfaces publiques.

## Garanties

- provenance et URL d'origine obligatoires ;
- empreinte SHA-256 du texte ;
- déduplication persistante dans SQLite ;
- arrêt sur `401`, `403`, `429` ou interdiction `robots.txt` ;
- aucun CAPTCHA, compte ou contrôle d'accès contourné ;
- statuts `official`, `secondary` et `unverified` ;
- schéma strict Pydantic v2.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,huggingface]'
```

## Utilisation

Importer un petit échantillon du dataset public :

```bash
jurisprudence-extractor huggingface-cassation --limit 20
```

Collecter des décisions constitutionnelles publiques :

```bash
jurisprudence-extractor constitutional-court --limit 20
```

Par défaut, les décisions sont stockées dans `jurisprudence.sqlite3`.

## Tests

```bash
pytest
ruff check .
```

## Avertissement

La publication en ligne d'une décision ne dispense pas de respecter la loi marocaine n° 09-08,
les droits des personnes, les conditions d'utilisation des sources et les règles applicables
à la réutilisation des bases. Les données sensibles doivent être anonymisées avant toute
diffusion ou indexation publique.
