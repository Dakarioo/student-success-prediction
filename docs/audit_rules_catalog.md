# Catalogue des règles d'audit

> Généré automatiquement depuis `src/data_quality/rules.py` (`python -m src.data_quality --catalog`). Ne pas modifier à la main : modifier le registre puis régénérer.

Gravité : CRITICAL > HIGH > MEDIUM > LOW > INFO. Diagnostic : `erreur_confirmee` (Erreur confirmée), `anomalie_potentielle` (Anomalie potentielle), `valeur_atypique` (Valeur statistiquement atypique), `risque_methodologique` (Risque méthodologique), `information_descriptive` (Information descriptive). La gravité de certaines règles peut être ajustée au cas par cas (ex. `STR_TYPE_MISMATCH`, `LEA_TECHNICAL_METADATA`, `IMB_CLASS_IMBALANCE`).

## Détecteur `structure`

### `STR_EMPTY_DATASET` — Jeu de données sans observation

- **Gravité** : CRITICAL · **Diagnostic** : erreur_confirmee · **Catégorie** : structure
- **Variables** : toutes
- **Justification** : Un fichier sans ligne ne permet aucune analyse.
- **Méthode** : Comptage des lignes
- **Impact ML** : Aucun apprentissage possible.
- **Action envisagée** : Vérifier l'export source et la procédure de récupération du fichier.

### `STR_SHAPE` — Dimensions du jeu de données

- **Gravité** : INFO · **Diagnostic** : information_descriptive · **Catégorie** : structure
- **Variables** : toutes
- **Justification** : Le dictionnaire décrit 33 colonnes ; les dimensions servent de référence aux comparaisons.
- **Méthode** : Comptage
- **Impact ML** : Aucun en soi.
- **Action envisagée** : Consigner les dimensions avant et après nettoyage.

### `STR_MISSING_COLUMN` — Colonne du dictionnaire absente du fichier

- **Gravité** : CRITICAL · **Diagnostic** : erreur_confirmee · **Catégorie** : structure
- **Variables** : colonnes du dictionnaire
- **Justification** : Toute variable documentée doit figurer dans l'export.
- **Méthode** : Comparaison avec le dictionnaire
- **Impact ML** : Variables explicatives ou cible indisponibles ; code de prétraitement en échec.
- **Action envisagée** : Récupérer un export complet ; ne pas reconstruire la colonne artificiellement.

### `STR_UNEXPECTED_COLUMN` — Colonne absente du dictionnaire

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : structure
- **Variables** : colonnes hors dictionnaire
- **Justification** : Une colonne non documentée n'a pas de sens métier établi.
- **Méthode** : Comparaison avec le dictionnaire
- **Impact ML** : Risque d'utiliser une information non maîtrisée (fuite, artefact technique).
- **Action envisagée** : Documenter l'origine de la colonne avant toute utilisation.

### `STR_DUPLICATE_COLUMN_NAME` — Nom de colonne dupliqué dans l'en-tête

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : structure
- **Variables** : en-tête
- **Justification** : Deux colonnes de même nom sont ambiguës ; pandas les renomme silencieusement.
- **Méthode** : Lecture brute de l'en-tête
- **Impact ML** : Sélection de la mauvaise colonne, résultats non reproductibles.
- **Action envisagée** : Identifier la colonne correcte avec le producteur de l'export.

### `STR_TYPE_MISMATCH` — Type lu différent du type attendu

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : structure
- **Variables** : variables numériques et codes
- **Justification** : Le dictionnaire définit des notes, âges et comptages numériques ; un type texte révèle des valeurs non numériques.
- **Méthode** : Inférence de type pandas sur le texte brut
- **Impact ML** : Calculs impossibles ou faux, encodage catégoriel accidentel de variables numériques.
- **Action envisagée** : Identifier les valeurs responsables (voir FMT_* et MIS_*), puis convertir explicitement lors du nettoyage déterministe.

### `STR_EMPTY_COLUMN` — Colonne entièrement vide

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : structure
- **Variables** : toutes
- **Justification** : Une colonne sans aucune valeur n'apporte aucune information.
- **Méthode** : Comptage des valeurs manquantes
- **Impact ML** : Variable inutilisable ; imputation impossible.
- **Action envisagée** : Vérifier l'export ; exclure la variable si l'absence est confirmée.

### `STR_CONSTANT_COLUMN` — Colonne constante

- **Gravité** : MEDIUM · **Diagnostic** : risque_methodologique · **Catégorie** : structure
- **Variables** : toutes
- **Justification** : Une variable à une seule modalité ne peut pas discriminer les classes.
- **Méthode** : Nombre de modalités distinctes
- **Impact ML** : Aucun pouvoir prédictif ; bruit inutile pour KNN ; risque si la constante change à l'avenir (dérive).
- **Action envisagée** : Exclure des variables explicatives (décision à consigner dans le registre).

### `STR_QUASI_CONSTANT_COLUMN` — Colonne quasi constante

- **Gravité** : INFO · **Diagnostic** : information_descriptive · **Catégorie** : structure
- **Variables** : toutes
- **Justification** : Une modalité dominante (≥ seuil) laisse peu de variabilité exploitable.
- **Méthode** : Part de la modalité dominante
- **Impact ML** : Faible pouvoir prédictif ; plis de validation pouvant ne contenir qu'une modalité.
- **Action envisagée** : Examiner l'intérêt métier ; envisager un regroupement ou une exclusion argumentée.

## Détecteur `missing_values`

### `MIS_NATIVE` — Valeur manquante native (champ vide)

- **Gravité** : MEDIUM · **Diagnostic** : erreur_confirmee · **Catégorie** : valeurs_manquantes
- **Variables** : toutes
- **Justification** : Un champ vide est lu comme NaN par pandas : l'information est absente.
- **Méthode** : Champ vide dans le CSV
- **Impact ML** : Modèles scikit-learn en échec sans imputation ; biais si le manque est informatif.
- **Action envisagée** : Imputer dans un pipeline ajusté sur l'apprentissage, ou exclure après analyse.

### `MIS_WHITESPACE_ONLY` — Valeur composée uniquement d'espaces

- **Gravité** : MEDIUM · **Diagnostic** : erreur_confirmee · **Catégorie** : valeurs_manquantes
- **Variables** : toutes
- **Justification** : Une chaîne d'espaces n'est pas reconnue comme manquante par pandas.
- **Méthode** : Expression régulière ^\s+$
- **Impact ML** : Fausse modalité catégorielle ; colonne numérique lue comme texte.
- **Action envisagée** : Convertir en valeur manquante lors du nettoyage déterministe.

### `MIS_NULL_TOKEN` — Mot-clé NULL textuel (NA, NULL, N/A…)

- **Gravité** : MEDIUM · **Diagnostic** : erreur_confirmee · **Catégorie** : valeurs_manquantes
- **Variables** : toutes
- **Justification** : Ces mots-clés sont interprétés comme NaN par pandas par défaut mais restent du texte dans d'autres outils.
- **Méthode** : Liste des marqueurs NaN de pandas
- **Impact ML** : Comportement dépendant de l'outil de lecture.
- **Action envisagée** : Déclarer explicitement les marqueurs de manque à la lecture.

### `MIS_DISGUISED` — Valeur manquante déguisée (ND, ?, Non renseigné…)

- **Gravité** : MEDIUM · **Diagnostic** : erreur_confirmee · **Catégorie** : valeurs_manquantes
- **Variables** : toutes
- **Justification** : Ces chaînes, observées dans le fichier, expriment une absence d'information sans être reconnues comme telles.
- **Méthode** : Liste de marqueurs déguisés (insensible à la casse et aux espaces)
- **Impact ML** : Modalité artificielle « ND » apprise par le modèle ; colonne numérique lue comme texte ; sous-estimation du taux de valeurs manquantes.
- **Action envisagée** : Recoder en valeur manquante (nettoyage déterministe), puis traiter avec les autres manques.

### `MIS_KEY_FIELD` — Identifiant ou cible manquant

- **Gravité** : CRITICAL · **Diagnostic** : erreur_confirmee · **Catégorie** : valeurs_manquantes
- **Variables** : id_etudiant, statut_academique
- **Justification** : Sans cible, l'observation est inutilisable en apprentissage supervisé ; sans identifiant, le contrôle de non-chevauchement est impossible.
- **Méthode** : Valeur manquante sur une variable clé
- **Impact ML** : Observation inexploitable ou contrôle de fuite impossible.
- **Action envisagée** : Exclure l'observation de l'apprentissage supervisé (décision à consigner).

### `MIS_ROW_CONCENTRATION` — Observation concentrant plusieurs valeurs manquantes

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : valeurs_manquantes
- **Variables** : toutes
- **Justification** : Une observation très incomplète peut refléter un export défaillant.
- **Méthode** : Nombre de valeurs manquantes (natives et déguisées) par ligne
- **Impact ML** : Imputations multiples sur une même ligne : information largement artificielle.
- **Action envisagée** : Examiner ces observations ; envisager leur exclusion si l'information restante est faible.

### `MIS_ASSOCIATION` — Valeurs manquantes associées entre deux variables

- **Gravité** : INFO · **Diagnostic** : information_descriptive · **Catégorie** : valeurs_manquantes
- **Variables** : paires de variables
- **Justification** : Des manques simultanés suggèrent un mécanisme commun (non aléatoire).
- **Méthode** : Coefficient phi entre indicateurs de manque
- **Impact ML** : Hypothèse MCAR fragile ; imputation indépendante variable par variable discutable.
- **Action envisagée** : Analyser le mécanisme ; envisager des indicateurs de manque.

## Détecteur `duplicates`

### `DUP_EXACT_ROW` — Doublon exact d'une observation

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : doublons
- **Variables** : toutes
- **Justification** : Deux lignes strictement identiques (identifiant compris) décrivent le même étudiant.
- **Méthode** : pandas.DataFrame.duplicated sur le texte brut
- **Impact ML** : Surpondération ; même étudiant possible en apprentissage ET en test (fuite, score optimiste).
- **Action envisagée** : Conserver une seule occurrence avant la séparation apprentissage/test (décision D-005).

### `DUP_ID_CONFLICT` — Identifiant partagé par des observations divergentes

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : doublons
- **Variables** : id_etudiant
- **Justification** : Un identifiant désigne un étudiant unique ; des informations différentes sont en conflit.
- **Méthode** : Groupes d'id_etudiant de taille > 1, contenus différents
- **Impact ML** : Impossible de savoir quelle version est correcte ; fuite si les lignes sont séparées.
- **Action envisagée** : Arbitrer avec la source ; à défaut, regrouper par identifiant lors du découpage.

### `DUP_CONTENT_DIFFERENT_ID` — Contenu identique sous des identifiants différents

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : doublons
- **Variables** : toutes sauf id_etudiant
- **Justification** : Deux étudiants distincts peuvent coïncider, mais la probabilité est faible avec 30+ variables dont des notes décimales.
- **Méthode** : duplicated sur toutes les colonnes sauf l'identifiant
- **Impact ML** : Possible double saisie, donc surpondération et fuite.
- **Action envisagée** : Vérifier avec la source avant toute suppression.

### `DUP_NORMALIZED` — Doublon révélé après normalisation du texte

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : doublons
- **Variables** : toutes
- **Justification** : Des lignes ne différant que par la casse, les accents ou les espaces sont probablement identiques.
- **Méthode** : duplicated après strip/minuscules/suppression des accents
- **Impact ML** : Doublons non détectés par une comparaison stricte.
- **Action envisagée** : Traiter avec les doublons exacts après harmonisation des modalités.

## Détecteur `formats`

### `FMT_CATEGORY_VARIANT` — Variante de saisie d'une modalité (espaces, casse, accents)

- **Gravité** : LOW · **Diagnostic** : erreur_confirmee · **Catégorie** : format_saisie
- **Variables** : variables qualitatives
- **Justification** : Ces variantes désignent la même catégorie que la forme de référence.
- **Méthode** : Comparaison avec une clé normalisée
- **Impact ML** : Modalités artificiellement multipliées : encodage one-hot gonflé, effectifs dispersés.
- **Action envisagée** : Harmoniser vers la forme de référence (nettoyage déterministe, sans paramètre appris).

### `FMT_FOREIGN_SYNONYM` — Synonyme dans une autre langue (YES / NO)

- **Gravité** : LOW · **Diagnostic** : erreur_confirmee · **Catégorie** : format_saisie
- **Variables** : variables binaires
- **Justification** : Le dictionnaire définit Oui / Non ; YES / NO en sont la traduction.
- **Méthode** : Table de synonymes
- **Impact ML** : Modalités supplémentaires dans une variable binaire.
- **Action envisagée** : Recoder vers Oui / Non (table de correspondance documentée).

### `FMT_NUMERIC_REPRESENTATION` — Représentation numérique non standard (virgule décimale, espaces)

- **Gravité** : LOW · **Diagnostic** : erreur_confirmee · **Catégorie** : format_saisie
- **Variables** : variables numériques
- **Justification** : Le dictionnaire indique un point décimal ; une virgule empêche la lecture numérique.
- **Méthode** : Expression régulière
- **Impact ML** : Colonne entière lue comme texte.
- **Action envisagée** : Remplacer la virgule par un point avant conversion.

### `FMT_TEXT_IN_NUMERIC` — Texte non numérique dans une variable numérique

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : format_saisie
- **Variables** : variables numériques
- **Justification** : Valeur ni numérique ni marqueur de manque connu.
- **Méthode** : Échec de conversion numérique
- **Impact ML** : Conversion numérique impossible.
- **Action envisagée** : Identifier la signification avec la source ; à défaut, traiter comme manquante.

### `FMT_PARASITE_CHARACTERS` — Caractères parasites (contrôle, tabulation, espace insécable…)

- **Gravité** : LOW · **Diagnostic** : erreur_confirmee · **Catégorie** : format_saisie
- **Variables** : toutes
- **Justification** : Caractères invisibles ou non imprimables sans signification métier.
- **Méthode** : Expression régulière sur caractères non imprimables
- **Impact ML** : Modalités faussement distinctes, conversions échouées.
- **Action envisagée** : Supprimer ces caractères lors du nettoyage.

### `FMT_SIMILAR_CATEGORIES` — Modalités orthographiquement proches

- **Gravité** : INFO · **Diagnostic** : anomalie_potentielle · **Catégorie** : format_saisie
- **Variables** : variables qualitatives
- **Justification** : Des chaînes très proches peuvent être des variantes orthographiques… ou des catégories réellement distinctes (ex. b2 / b3).
- **Méthode** : Similarité difflib entre clés normalisées
- **Impact ML** : Fragmentation possible d'une même catégorie.
- **Action envisagée** : Vérifier manuellement ; ne regrouper qu'avec une justification métier.

## Détecteur `business_rules`

### `DOM_OUT_OF_RANGE` — Valeur hors des bornes du dictionnaire

- **Gravité** : CRITICAL · **Diagnostic** : erreur_confirmee · **Catégorie** : domaine_metier
- **Variables** : notes /200, notes /20, taux de chômage
- **Justification** : Le dictionnaire fixe les échelles : notes d'admission et antérieures sur 200, notes semestrielles sur 20.
- **Méthode** : Comparaison aux bornes
- **Impact ML** : Valeurs impossibles qui faussent moyennes, échelles (KNN) et seuils des arbres.
- **Action envisagée** : Considérer comme manquante (recodage déterministe), puis imputer dans le pipeline ; ne jamais « corriger » par une valeur supposée.

### `DOM_NEGATIVE_COUNT` — Nombre d'UE ou d'évaluations négatif

- **Gravité** : CRITICAL · **Diagnostic** : erreur_confirmee · **Catégorie** : domaine_metier
- **Variables** : ue_*, nb_evaluations_*
- **Justification** : Le dictionnaire impose des entiers non négatifs.
- **Méthode** : Comparaison à 0
- **Impact ML** : Valeurs impossibles, contrôles croisés faussés.
- **Action envisagée** : Recoder en manquante lors du nettoyage.

### `DOM_NON_INTEGER` — Nombre non entier dans une variable de comptage

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : domaine_metier
- **Variables** : ue_*, nb_evaluations_*, âges
- **Justification** : Le dictionnaire impose des entiers (comptages) ; l'âge est en années révolues.
- **Méthode** : Partie fractionnaire non nulle
- **Impact ML** : Valeur impossible.
- **Action envisagée** : Vérifier la source ; recoder en manquante si non justifiable.

### `DOM_SENTINEL_VALUE` — Code sentinelle probable (999)

- **Gravité** : HIGH · **Diagnostic** : anomalie_potentielle · **Catégorie** : domaine_metier
- **Variables** : variables numériques sans borne haute
- **Justification** : 999 est un code conventionnel de valeur inconnue ; aucune borne haute n'est fixée par le dictionnaire, d'où un diagnostic potentiel.
- **Méthode** : Égalité avec les codes sentinelles configurés
- **Impact ML** : Valeur extrême artificielle (moyennes, écarts-types et distances écrasés).
- **Action envisagée** : Traiter comme valeur manquante déguisée après confirmation.

### `DOM_CATEGORY_OUT_OF_DOMAIN` — Modalité hors du domaine du dictionnaire

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : domaine_metier
- **Variables** : rang_voeu, regime_cours, binaires, niveau_dossier
- **Justification** : Le dictionnaire liste les modalités admises.
- **Méthode** : Comparaison au domaine après normalisation
- **Impact ML** : Catégorie inconnue, non interprétable.
- **Action envisagée** : Identifier la modalité correspondante avec la source ; sinon, manquante.

### `DOM_TARGET_INVALID` — Classe cible hors des trois classes attendues

- **Gravité** : CRITICAL · **Diagnostic** : erreur_confirmee · **Catégorie** : domaine_metier
- **Variables** : statut_academique
- **Justification** : La cible ne peut prendre que Abandon, En cours ou Diplômé.
- **Méthode** : Comparaison au domaine après normalisation
- **Impact ML** : Classe parasite apprise par le modèle ; métriques faussées.
- **Action envisagée** : Exclure ou recoder après vérification (jamais d'imputation de la cible).

### `DOM_ID_FORMAT` — Identifiant au format inhabituel

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : domaine_metier
- **Variables** : id_etudiant
- **Justification** : Le format ET + 6 chiffres est une convention OBSERVÉE, non décrite au dictionnaire.
- **Méthode** : Expression régulière
- **Impact ML** : Rapprochements entre fichiers et contrôle de chevauchement fragilisés.
- **Action envisagée** : Vérifier l'identifiant auprès de la source.

### `DOM_AGE_IMPOSSIBLE` — Âge impossible (≤ 0 ou > 120 ans)

- **Gravité** : CRITICAL · **Diagnostic** : erreur_confirmee · **Catégorie** : domaine_metier
- **Variables** : age_inscription, age_inscription_mois
- **Justification** : Un âge nul, négatif ou supérieur à 120 ans est biologiquement impossible.
- **Méthode** : Comparaison aux bornes d'impossibilité
- **Impact ML** : Valeur aberrante qui fausse les échelles et les distances.
- **Action envisagée** : Recoder en manquante ; age_inscription_mois peut aider à vérifier (sans arbitrage automatique).

### `DOM_AGE_IMPLAUSIBLE` — Âge peu plausible pour une inscription (hors [16 ; 70])

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : domaine_metier
- **Variables** : age_inscription
- **Justification** : HYPOTHÈSE d'audit : le dictionnaire ne fixe pas de plage d'âge.
- **Méthode** : Comparaison à une plage configurable
- **Impact ML** : Possible erreur de saisie, ou profil réel rare.
- **Action envisagée** : Vérifier ; conserver si plausible.

## Détecteur `consistency`

### `CON_VALIDATED_GT_ENROLLED` — UE validées supérieures aux UE inscrites

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : coherence_variables
- **Variables** : ue_validees_s*, ue_inscrites_s*
- **Justification** : Une UE validée est une UE suivie. Les UE créditées ne dépassent jamais les UE inscrites dans le fichier, ce qui indique qu'elles y sont comptées.
- **Méthode** : Comparaison ligne à ligne (valeurs du domaine uniquement)
- **Impact ML** : Profil de réussite impossible, signal trompeur pour le modèle.
- **Action envisagée** : Arbitrer avec la source ; à défaut, rendre les deux valeurs manquantes.

### `CON_CREDITED_GT_ENROLLED` — UE créditées supérieures aux UE inscrites

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : coherence_variables
- **Variables** : ue_creditees_s*, ue_inscrites_s*
- **Justification** : Les UE créditées font partie des UE inscrites (relation vérifiée sur le fichier).
- **Méthode** : Comparaison ligne à ligne
- **Impact ML** : Incohérence de comptage.
- **Action envisagée** : Vérifier la source.

### `CON_NO_EVAL_GT_ENROLLED` — UE sans évaluation supérieures aux UE inscrites

- **Gravité** : HIGH · **Diagnostic** : erreur_confirmee · **Catégorie** : coherence_variables
- **Variables** : ue_sans_evaluation_s*, ue_inscrites_s*
- **Justification** : Une UE sans évaluation est une UE inscrite.
- **Méthode** : Comparaison ligne à ligne
- **Impact ML** : Incohérence de comptage.
- **Action envisagée** : Vérifier la source.

### `CON_VALIDATED_PLUS_NO_EVAL_GT_ENROLLED` — UE validées + UE sans évaluation > UE inscrites

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : ue_validees_s*, ue_sans_evaluation_s*, ue_inscrites_s*
- **Justification** : Si une UE validée a été évaluée, les deux ensembles sont disjoints. Une UE créditée peut toutefois être validée sans évaluation : diagnostic à confirmer.
- **Méthode** : Comparaison ligne à ligne
- **Impact ML** : Comptages potentiellement incohérents.
- **Action envisagée** : Examiner avec la définition exacte des UE créditées.

### `CON_CREDITED_GT_VALIDATED` — UE créditées supérieures aux UE validées

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : ue_creditees_s*, ue_validees_s*
- **Justification** : Hypothèse : une UE créditée (équivalence) est comptée comme validée. Non confirmé par le dictionnaire.
- **Méthode** : Comparaison ligne à ligne
- **Impact ML** : Possible incohérence de comptage.
- **Action envisagée** : Confirmer la définition des UE créditées avant tout traitement.

### `CON_EVALUATIONS_LT_VALIDATED` — Moins d'évaluations que d'UE validées hors crédits

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : nb_evaluations_s*, ue_validees_s*, ue_creditees_s*
- **Justification** : Une UE validée non créditée suppose au moins une évaluation (plusieurs évaluations par UE sont possibles : seule la borne basse est contrôlée).
- **Méthode** : nb_evaluations < ue_validees − ue_creditees
- **Impact ML** : Résultats semestriels peu fiables.
- **Action envisagée** : Vérifier les comptages auprès de la source.

### `CON_ACTIVITY_WITHOUT_ENROLMENT` — Évaluations ou note sans aucune UE inscrite

- **Gravité** : HIGH · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : ue_inscrites_s*, nb_evaluations_s*, note_moyenne_s*
- **Justification** : Sans UE inscrite, aucune évaluation ni note ne devrait exister.
- **Méthode** : ue_inscrites = 0 et (nb_evaluations > 0 ou note > 0)
- **Impact ML** : Signal contradictoire pour le modèle.
- **Action envisagée** : Vérifier la source.

### `CON_ZERO_GRADE_WITH_VALIDATED` — Note moyenne nulle malgré des UE validées

- **Gravité** : HIGH · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : note_moyenne_s*, ue_validees_s*
- **Justification** : Le dictionnaire justifie une note nulle par l'absence d'UE validée ; avec des UE validées, le 0 ressemble à un code de valeur manquante.
- **Méthode** : note = 0 et ue_validees > 0
- **Impact ML** : Note artificiellement basse, confusion avec les abandons.
- **Action envisagée** : Traiter le 0 comme manquant dans ce cas, après validation.

### `CON_PASSING_GRADE_NO_VALIDATED` — Moyenne ≥ 10/20 sans aucune UE validée

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : note_moyenne_s*, ue_validees_s*
- **Justification** : HYPOTHÈSE : une UE se valide à 10/20 ; une moyenne suffisante sans UE validée est surprenante (compensation, notes partielles possibles).
- **Méthode** : note ≥ seuil et ue_validees = 0 et ue_inscrites > 0
- **Impact ML** : Possible incohérence entre note et résultats.
- **Action envisagée** : Examiner les cas ; ne pas corriger automatiquement.

### `CON_GRADE_WITHOUT_EVALUATION` — Note moyenne positive sans aucune évaluation

- **Gravité** : HIGH · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : note_moyenne_s*, nb_evaluations_s*
- **Justification** : Une note résulte d'évaluations.
- **Méthode** : note > 0 et nb_evaluations = 0
- **Impact ML** : Note non fondée.
- **Action envisagée** : Vérifier la source.

### `CON_AGE_MONTHS` — Âge en mois incohérent avec l'âge en années

- **Gravité** : HIGH · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : age_inscription, age_inscription_mois
- **Justification** : Âge en années révolues ⇒ 12 × âge ≤ âge_mois ≤ 12 × âge + 11. La divergence ne dit pas laquelle des deux valeurs est fausse.
- **Méthode** : Encadrement 12a ≤ m ≤ 12a + 11
- **Impact ML** : Deux versions contradictoires de la même information.
- **Action envisagée** : Ne pas arbitrer automatiquement ; privilégier la variable documentée (années) si l'autre est exclue comme redondante.

### `CON_ADMISSION_ARCHIVE` — Divergence importante entre note d'admission et note archivée

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : note_admission, note_admission_archive
- **Justification** : Deux exports de la même note devraient concorder ; de petits écarts systématiques (≈ ±3 points) existent, seul un écart supérieur à la tolérance est signalé.
- **Méthode** : |note_admission − note_admission_archive| > tolérance
- **Impact ML** : Information contradictoire ; impossible de savoir quel export est correct.
- **Action envisagée** : Ne pas arbitrer automatiquement ; documenter le choix de la variable de référence.

### `CON_NIVEAU_DOSSIER` — Niveau du dossier incohérent avec la note antérieure

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : niveau_dossier, note_diplome_anterieur
- **Justification** : Le niveau est dérivé de la note antérieure (dictionnaire). Les seuils (120 / 140 / 160) sont INFÉRÉS du fichier, où ils séparent parfaitement les valeurs du domaine.
- **Méthode** : Comparaison aux seuils inférés
- **Impact ML** : Deux informations contradictoires ; redondance imparfaite.
- **Action envisagée** : Vérifier ; en cas d'exclusion de niveau_dossier (redondant), l'incohérence disparaît.

### `CON_FILIERE_REGIME` — Filière « (soir) » incohérente avec le régime des cours

- **Gravité** : HIGH · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : filiere, regime_cours
- **Justification** : Une filière libellée « (soir) » implique des cours du soir, et réciproquement dans le fichier (dépendance observée).
- **Méthode** : Comparaison de la mention « (soir) » et du régime
- **Impact ML** : Information administrative contradictoire.
- **Action envisagée** : Vérifier la source.

### `CON_ADMISSION_MODE_AGE` — Admission « Plus de 23 ans » avec un âge inférieur à 23 ans

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : mode_admission, age_inscription
- **Justification** : Le libellé de la voie d'admission suppose un âge minimal (la date exacte d'appréciation de l'âge n'est pas connue).
- **Méthode** : Comparaison libellé / âge
- **Impact ML** : Incohérence administrative.
- **Action envisagée** : Vérifier la source.

### `CON_GRADUATE_WITHOUT_UE` — Diplômé sans aucune UE inscrite en S1 et en S2

- **Gravité** : MEDIUM · **Diagnostic** : anomalie_potentielle · **Catégorie** : coherence_variables
- **Variables** : statut_academique, ue_inscrites_s1, ue_inscrites_s2
- **Justification** : Un diplômé sans UE inscrite la première année est surprenant ; des parcours particuliers (équivalences, reprises) restent possibles.
- **Méthode** : Cible = Diplômé et ue_inscrites_s1 = ue_inscrites_s2 = 0
- **Impact ML** : Profil atypique difficile à apprendre ; possible erreur d'export.
- **Action envisagée** : Examiner ces profils ; ne pas supprimer sans justification.

## Détecteur `statistical`

### `UNI_OUTLIER` — Valeur statistiquement atypique

- **Gravité** : INFO · **Diagnostic** : valeur_atypique · **Catégorie** : atypique_univarie
- **Variables** : variables numériques
- **Justification** : Valeur au-delà des seuils d'au moins une méthode (IQR, Z-score, Z-score modifié). Une valeur atypique n'est pas une erreur.
- **Méthode** : IQR / Z-score / Z-score modifié (MAD)
- **Impact ML** : Influence possible sur KNN (distances) ; faible sur les arbres.
- **Action envisagée** : Conserver par défaut ; envisager une mise à l'échelle robuste.

### `UNI_EXTREME_OUTLIER` — Valeur extrêmement atypique (consensus de méthodes robustes)

- **Gravité** : MEDIUM · **Diagnostic** : valeur_atypique · **Catégorie** : atypique_univarie
- **Variables** : variables numériques
- **Justification** : Valeur au-delà de Q3 + 3·IQR (ou Q1 − 3·IQR) ET de |Z modifié| > 3,5.
- **Méthode** : IQR × 3 et Z-score modifié
- **Impact ML** : Forte influence sur les méthodes à distances.
- **Action envisagée** : Vérifier la vraisemblance ; conserver si plausible.

### `UNI_ZERO_DISPERSION` — Dispersion robuste nulle : méthode non applicable

- **Gravité** : INFO · **Diagnostic** : information_descriptive · **Catégorie** : atypique_univarie
- **Variables** : variables numériques
- **Justification** : IQR ou MAD nul (valeurs concentrées) : les seuils dégénèrent et signaleraient toute valeur différente du mode.
- **Méthode** : IQR = 0 ou MAD = 0
- **Impact ML** : Aucun.
- **Action envisagée** : Analyser la distribution autrement (modalités rares).

### `UNI_RARE_CATEGORY` — Modalité rare

- **Gravité** : INFO · **Diagnostic** : information_descriptive · **Catégorie** : atypique_univarie
- **Variables** : variables qualitatives
- **Justification** : Modalité (après normalisation) observée dans moins de 1 % des cas.
- **Méthode** : Fréquence relative
- **Impact ML** : Instabilité de l'encodage ; modalité absente de certains plis.
- **Action envisagée** : Envisager un regroupement justifié métier (« Autre »).

## Détecteur `multivariate`

### `MUL_OUTLIER` — Observation atypique en plusieurs dimensions

- **Gravité** : INFO · **Diagnostic** : valeur_atypique · **Catégorie** : atypique_multivarie
- **Variables** : variables numériques individuelles
- **Justification** : Combinaison de valeurs inhabituelle (Isolation Forest et/ou LOF), alors que chaque valeur peut être normale isolément.
- **Méthode** : Isolation Forest / Local Outlier Factor
- **Impact ML** : Profil rare ; possible erreur combinée.
- **Action envisagée** : Examiner les observations signalées par les deux méthodes en priorité.

## Détecteur `redundancy`

### `RED_IDENTICAL_COLUMNS` — Colonnes identiques

- **Gravité** : MEDIUM · **Diagnostic** : risque_methodologique · **Catégorie** : redondance
- **Variables** : paires de variables
- **Justification** : Deux colonnes égales portent la même information.
- **Méthode** : Égalité des valeurs
- **Impact ML** : Double pondération (KNN), importances partagées.
- **Action envisagée** : Conserver une seule colonne.

### `RED_NEAR_DUPLICATE` — Colonnes quasi identiques

- **Gravité** : MEDIUM · **Diagnostic** : risque_methodologique · **Catégorie** : redondance
- **Variables** : paires de variables numériques
- **Justification** : Corrélation ≥ 0,98 : la seconde colonne n'apporte presque rien.
- **Méthode** : Corrélation de Pearson et de Spearman
- **Impact ML** : Redondance, importances diluées, incohérences possibles entre versions.
- **Action envisagée** : Choisir une version de référence (justification métier).

### `RED_DETERMINISTIC` — Dépendance déterministe entre variables

- **Gravité** : MEDIUM · **Diagnostic** : risque_methodologique · **Catégorie** : redondance
- **Variables** : paires de variables
- **Justification** : Une variable est (quasi) entièrement déterminée par une autre (dérivation documentée ou constatée).
- **Méthode** : Dépendance fonctionnelle (part des valeurs déterminées)
- **Impact ML** : Information dupliquée ; risque d'incohérence entre les deux versions.
- **Action envisagée** : Conserver la variable source ; exclure la variable dérivée sauf justification.

### `RED_HIGH_CORRELATION` — Forte corrélation entre variables numériques

- **Gravité** : INFO · **Diagnostic** : information_descriptive · **Catégorie** : redondance
- **Variables** : paires de variables
- **Justification** : Une forte corrélation est une association statistique, pas nécessairement une redondance.
- **Méthode** : Corrélation de Spearman
- **Impact ML** : Multicolinéarité ; importances partagées entre variables corrélées.
- **Action envisagée** : Tenir compte de la corrélation dans l'interprétation des importances.

### `RED_CATEGORICAL_ASSOCIATION` — Forte association entre variables qualitatives

- **Gravité** : INFO · **Diagnostic** : information_descriptive · **Catégorie** : redondance
- **Variables** : paires de variables
- **Justification** : V de Cramér élevé entre deux variables qualitatives.
- **Méthode** : V de Cramér
- **Impact ML** : Information partiellement dupliquée.
- **Action envisagée** : Examiner le sens métier avant toute exclusion.

## Détecteur `leakage`

### `LEA_IDENTIFIER` — Identifiant utilisable comme variable

- **Gravité** : MEDIUM · **Diagnostic** : risque_methodologique · **Catégorie** : fuite_donnees
- **Variables** : id_etudiant
- **Justification** : Un identifiant n'a aucun sens prédictif ; un modèle peut toutefois le mémoriser.
- **Méthode** : Rôle déclaré dans le dictionnaire
- **Impact ML** : Apprentissage artificiel, sur-apprentissage.
- **Action envisagée** : Exclure des variables explicatives ; le réserver aux contrôles de chevauchement.

### `LEA_DUPLICATE_SPLIT` — Même étudiant présent plusieurs fois : risque de chevauchement

- **Gravité** : HIGH · **Diagnostic** : risque_methodologique · **Catégorie** : fuite_donnees
- **Variables** : id_etudiant
- **Justification** : La SAÉ impose qu'un étudiant ne figure pas dans des ensembles différents.
- **Méthode** : Identifiants répétés
- **Impact ML** : Score de test optimiste (le modèle a vu l'étudiant à l'apprentissage).
- **Action envisagée** : Dédoublonner avant la séparation ou découper par groupe d'identifiant.

### `LEA_TECHNICAL_METADATA` — Métadonnée technique sans sens métier

- **Gravité** : MEDIUM · **Diagnostic** : risque_methodologique · **Catégorie** : fuite_donnees
- **Variables** : version_export, code_campagne
- **Justification** : Une information d'export peut refléter le mode de constitution du fichier et créer une corrélation artificielle avec la cible.
- **Méthode** : Rôle déclaré dans le dictionnaire
- **Impact ML** : Apprentissage d'un artefact de collecte, non généralisable.
- **Action envisagée** : Exclure des variables explicatives.

### `LEA_TARGET_ASSOCIATION` — Association suspecte avec la cible

- **Gravité** : MEDIUM · **Diagnostic** : risque_methodologique · **Catégorie** : fuite_donnees
- **Variables** : variables explicatives
- **Justification** : Association forte d'une variable NON académique (ou d'une modalité pure) avec la cible : à vérifier, sans conclure automatiquement à une fuite.
- **Méthode** : V de Cramér / rapport de corrélation η / pureté des modalités
- **Impact ML** : Score artificiellement élevé si l'information dérive de la cible.
- **Action envisagée** : Vérifier la date de disponibilité et le mode de calcul de la variable.

### `LEA_STRONG_PREDICTOR` — Forte association avec la cible d'une variable disponible en fin de S2

- **Gravité** : INFO · **Diagnostic** : information_descriptive · **Catégorie** : fuite_donnees
- **Variables** : variables des semestres 1 et 2
- **Justification** : Les résultats de S1/S2 sont disponibles au moment de la prédiction : leur association forte est attendue et légitime.
- **Méthode** : V de Cramér / rapport de corrélation η
- **Impact ML** : Aucun en soi ; modèle dépendant de ces variables.
- **Action envisagée** : Conserver ; mentionner la dépendance dans l'interprétation.

### `LEA_INFORMATIVE_MISSINGNESS` — Valeurs manquantes associées à la cible

- **Gravité** : MEDIUM · **Diagnostic** : risque_methodologique · **Catégorie** : fuite_donnees
- **Variables** : variables avec valeurs manquantes
- **Justification** : Un taux de manque très différent selon la classe signifie que le manque est informatif.
- **Méthode** : Test du khi-deux et V de Cramér sur l'indicateur de manque
- **Impact ML** : Une imputation naïve efface ou crée un signal ; un indicateur de manque peut capter un artefact de collecte.
- **Action envisagée** : Décider explicitement (indicateur de manque ou non) et vérifier la plausibilité métier.

### `LEA_AUDIT_STATISTICS` — Statistiques d'audit calculées sur l'ensemble des données

- **Gravité** : INFO · **Diagnostic** : risque_methodologique · **Catégorie** : fuite_donnees
- **Variables** : toutes
- **Justification** : Les seuils d'audit (quantiles, IQR, corrélations) sont descriptifs et calculés avant la séparation apprentissage/test.
- **Méthode** : Rappel de protocole
- **Impact ML** : Fuite si ces valeurs sont réutilisées pour un traitement appris (imputation, bornage).
- **Action envisagée** : Recalculer tout paramètre appris dans les pipelines, sur l'apprentissage de chaque pli.

## Détecteur `class_balance`

### `IMB_CLASS_IMBALANCE` — Déséquilibre des classes de la cible

- **Gravité** : MEDIUM · **Diagnostic** : risque_methodologique · **Catégorie** : desequilibre_classes
- **Variables** : statut_academique
- **Justification** : Classes d'effectifs inégaux : risque méthodologique, pas erreur individuelle.
- **Méthode** : Effectifs et ratio majoritaire / minoritaire
- **Impact ML** : Accuracy trompeuse ; classe minoritaire mal reconnue.
- **Action envisagée** : Stratifier séparation et plis ; métrique adaptée (F1 macro) ; pondération éventuelle évaluée en validation croisée — aucun rééquilibrage dans l'audit.

## Hypothèses d'audit (absentes du dictionnaire)

- `age_inscription` : Plage plausible [16 ; 70] ans : hypothèse d'audit, absente du dictionnaire
- `taux_chomage` : Bornes [0 ; 100] déduites de la définition d'un taux, pas du dictionnaire
- `niveau_dossier` : seuils 120 / 140 / 160 inférés du fichier.
- `id_etudiant` : motif `ET` + 6 chiffres observé dans le fichier.
