# jurisprudence-extractor

Pipeline traçable de collecte de jurisprudence marocaine rendue publiquement accessible.

## Sources livrées

- **Cour constitutionnelle du Maroc** : collecte des pages publiques, sans contournement.
- **OpenDataMoroccanLaw** : import en streaming du dataset public de décisions de la Cour de cassation.
- **Juriscassation** : collecte des métadonnées et extraits de recherche officiellement exposés.

Les portails Juriscassation, Adala et Portail des jugements seront ajoutés seulement après
validation de leurs conditions d'utilisation et de leurs interfaces publiques.
Le texte intégral de Juriscassation reste volontairement exclu : le site impose un code de
confirmation avant consultation et le projet ne l'automatise pas.

## Garanties

- provenance et URL d'origine obligatoires ;
- empreinte SHA-256 du texte ;
- déduplication persistante dans SQLite ;
- arrêt sur `401`, `403`, `429` ou interdiction `robots.txt` ;
- aucun CAPTCHA, compte ou contrôle d'accès contourné ;
- statuts `official`, `secondary` et `unverified` ;
- schéma strict Pydantic v2.
- anonymisation conservatrice des identifiants à forte confiance (courriel, téléphone, CIN
  explicitement libellée), avec signalement des décisions qui exigent une revue humaine ;
- audit mesuré du corpus et collecte incrémentale pour les sources ordonnées du plus récent
  au plus ancien.

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

Auditer à distance la taille et le schéma actuellement publiés, sans télécharger le corpus :

```bash
jurisprudence-extractor huggingface-audit
```

Collecter des décisions constitutionnelles publiques :

```bash
jurisprudence-extractor constitutional-court --limit 20
```

Collecter des métadonnées Juriscassation par sujet et chambre :

```bash
jurisprudence-extractor juriscassation-metadata \
  --subject "المسؤولية" --chamber 1 --limit 20
```

Par défaut, les décisions sont stockées dans `jurisprudence.sqlite3`.

Anonymiser les identifiants à forte confiance avant stockage :

```bash
jurisprudence-extractor constitutional-court --anonymize --limit 20
```

Reprendre une source ordonnée du plus récent au plus ancien jusqu'au premier élément déjà
stocké, puis auditer la base :

```bash
jurisprudence-extractor constitutional-court --incremental
jurisprudence-extractor audit
```

Le mode automatique ne détecte volontairement pas tous les noms de personnes. Le compteur
`requires_review` signale les textes sensibles à soumettre à une revue humaine avant diffusion.

Le corpus Hugging Face est traité comme une republication `secondary` sous licence CC-BY-4.0.
Son champ `source` conserve l'origine déclarée `juriscassation.cspj.ma`, mais il ne fournit pas
d'URL individuelle permettant de vérifier chaque décision sur le portail institutionnel.

## Export documentaire et Google Cloud Storage

Créer un pilote local de 100 décisions :

```bash
jurisprudence-extractor huggingface-export --limit 100 --output-dir corpus-pilot
```

Pour le corpus complet, télécharger une seule fois le JSONL publié puis l'exporter en flux local
évite les limites de débit de l'API de prévisualisation :

```bash
jurisprudence-extractor huggingface-export --limit 29000 \
  --input-jsonl /chemin/vers/train.jsonl \
  --output-dir /chemin/vers/corpus
```

Après authentification Google Cloud, envoyer le même pilote vers un bucket privé existant :

```bash
pip install -e '.[gcs]'
jurisprudence-extractor huggingface-export --limit 100 \
  --output-dir corpus-pilot \
  --bucket NOM_DU_BUCKET \
  --prefix jurisprudence/pilots/2026-08-21
```

L'envoi refuse les buckets qui n'imposent pas la prévention de l'accès public et l'accès
uniforme au niveau du bucket. Chaque objet est créé avec une précondition anti-écrasement et
un checksum. Les JSON bruts peuvent contenir des données personnelles et doivent rester privés.

## Collecte des PDF publics

```bash
jurisprudence-extractor constitutional-pdfs --output-dir pdf-corpus
jurisprudence-extractor marocdroit-pdfs --output-dir pdf-corpus
```

Le collecteur applique la RFC 9309, met en cache chaque `robots.txt`, respecte un délai entre les
requêtes, refuse les erreurs serveur et les routes interdites, limite les hôtes et vérifie la
signature `%PDF` avant stockage. Les recueils institutionnels et les republications privées sont
rangés séparément.

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
