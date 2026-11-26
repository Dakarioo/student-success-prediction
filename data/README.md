# Données

## Origine

`parcours_etudiants.csv` est un export administratif et pédagogique **préparé pour l'exercice** de la
SAÉ 5.03 (certaines variables et métadonnées sont simulées). Il est fourni par l'établissement sur
**Moodle**, avec le dictionnaire des variables.

## Rôle

Jeu de données unique du projet : chaque ligne décrit un étudiant (informations à l'inscription,
contexte économique, résultats des semestres 1 et 2) et son statut académique à l'échéance normale
de la formation (`statut_academique`, variable cible).

Description des variables : [`docs/data_dictionary.md`](../docs/data_dictionary.md).

## Format

| Élément | Valeur |
|---|---|
| Format | CSV |
| Séparateur | Virgule (`,`) |
| Encodage | UTF-8 **avec BOM** — lire avec `encoding="utf-8-sig"` (fait par `src/data_loader.py`) |
| Décimales | Point, selon le dictionnaire (à vérifier pendant l'audit) |
| Fins de ligne | LF |
| Dimensions | 4 504 lignes × 33 colonnes |
| Empreinte SHA-256 du fichier reçu | `707360BCC39CE4F85FD36CC4516B8601B3322E3CCAB62D0E690F3FBC5F0DDFC2` |

L'empreinte permet de vérifier que chaque membre travaille sur le même fichier, et qu'il n'a pas été modifié :

```powershell
Get-FileHash data\raw\parcours_etudiants.csv -Algorithm SHA256
```

## Structure

| Dossier | Contenu | Versionné |
|---|---|---|
| `raw/` | Données originales, **strictement immuables** | Non (seul `.gitkeep`) |
| `interim/` | Données intermédiaires issues d'étapes de préparation | Non (seul `.gitkeep`) |
| `processed/` | Données préparées, résultats de transformations | Non (seul `.gitkeep`) |

## Règles de manipulation

1. **Aucune opération n'écrase un fichier de `raw/`.** Le chargement se fait en lecture seule via
   `src.data_loader.load_raw_data()`, puis on travaille sur une copie (`df = df_raw.copy()`).
2. Les sorties intermédiaires sont écrites dans `interim/` ou `processed/`, jamais dans `raw/`.
3. Les transformations qui **apprennent des paramètres** (imputation, mise à l'échelle, encodage…) ne
   sont **jamais** ajustées sur l'ensemble des données avant la séparation apprentissage / test.
   Elles vivent dans des pipelines ajustés sur les données d'apprentissage appropriées.
4. Un fichier de `processed/` issu d'un traitement appris ne doit pas contenir le jeu de test transformé
   avec des paramètres estimés sur ce même test.
5. Aucune donnée synthétique ne remplace des données absentes.

## Récupération du jeu de données

1. Télécharger `parcours_etudiants.csv` depuis l'espace Moodle de la SAÉ 5.03.
2. Le placer dans `data/raw/` **sans le renommer ni l'ouvrir dans un tableur** (un enregistrement par
   Excel peut modifier l'encodage, le séparateur ou les décimales).
3. Vérifier son empreinte SHA-256 (voir ci-dessus).
4. Si le fichier est absent, `load_raw_data()` lève une erreur explicite indiquant cette procédure.

## Restrictions de publication

- Les données **ne sont pas versionnées** (`.gitignore`) et ne doivent pas être publiées sans
  autorisation explicite de l'établissement.
- Aucune ligne individuelle ne doit apparaître dans les sorties de notebooks, figures ou tableaux publiés.
- Voir [`docs/publication_checklist.md`](../docs/publication_checklist.md).
