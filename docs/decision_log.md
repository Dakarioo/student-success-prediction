# Registre des décisions méthodologiques

Ce registre permet de **justifier chaque choix** effectué pendant la SAÉ, à l'écrit comme à l'oral.
Une décision est ajoutée dès qu'elle est prise, relue par l'autre membre, puis passée au statut `Validée`.

**Statuts :** `À décider` · `Proposée` · `Validée` · `Remplacée par D-xxx` · `Abandonnée`

## Modèle de ligne

```markdown
| D-0XX | AAAA-MM-JJ | Mission N | Décision | Pourquoi | Autres options étudiées | Effet sur les données / résultats | Membre X | Membre Y | Proposée |
```

## Décisions

| ID | Date | Mission | Décision | Justification | Alternatives envisagées | Conséquences | Auteur | Relecteur | Statut |
|---|---|---|---|---|---|---|---|---|---|
| D-001 | 2026-11-26 | Initialisation | Structure du dépôt : `data/`, `notebooks/` (final + développement), `src/`, `tests/`, `docs/`, `reports/` | Séparer données, code réutilisable, expérimentations et livrables ; limiter les conflits Git | Un seul notebook sans modules | Les fonctions réutilisables vivent dans `src/` | Initialisation assistée | Membre 1 / Membre 2 | Proposée |
| D-002 | 2026-11-26 | Initialisation | Les données (CSV) et les PDF pédagogiques ne sont pas versionnés | Redistribution non autorisée à ce jour | Versionner le CSV dans un dépôt privé | Chaque membre place le CSV dans `data/raw/` localement | Initialisation assistée | Membre 1 / Membre 2 | Proposée |
| D-003 | 2026-11-26 | Initialisation | Ressources copiées depuis `sujet/` vers `data/raw/` et `docs/references/` ; `sujet/` conservé et ignoré par Git | Ne rien supprimer ni déplacer sans accord | Déplacer les fichiers | Deux copies locales identiques (empreintes SHA-256 vérifiées) | Initialisation assistée | Membre 1 / Membre 2 | Proposée |
| D-004 | 2026-11-26 | Initialisation | Dépendances bornées (`>=` version vérifiée, `<` prochaine version majeure), Python ≥ 3.11 | Compromis reproductibilité / compatibilité ; pandas 3 exige Python 3.11 | Versions figées exactes | Installer dans un `.venv` local ; figer les versions exactes avant la remise si nécessaire | Initialisation assistée | Membre 1 / Membre 2 | Proposée |
| D-012 | 2026-11-26 | Initialisation | Dépôt GitHub **public** dès sa création, partagé avec le binôme | Valoriser le projet auprès de recruteurs ; simplicité de collaboration | Dépôt privé jusqu'à la remise, puis passage en public | Données et PDF toujours exclus (`.gitignore`) ; contenu poussé immédiatement visible ; vérifier les règles de l'établissement | Membre 1 | Membre 2 | Proposée |
| D-013 | 2026-11-26 | Mission 1 | Audit automatisé dans le paquet `src/data_quality` (détecteurs indépendants, registre central des règles, configuration centralisée) ; `src/audit.py` devient une façade d'import | Réutilisable dans les notebooks et en terminal, reproductible, testable ; `src/audit.py` était réservé à cette mission | Fonctions dans un seul module `audit.py` ; code directement dans le notebook | Audit relançable sur les données nettoyées ; aucune donnée modifiée | Assistant (Claude) | Membre 1 / Membre 2 | Proposée |
| D-014 | 2026-11-26 | Mission 1 | Lecture du CSV en texte brut pour l'audit (`load_raw_text_data`) ; contrôles croisés et statistiques limités aux valeurs du domaine métier | Voir les valeurs exactement comme dans le fichier ; éviter les signalements en cascade d'une même valeur impossible | Lecture typée par pandas (masque « ND », virgules, espaces) | Chaque valeur impossible est signalée une seule fois | Assistant (Claude) | Membre 1 / Membre 2 | Proposée |
| D-015 | 2026-11-26 | Mission 1 | Hypothèses d'audit explicites : âge plausible [16 ; 70], validation d'une UE à 10/20, UE créditées comptées comme validées, seuils de `niveau_dossier` 120/140/160 inférés du fichier, identifiant `ET` + 6 chiffres | Le dictionnaire ne fixe pas ces limites ; elles ne produisent que des anomalies potentielles | Ne pas contrôler ces relations | Diagnostics « à vérifier », jamais « erreur confirmée » | Assistant (Claude) | Membre 1 / Membre 2 | Proposée |
| D-016 | 2026-11-26 | Mission 1 | Atypiques univariés : IQR + Z-score (si \|asymétrie\| ≤ 1) + Z-score modifié, échelle log1p si asymétrie > 1, consensus de 2 méthodes, zéros structurels exclus, queue haute seule pour les comptages | Une valeur rare n'est pas une erreur ; éviter de signaler les profils légitimes (étudiants plus âgés, abandons) | Une seule méthode ; seuils sur données brutes | 1 104 signalements univariés (INFO / MEDIUM) au lieu de ~3 200 | Assistant (Claude) | Membre 1 / Membre 2 | Proposée |
| D-017 | 2026-11-26 | Mission 1 | `pytest` et `ruff` installés dans un `.venv` local créé avec `--system-site-packages` (bibliothèques existantes réutilisées) | Exécuter les tests ; outils déjà déclarés dans `requirements.txt` | Installation globale | Aucune dépendance nouvelle ; `.venv` ignoré par Git | Assistant (Claude) | Membre 1 / Membre 2 | Proposée |
| D-005 | — | Mission 1 | Traitement des doublons et des `id_etudiant` répétés | — | Dédoublonnage ; découpage groupé stratifié | Détermine le protocole de séparation | — | — | À décider |
| D-006 | — | Mission 1 / 2 | Traitement des colonnes numériques lues comme texte | — | — | — | — | — | À décider |
| D-007 | — | Mission 2 | Traitement des variables redondantes (`note_admission_archive`, `age_inscription_mois`, `niveau_dossier`) | — | — | — | — | — | À décider |
| D-008 | — | Mission 2 | Conservation ou exclusion des métadonnées (`version_export`, `code_campagne`) | — | — | — | — | — | À décider |
| D-009 | — | Missions 4 / 5 | Métrique principale de sélection (à fixer **avant** l'optimisation) | — | F1 macro (candidate), F1 pondéré, Recall d'une classe | — | — | — | À décider |
| D-010 | — | Mission 4 | Grilles de valeurs des hyperparamètres obligatoires | — | — | — | — | — | À décider |
| D-011 | — | Mission 4 | Modèle final retenu | — | — | — | — | — | À décider |
