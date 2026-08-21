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

## 2026-08-21 — Qualité, anonymisation et reprise incrémentale

- Ajout d'une anonymisation conservatrice des courriels, téléphones marocains et CIN
  explicitement libellées, avec recalcul de l'empreinte du texte transformé.
- Ajout d'un signal de revue humaine pour les décisions présentant des indices sensibles ;
  l'outil ne prétend pas détecter automatiquement tous les noms ou toutes les données privées.
- Ajout d'un audit JSON mesuré : volumes par source et type de contenu, champs manquants,
  empreintes de contenu répétées et décisions encore en attente d'anonymisation.
- Ajout d'un mode incrémental qui s'arrête au premier élément déjà stocké pour les sources
  explicitement ordonnées du plus récent au plus ancien.
- Ajout de tests unitaires couvrant l'anonymisation, l'audit et la détection préalable des
  décisions déjà stockées.

## 2026-08-21 — Audit et correction du dataset OpenDataMoroccanLaw

- Audit de l'API Hugging Face : 29 000 lignes, 8 colonnes et période 1997-07-22 à 2026-06-26.
- Correction du mapping selon le schéma réellement publié : `docket_number`, `decision_number`,
  `date`, `chamber`, `bench`, `text`, `has_preamble` et `source`.
- Correction de la provenance : le dataset est une republication secondaire sous CC-BY-4.0,
  avec conservation de l'origine déclarée mais sans URL individuelle par décision.
- Ajout d'une commande d'audit distant reproductible ne téléchargeant pas l'intégralité du corpus.
- Ajout de tests du mapping et du résumé statistique.

## 2026-08-21 — Pilote documentaire et stockage Google Cloud

- Ajout du pipeline `raw JSON` + `normalized Markdown` + `metadata JSON` et d'un manifeste JSONL.
- Ajout d'identifiants stables, empreintes SHA-256 et types MIME pour chaque objet.
- Ajout d'un stockage GCS optionnel avec checksum, création seule et refus des buckets qui
  n'imposent pas la prévention de l'accès public et l'accès uniforme au niveau du bucket.
- Pilote local mesuré : 100 décisions, 301 fichiers et 2,6 Mo.
- Dix décisions présentent les signaux sensibles actuellement détectés ; les 100 décisions
  restent soumises à revue humaine, car l'absence de signal n'établit pas l'absence de noms.
- Authentification `admin@lovemaroc.org` renouvelée par l'opérateur.
- Prévention d'accès public renforcée à `enforced` sur le bucket existant
  `gs://gti-secure-vault-2026` ; accès uniforme déjà actif et aucune liaison IAM publique constatée.
- Envoi réussi sous `jurisprudence/pilots/2026-08-21/` : 301 objets et 1,88 MiB annoncés.
- Intégrité vérifiée : le SHA-256 du manifeste local et distant est identique
  (`01b77f56492af91e53c4135e22adc21396ddaae1571c239fb1eb85a77b052b6e`).

## 2026-08-21 — Corpus OpenDataMoroccanLaw complet sur GCS

- L'API de prévisualisation Hugging Face a répondu `429` après 3 000 lignes ; abandon de cette
  voie pour la collecte complète afin de respecter la limitation de débit.
- Téléchargement du fichier JSONL publié (29 000 lignes) puis ajout d'un lecteur JSONL en flux.
- Export complet : 29 000 JSON bruts, 29 000 Markdown, 29 000 métadonnées et un manifeste ;
  volume local mesuré : 686 Mo.
- 3 663 décisions portent un signal automatique de revue prioritaire ; les 29 000 restent privées
  car ce signal n'est pas une preuve d'anonymisation exhaustive.
- Envoi sous le préfixe versionné correspondant à la révision Hugging Face `7090abd00c...`.
- Preuve distante : 29 000 JSON bruts, 29 000 Markdown, JSONL source complet, archive complète
  des 29 000 métadonnées et manifeste, pour 686,78 MiB annoncés par GCS.
- L'envoi individuel des métadonnées a été arrêté après 2 523 objets en raison d'une attente sous
  quota ; l'archive complète vérifiée garantit leur sauvegarde sans solliciter 29 000 écritures.
- SHA-256 distants vérifiés : manifeste `af0e08a...`, JSONL `3c0a2df...`, archive métadonnées
  `e4afbd3...`.

## 2026-08-21 — Collecte initiale des PDF judiciaires publics

- Mise en conformité du contrôle `robots.txt` avec la RFC 9309 : `4xx` autorise, erreur réseau ou
  `5xx` refuse, et toute règle `Disallow` applicable reste bloquante.
- Ajout d'un collecteur PDF limité par domaine, délai, signature `%PDF` et empreinte SHA-256.
- Cour constitutionnelle : deux recueils officiels récupérés, 1 264 pages et 9 398 350 octets.
- MarocDroit : quatre décisions secondaires récupérées, 23 pages et 1 792 362 octets.
- Validation `pdfinfo` : six PDF valides et non chiffrés ; contrôle visuel des couvertures des deux
  recueils institutionnels.
- Stockage GCS séparé sous `pdf/official/` et `pdf/secondary/`, avec précondition anti-écrasement.
- Intégrité des manifestes vérifiée local/distant : Cour constitutionnelle `ed60ef8...`,
  MarocDroit `33ffda4...`.
- Exclusion confirmée : les routes PDF de jurisprudence.ma sont interdites par `robots.txt` ;
  Juriscassation reste derrière un code de confirmation et n'est pas contourné.

## 2026-08-21 — Moteur de crawl hybride Scrapy / Playwright

- Ajout de Scrapy comme moteur principal avec `ROBOTSTXT_OBEY`, AutoThrottle, concurrence limitée
  par domaine, retries bornés et reprise persistante via `JOBDIR`.
- Ajout d'un pipeline PDF incrémental : validation `%PDF`, SHA-256, déduplication, métadonnées JSON
  et stockage local selon `raw/pdf/{statut}/{source}`.
- Ajout d'un stockage GCS générique immuable, réutilisé par les exports documentaires et PDF, avec
  checksum et précondition de création seule.
- Ajout optionnel de `scrapy-playwright` et Chromium pour les seules requêtes JavaScript qui seront
  explicitement marquées par un connecteur ; aucun navigateur n'est utilisé pour les PDF directs.
- Conservation des exclusions : aucune route interdite par `robots.txt`, aucun CAPTCHA et aucun code
  de confirmation ne sont contournés.
- Smoke tests réels avec la session `admin@lovemaroc.org` : deux PDF officiels (9 398 350 octets) et
  quatre PDF secondaires (1 792 362 octets), tous accompagnés de leur métadonnée JSON dans GCS.
- Authentification locale effectuée avec un jeton `gcloud` éphémère non écrit sur disque ; une
  identité de workload reste requise pour l'exécution longue durée dans Google Cloud.

## 2026-08-21 — Recherche MarocDroit et PDF vers Markdown

- Ajout d'un spider sur la recherche publique paginée de MarocDroit avec cinq expressions
  judiciaires, suivi limité aux articles et pièces jointes autorisés par `robots.txt`.
- Ajout d'une classification `decision` / `collection` ; les pièces purement doctrinales sont
  exclues du corpus judiciaire.
- Crawl exhaustif des cinq recherches : huit ressources PDF uniques, 66 pages et 5 001 959 octets
  archivés dans GCS ; sept décisions/candidats et un commentaire doctrinal détecté à reclasser.
- Ajout de l'extraction `pdftotext -layout`, avec repli `ocrmypdf` arabe, français et anglais lorsque
  le texte natif est insuffisant.
- Conversion de quatorze PDF : 1 353 pages physiques et 1 737 089 caractères non blancs ; deux scans
  ont utilisé l'OCR.
- Dérivés courants versionnés sous `derived/md/v2` et `derived/extraction/v2`; chaque OCR et chaque
  republication secondaire sont marqués `requires_human_review=true`. La `v1` reste immuable et les
  PDF sources restent inchangés.
