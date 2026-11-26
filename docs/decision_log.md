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
| D-005 | — | Mission 1 | Traitement des doublons et des `id_etudiant` répétés | — | Dédoublonnage ; découpage groupé stratifié | Détermine le protocole de séparation | — | — | À décider |
| D-006 | — | Mission 1 / 2 | Traitement des colonnes numériques lues comme texte | — | — | — | — | — | À décider |
| D-007 | — | Mission 2 | Traitement des variables redondantes (`note_admission_archive`, `age_inscription_mois`, `niveau_dossier`) | — | — | — | — | — | À décider |
| D-008 | — | Mission 2 | Conservation ou exclusion des métadonnées (`version_export`, `code_campagne`) | — | — | — | — | — | À décider |
| D-009 | — | Missions 4 / 5 | Métrique principale de sélection (à fixer **avant** l'optimisation) | — | F1 macro (candidate), F1 pondéré, Recall d'une classe | — | — | — | À décider |
| D-010 | — | Mission 4 | Grilles de valeurs des hyperparamètres obligatoires | — | — | — | — | — | À décider |
| D-011 | — | Mission 4 | Modèle final retenu | — | — | — | — | — | À décider |
