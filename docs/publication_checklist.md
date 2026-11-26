# Checklist de publication GitHub

> Le dépôt est **public dès sa création**, par décision du binôme (voir D-012 dans
> [`decision_log.md`](decision_log.md)). Tout ce qui est poussé est donc immédiatement visible et peut
> être copié ou indexé : les sections 2 et 3 sont à vérifier **avant chaque push**, pas seulement à la fin.
> Le projet est présenté comme un **travail pédagogique**, et non comme un système opérationnel de
> décision académique.

## 1. Autorisations

- [ ] Autorisation de publier le fichier `parcours_etudiants.csv` obtenue (à défaut : **ne pas publier**,
      il reste exclu par `.gitignore`).
- [ ] Droits de redistribution de `SAE5_03.pdf` et `Dictionnaire_variables.pdf` vérifiés (à défaut : non publiés).
- [ ] Consignes de l'établissement concernant la publication des travaux vérifiées.
- [ ] Accord écrit des deux membres du binôme.
- [ ] Publication du travail **avant la remise** compatible avec les règles de l'établissement
      (un dépôt public peut être consulté par d'autres binômes de la promotion).
- [ ] Adresse e-mail des commits : adresse `noreply` de GitHub recommandée (les e-mails des commits
      d'un dépôt public sont visibles par tous).

## 2. Contenu sensible

- [ ] Aucune donnée personnelle ni identifiant étudiant dans les fichiers versionnés.
- [ ] Aucune donnée individuelle dans les **sorties** des notebooks (tableaux `head()`, lignes d'étudiants).
- [ ] Aucune figure ou table de `reports/` ne permet d'identifier un étudiant.
- [ ] Aucun secret (`.env`, jeton, mot de passe, clé) dans les fichiers ni dans l'historique.
- [ ] Aucun chemin absolu personnel (dossier utilisateur, nom de session) dans les fichiers versionnés.

## 3. Historique Git

- [ ] `git log --stat` relu : aucun fichier de données, PDF ou modèle n'a jamais été commité.
- [ ] Si un fichier sensible apparaît dans l'historique : **ne pas publier** ; réécrire l'historique
      (ou créer un nouveau dépôt propre) avant tout passage en public.
- [ ] `git status --ignored` vérifié : les fichiers ignorés correspondent à l'attendu.

## 4. Propreté

- [ ] Fichiers temporaires, checkpoints et caches absents.
- [ ] Notebooks de développement nettoyés ou retirés s'ils n'apportent rien à la lecture.
- [ ] Sorties de notebooks allégées (pas de sorties volumineuses inutiles).

## 5. Reproductibilité et qualité

- [ ] Installation testée dans un `.venv` neuf avec `requirements.txt`.
- [ ] Notebook final exécuté entièrement (*Restart Kernel and Run All Cells*) sans erreur.
- [ ] `python -m pytest` et `python -m ruff check .` passent.
- [ ] Résultats du README identiques à ceux du notebook final.
- [ ] Procédure d'obtention des données expliquée (`data/README.md`) pour un lecteur sans accès au CSV.

## 6. Présentation

- [ ] README finalisé : résultats réels, limites, mention du cadre pédagogique.
- [ ] Auteurs identifiés et contributions décrites.
- [ ] Licence choisie **d'un commun accord** (ou absence de licence assumée), compatible avec les
      ressources pédagogiques. Aucune licence n'est ajoutée par défaut.
- [ ] Description et topics du dépôt renseignés sur GitHub.

## 7. Mise en valeur portfolio (après la remise)

- [ ] Toutes les cases ci-dessus sont cochées.
- [ ] Les deux membres valident la version mise en avant (README, résultats, épinglage sur leur profil).
