# Collaboration en binôme

> Complète [`CONTRIBUTING.md`](../CONTRIBUTING.md), qui décrit le workflow Git. Ce document précise
> **qui fait quoi**, comment se déroule la relecture et comment le travail est intégré au notebook final.

## 1. Principes

- **Responsabilité partagée.** L'évaluation est individuelle : chaque membre doit pouvoir justifier,
  expliquer et modifier **toute** partie du code et des décisions, pas seulement les siennes.
- **Tâches réparties, connaissances communes.** Chaque tâche a un responsable et un relecteur
  (voir [`project_plan.md`](project_plan.md)).
- **Une source de vérité par élément.** Paramètres dans `src/config.py`, fonctions dans `src/`,
  décisions dans [`decision_log.md`](decision_log.md), résultats validés dans le notebook final.

## 2. Rôles

| Rôle | Responsabilités |
|---|---|
| Responsable d'une tâche | Crée la branche, réalise le travail, vérifie l'exécution, ouvre la Pull Request |
| Relecteur | Vérifie la méthode, l'absence de fuite, la lisibilité ; pose des questions jusqu'à pouvoir expliquer le travail |
| Intégrateur (temporaire) | Seul à modifier le notebook final pendant une intégration ; rôle tournant par mission |

## 3. Règles de travail sur les notebooks

1. **Ne jamais modifier simultanément** `notebooks/SAE5_03_Data_Mining.ipynb`. L'intégrateur prévient
   l'autre membre avant de commencer et après avoir fusionné.
2. Chaque mission est développée dans son notebook de `notebooks/development/`.
3. Toute fonction utilisée plus d'une fois est déplacée dans le module `src/` correspondant.
4. Avant chaque commit : *Restart Kernel and Run All Cells*, puis vérifier qu'aucune sortie volumineuse
   (tableaux entiers, centaines de lignes, données individuelles) n'est enregistrée.
5. Ne jamais afficher de lignes individuelles d'étudiants dans un notebook destiné à être publié.

## 4. Procédure de revue

1. Le responsable ouvre une Pull Request en remplissant le modèle (`.github/pull_request_template.md`).
2. Le relecteur exécute le notebook ou les tests sur sa machine.
3. Le relecteur vérifie la checklist : protocole respecté, pas de fuite, décisions consignées,
   interprétations cohérentes avec les sorties réelles.
4. Les remarques sont traitées par de nouveaux commits sur la même branche.
5. Le relecteur approuve ; le responsable fusionne dans `main`, puis supprime la branche.

**Test de maîtrise :** avant d'approuver, le relecteur doit pouvoir expliquer oralement le travail à
l'autre membre (préparation à l'évaluation individuelle).

## 5. Intégration dans le notebook final

| Étape | Action |
|---|---|
| 1 | La mission est validée dans son notebook de développement (PR fusionnée) |
| 2 | L'intégrateur crée une branche `docs/integrate-mission-N` |
| 3 | Il reporte les cellules utiles : code appelant `src/`, tableaux, figures, interprétations |
| 4 | Il exécute le notebook final de haut en bas dans un noyau neuf |
| 5 | Il ouvre une PR ; l'autre membre relit le rendu complet |
| 6 | Après fusion, le rôle d'intégrateur passe à l'autre membre pour la mission suivante |

Le notebook final doit rester **compréhensible sans les notebooks de développement**.

## 6. Communication

- Point de synchronisation régulier (fréquence à définir par le binôme) : avancement, blocages, prochaines tâches.
- Le tableau GitHub Project reflète l'état réel des tâches.
- Toute décision méthodologique discutée oralement est **écrite** dans `decision_log.md`.
