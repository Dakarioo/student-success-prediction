"""Synthèses, exports (CSV, JSON), rapport Markdown et catalogue des règles.

Le rapport Markdown est destiné à ``reports/`` (versionnable) : il ne contient
AUCUN identifiant étudiant ni donnée individuelle, uniquement des agrégats.
Les fichiers détaillés (avec identifiants) restent dans ``outputs/audit/``,
dossier exclu du dépôt Git.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from src.data_quality.config import VARIABLE_SPECS
from src.data_quality.rules import RULES, rules_frame
from src.data_quality.schemas import (
    SEVERITY_LABELS_FR,
    SEVERITY_ORDER,
    STATUS_LABELS_FR,
    Category,
    DiagnosticStatus,
    Severity,
)

if TYPE_CHECKING:
    from src.data_quality.audit import AuditResult

logger = logging.getLogger(__name__)

_SEVERITY_RANK = {s.value: i for i, s in enumerate(SEVERITY_ORDER)}
_CATEGORY_LABELS = {
    Category.STRUCTURE.value: "Structure",
    Category.MISSING.value: "Valeurs manquantes",
    Category.DUPLICATES.value: "Doublons",
    Category.FORMAT.value: "Format et saisie",
    Category.DOMAIN.value: "Domaine métier",
    Category.CONSISTENCY.value: "Cohérence entre variables",
    Category.UNIVARIATE.value: "Atypiques univariés",
    Category.MULTIVARIATE.value: "Atypiques multivariés",
    Category.REDUNDANCY.value: "Redondances",
    Category.LEAKAGE.value: "Fuite de données",
    Category.IMBALANCE.value: "Déséquilibre des classes",
}


# ============================================================================ synthèses
def synthesis_by_rule(anomalies: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par règle : signalements, observations distinctes, variables."""
    columns = [
        "rule_id",
        "titre",
        "categorie",
        "gravite",
        "diagnostic",
        "n_signalements",
        "n_observations_distinctes",
        "variables",
    ]
    if anomalies.empty:
        return pd.DataFrame(columns=columns)
    grouped = anomalies.groupby(["rule_id", "severity"], sort=False)
    table = grouped.agg(
        n_signalements=("anomaly_id", "size"),
        n_observations_distinctes=("row_index", "nunique"),
        variables=("column", lambda s: ", ".join(sorted(s.dropna().astype(str).unique()))),
    ).reset_index()
    table["titre"] = table["rule_id"].map(lambda r: RULES[r].title)
    table["categorie"] = table["rule_id"].map(lambda r: RULES[r].category.value)
    table["diagnostic"] = table["rule_id"].map(lambda r: RULES[r].status.value)
    table = table.rename(columns={"severity": "gravite"})
    table["_rank"] = table["gravite"].map(_SEVERITY_RANK)
    table = table.sort_values(["_rank", "n_signalements"], ascending=[True, False])
    return table[columns].reset_index(drop=True)


def summary_counts(anomalies: pd.DataFrame, n_rows: int) -> dict[str, Any]:
    """Totaux : signalements vs observations distinctes, par gravité, catégorie, statut."""
    obs = anomalies[anomalies["scope"] == "observation"]
    not_info = obs[obs["severity"] != Severity.INFO.value]
    serious = obs[obs["severity"].isin([Severity.CRITICAL.value, Severity.HIGH.value])]

    def per(column: str) -> dict[str, dict[str, int]]:
        reports = anomalies[column].value_counts()
        rows = obs.groupby(column)["row_index"].nunique()
        return {
            str(k): {
                "signalements": int(reports.get(k, 0)),
                "observations_distinctes": int(rows.get(k, 0)),
            }
            for k in reports.index
        }

    return {
        "n_signalements": int(len(anomalies)),
        "n_signalements_individuels": int(len(obs)),
        "n_signalements_globaux": int((anomalies["scope"] == "global").sum()),
        "n_observations_distinctes": int(obs["row_index"].nunique()),
        "n_observations_distinctes_hors_info": int(not_info["row_index"].nunique()),
        "n_observations_critique_ou_elevee": int(serious["row_index"].nunique()),
        "part_observations_concernees": round(obs["row_index"].nunique() / n_rows, 4)
        if n_rows
        else 0.0,
        "part_observations_hors_info": round(not_info["row_index"].nunique() / n_rows, 4)
        if n_rows
        else 0.0,
        "par_gravite": per("severity"),
        "par_categorie": per("category"),
        "par_diagnostic": per("diagnostic_status"),
    }


def quality_by_variable(result: AuditResult) -> pd.DataFrame:
    """Qualité par variable : conformité, manquants et signalements par gravité."""
    structure = result.tables.get("structure_variables", pd.DataFrame())
    missing = result.tables.get("valeurs_manquantes", pd.DataFrame())
    table = (
        structure.copy()
        if not structure.empty
        else pd.DataFrame({"variable": list(dict.fromkeys(result.anomalies["column"].dropna()))})
    )
    if not missing.empty:
        table = table.merge(
            missing[["variable", "n_natifs", "n_deguises", "n_total", "pct_total"]].rename(
                columns={"n_total": "n_manquants", "pct_total": "pct_manquants"}
            ),
            on="variable",
            how="left",
        )
    obs = result.anomalies[result.anomalies["scope"] == "observation"]
    levels = [s.value for s in SEVERITY_ORDER]
    pivot = pd.crosstab(obs["column"], obs["severity"]).reindex(columns=levels, fill_value=0)
    pivot.columns = [f"n_{c.lower()}" for c in pivot.columns]
    rows_hors_info = (
        obs[obs["severity"] != Severity.INFO.value].groupby("column")["row_index"].nunique()
    )
    table = table.merge(pivot, left_on="variable", right_index=True, how="left")
    table["n_observations_concernees_hors_info"] = table["variable"].map(rows_hors_info)
    count_cols = [c for c in table.columns if c.startswith("n_")]
    table[count_cols] = table[count_cols].fillna(0).astype(int)
    n = max(result.n_rows, 1)
    table["pct_observations_concernees_hors_info"] = (
        100 * table["n_observations_concernees_hors_info"] / n
    ).round(2)
    return table.sort_values(
        ["n_critical", "n_high", "n_observations_concernees_hors_info"], ascending=False
    ).reset_index(drop=True)


def methodological_risks(result: AuditResult) -> pd.DataFrame:
    """Signalements de fuite, déséquilibre et redondance (risques pour le ML)."""
    cats = {Category.LEAKAGE.value, Category.IMBALANCE.value, Category.REDUNDANCY.value}
    subset = result.anomalies[result.anomalies["category"].isin(cats)]
    return subset[
        [
            "rule_id",
            "category",
            "severity",
            "diagnostic_status",
            "column",
            "related_columns",
            "observed_value",
            "description",
            "potential_impact",
            "suggested_action",
        ]
    ].reset_index(drop=True)


# ============================================================================== exports
def export_results(
    result: AuditResult,
    output_dir: Path | str | None = None,
    figures: bool = True,
    report_path: Path | str | None = None,
) -> dict[str, Path]:
    """Écrit tous les fichiers de sortie et retourne leurs chemins."""
    out_dir = Path(output_dir or result.config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    def write(name: str, frame: pd.DataFrame | None) -> None:
        if frame is None:
            return
        path = out_dir / f"{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        written[name] = path

    a = result.anomalies
    write("anomalies_detail", a)
    write("anomalies_synthese", synthesis_by_rule(a))
    write("qualite_variables", quality_by_variable(result))
    write("doublons", result.tables.get("doublons"))
    write("valeurs_manquantes", _missing_export(result))
    write(
        "incoherences_metier",
        a[a["category"].isin([Category.DOMAIN.value, Category.CONSISTENCY.value])],
    )
    write("valeurs_atypiques", result.tables.get("valeurs_atypiques"))
    write("scores_multivaries", result.tables.get("scores_multivaries"))
    write("redondances", _redundancy_export(result))
    write("risques_methodologiques", methodological_risks(result))
    write("association_cible", result.tables.get("association_cible"))

    figure_paths: dict[str, Path] = {}
    if figures:
        from src.data_quality.visualization import save_audit_figures

        figure_paths = save_audit_figures(result, out_dir / "figures")
        written.update({f"figure_{k}": v for k, v in figure_paths.items()})

    summary_path = out_dir / "audit_resume.json"
    summary_path.write_text(
        json.dumps(build_summary(result), ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    written["audit_resume"] = summary_path

    if report_path is not False:
        report = Path(report_path or result.config.report_path)
        write_report(result, report, figure_paths)
        written["rapport"] = report
    logger.info("%d fichiers écrits dans %s", len(written), out_dir)
    return written


def _missing_export(result: AuditResult) -> pd.DataFrame | None:
    table = result.tables.get("valeurs_manquantes")
    by_class = result.tables.get("manquants_par_classe")
    if table is None:
        return None
    if by_class is not None and not by_class.empty:
        renamed = by_class.rename(
            columns={c: f"pct_manquants_{c}" for c in by_class.columns if c != "variable"}
        )
        table = table.merge(renamed, on="variable", how="left")
    return table


def _redundancy_export(result: AuditResult) -> pd.DataFrame | None:
    redundancy = result.tables.get("redondances")
    pairs = result.tables.get("paires_documentees")
    if redundancy is None:
        return None
    if pairs is None or pairs.empty:
        return redundancy
    long = pairs.melt(id_vars=["paire", "lecture"], var_name="mesure", value_name="valeur")
    long = long.dropna(subset=["valeur"])
    split = long["paire"].str.split(" / ", expand=True)
    documented = pd.DataFrame(
        {
            "variable_1": split[0],
            "variable_2": split[1],
            "type": "PAIRE_DOCUMENTEE",
            "mesure": long["mesure"],
            "valeur": long["valeur"],
            "commentaire": long["lecture"],
        }
    )
    return pd.concat([redundancy, documented], ignore_index=True)


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (Path, datetime)):
        return str(value)
    if isinstance(value, pd.DataFrame):
        return value.to_dict("records")
    return str(value)


def build_summary(result: AuditResult) -> dict[str, Any]:
    """Résumé structuré (JSON) : métadonnées, comptages, synthèses par détecteur."""
    config = {
        k: v for k, v in asdict(result.config).items() if k not in {"output_dir", "report_path"}
    }
    return {
        "genere_le": datetime.now().isoformat(timespec="seconds"),
        "source": result.source,
        "sha256_source": result.source_sha256,
        "dimensions": {"lignes": result.n_rows, "colonnes": result.n_columns},
        "controles_executes": result.detectors_run,
        "erreurs": result.errors,
        "duree_s": result.duration_s,
        "comptages": result.counts(),
        "syntheses_detecteurs": result.summaries,
        "configuration": config,
    }


# ============================================================================== Markdown
def md_table(frame: pd.DataFrame, max_rows: int | None = None, floatfmt: str = "{:.3g}") -> str:
    """Tableau Markdown sans dépendance externe."""
    if frame is None or frame.empty:
        return "_Aucune ligne._\n"
    data = frame.head(max_rows) if max_rows else frame

    def cell(value: Any) -> str:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return ""
        if isinstance(value, (float, np.floating)):
            return floatfmt.format(value)
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(map(str, data.columns)) + " |",
        "|" + "|".join("---" for _ in data.columns) + "|",
    ]
    lines += [
        "| " + " | ".join(cell(v) for v in row) + " |" for row in data.itertuples(index=False)
    ]
    if max_rows and len(frame) > max_rows:
        lines.append(f"\n_… {len(frame) - max_rows} ligne(s) supplémentaire(s) dans les CSV._")
    return "\n".join(lines) + "\n"


def _fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _pct(part: float) -> str:
    return f"{100 * part:.1f} %".replace(".", ",")


def write_report(
    result: AuditResult, path: Path | str, figures: dict[str, Path] | None = None
) -> Path:
    """Génère le rapport d'audit Markdown (agrégats uniquement)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    builder = _ReportBuilder(result, path, figures or {})
    path.write_text(builder.build(), encoding="utf-8")
    return path


class _ReportBuilder:
    """Assemble les 15 sections du rapport à partir des résultats réels."""

    def __init__(self, result: AuditResult, path: Path, figures: dict[str, Path]) -> None:
        self.r = result
        self.path = path
        self.figures = figures
        self.counts = result.counts()
        self.synthesis = synthesis_by_rule(result.anomalies)
        self.parts: list[str] = []

    # -- utilitaires -----------------------------------------------------------------
    def add(self, text: str = "") -> None:
        self.parts.append(text)

    def figure(self, name: str, caption: str) -> None:
        if name in self.figures:
            rel = os.path.relpath(self.figures[name], self.path.parent).replace(os.sep, "/")
            self.add(f"![{caption}]({rel})\n")
            self.add(f"*Figure — {caption}.*\n")

    def rule_count(self, rule_id: str) -> tuple[int, int]:
        rows = self.synthesis[self.synthesis["rule_id"] == rule_id]
        return int(rows["n_signalements"].sum()), int(rows["n_observations_distinctes"].sum())

    # -- assemblage ------------------------------------------------------------------
    def build(self) -> str:
        self.add("# Rapport d'audit de qualité des données\n")
        self.add(
            f"> Rapport généré automatiquement le {datetime.now():%Y-%m-%d à %H:%M} par "
            "`src/data_quality` à partir des résultats réels de l'audit. Il ne contient "
            "aucun identifiant étudiant : le détail par observation est dans "
            "`outputs/audit/anomalies_detail.csv` (non versionné). L'audit **ne modifie "
            "aucune donnée**.\n"
        )
        for section in (
            self.s01_dataset,
            self.s02_executive,
            self.s03_method,
            self.s04_global,
            self.s05_categories,
            self.s06_variables,
            self.s07_severity,
            self.s08_business,
            self.s09_duplicates,
            self.s10_outliers,
            self.s11_redundancy,
            self.s12_risks,
            self.s13_recommendations,
            self.s14_limits,
            self.s15_conclusion,
        ):
            section()
        return "\n".join(self.parts)

    def s01_dataset(self) -> None:
        r = self.r
        self.add("## 1. Présentation du jeu de données\n")
        structure = r.tables.get("structure_variables", pd.DataFrame())
        roles = (
            structure["role"].value_counts().rename_axis("rôle").reset_index(name="variables")
            if not structure.empty
            else pd.DataFrame()
        )
        self.add(
            md_table(
                pd.DataFrame(
                    {
                        "Élément": [
                            "Fichier",
                            "Empreinte SHA-256",
                            "Observations",
                            "Colonnes",
                            "Variable cible",
                            "Contrôles exécutés",
                        ],
                        "Valeur": [
                            r.source,
                            f"`{r.source_sha256 or 'non calculée (DataFrame)'}`",
                            _fmt_int(r.n_rows),
                            str(r.n_columns),
                            "`statut_academique`",
                            ", ".join(r.detectors_run),
                        ],
                    }
                )
            )
        )
        if not roles.empty:
            self.add("Rôles des variables (dictionnaire officiel) :\n")
            self.add(md_table(roles))
        self.add(
            "La prédiction porte sur le statut observé à l'échéance normale de la formation, à "
            "partir des informations disponibles **jusqu'à la fin du semestre 2**.\n"
        )

    def s02_executive(self) -> None:
        c = self.counts
        self.add("## 2. Résumé exécutif\n")
        self.add(
            f"- **{_fmt_int(c['n_signalements'])} signalements** au total, dont "
            f"{_fmt_int(c['n_signalements_individuels'])} portant sur une observation et "
            f"{_fmt_int(c['n_signalements_globaux'])} globaux (variables, jeu de données).\n"
            f"- **{_fmt_int(c['n_observations_distinctes'])} observations distinctes** "
            f"concernées ({_pct(c['part_observations_concernees'])}), dont "
            f"**{_fmt_int(c['n_observations_distinctes_hors_info'])}** "
            f"({_pct(c['part_observations_hors_info'])}) par au moins un signalement de "
            "gravité supérieure à INFO, et "
            f"**{_fmt_int(c['n_observations_critique_ou_elevee'])}** par un signalement "
            "CRITICAL ou HIGH.\n"
            "- Un nombre de signalements n'est pas un nombre d'observations : une observation "
            "peut cumuler plusieurs anomalies.\n"
        )
        top = self.synthesis[self.synthesis["gravite"].isin(["CRITICAL", "HIGH"])].head(8)
        if not top.empty:
            self.add("Problèmes prioritaires (gravité CRITICAL / HIGH) :\n")
            for row in top.itertuples(index=False):
                self.add(
                    f"- **{row.titre}** (`{row.rule_id}`, {row.gravite}) : "
                    f"{_fmt_int(row.n_signalements)} signalement(s), "
                    f"{_fmt_int(row.n_observations_distinctes)} observation(s) — "
                    f"{row.variables or RULES[row.rule_id].columns}."
                )
            self.add("")
        balance = self.r.summaries.get("class_balance", {})
        if "ratio_desequilibre" in balance:
            self.add(
                f"- Cible déséquilibrée : classe majoritaire « {balance['classe_majoritaire']} », "
                f"minoritaire « {balance['classe_minoritaire']} », ratio "
                f"{balance['ratio_desequilibre']:.2f} (Accuracy d'un modèle constant : "
                f"{_pct(balance['baseline_accuracy'])}).\n"
            )

    def s03_method(self) -> None:
        cfg = self.r.config
        self.add("## 3. Méthodologie de détection\n")
        self.add(
            "Principes : lecture du CSV **en texte brut** (aucune conversion implicite), "
            "valeurs originales conservées dans chaque signalement, aucun nettoyage, aucune "
            "imputation, aucune suppression. Les contrôles croisés et statistiques portent sur "
            "les seules valeurs du domaine métier, pour ne pas re-signaler une valeur impossible "
            "déjà détectée. Gravité (impact) et diagnostic (certitude) sont deux axes "
            "distincts.\n"
        )
        rows = [
            (
                "Structure",
                "Colonnes attendues/inattendues, types, colonnes vides ou constantes",
                f"quasi constante ≥ {cfg.quasi_constant_share:.0%}",
            ),
            (
                "Valeurs manquantes",
                "Natives, espaces, NULL textuels, déguisées ; par ligne ; phi",
                f"ligne ≥ {cfg.row_missing_alert} manques ; "
                f"phi ≥ {cfg.missing_association_min_phi}",
            ),
            (
                "Doublons",
                "Exacts, identifiants divergents, contenu identique, après normalisation",
                "—",
            ),
            (
                "Format",
                "Variantes de modalités, synonymes, virgule décimale, texte, caractères",
                f"similarité ≥ {cfg.similar_category_ratio}",
            ),
            (
                "Domaine métier",
                "Bornes du dictionnaire, entiers ≥ 0, modalités, âges",
                f"âge plausible [{cfg.age_plausible_min} ; {cfg.age_plausible_max}] (hypothèse)",
            ),
            (
                "Cohérence",
                "UE, évaluations, notes, âges, exports, niveau, filière, admission",
                f"tolérance exports {cfg.admission_archive_tolerance:g} pts ; "
                f"validation {cfg.passing_grade:g}/20 (hypothèse)",
            ),
            (
                "Atypiques univariés",
                "IQR, Z-score (si |asymétrie| ≤ 1), Z-score modifié (MAD)",
                f"IQR × {cfg.iqr_factor} / × {cfg.iqr_extreme_factor} ; |z| > "
                f"{cfg.zscore_threshold} ; |M| > {cfg.modified_zscore_threshold} ; consensus ≥ "
                f"{cfg.min_methods_agreement} méthodes ; log1p si asymétrie > 1",
            ),
            (
                "Modalités rares",
                "Fréquence après normalisation",
                f"< {cfg.rare_category_share:.0%} et ≤ {cfg.rare_category_max_count} obs.",
            ),
            (
                "Atypiques multivariés",
                "Isolation Forest, LOF (facultatif)",
                f"contamination {cfg.multivariate_contamination} ; graine {cfg.random_state}",
            ),
            (
                "Redondances",
                "Égalité, corrélations, dépendances fonctionnelles, V de Cramér",
                f"|ρ| ≥ {cfg.high_correlation} / ≥ {cfg.near_identical_correlation} ; V ≥ "
                f"{cfg.cramers_v_threshold}",
            ),
            (
                "Fuite de données",
                "Rôle, disponibilité, association à la cible, manques informatifs",
                f"η ou V ≥ {cfg.target_association_threshold}",
            ),
            (
                "Déséquilibre",
                "Effectifs, proportions, ratio",
                f"ratio ≥ {cfg.class_imbalance_ratio_alert}",
            ),
        ]
        self.add(md_table(pd.DataFrame(rows, columns=["Famille", "Méthodes", "Seuils"])))
        self.add(
            "Le catalogue complet des règles (identifiant, justification, gravité) est dans "
            "`docs/audit_rules_catalog.md`.\n"
        )

    def s04_global(self) -> None:
        c = self.counts
        self.add("## 4. Résultats globaux\n")
        rows = []
        for level in SEVERITY_ORDER:
            info = c["par_gravite"].get(
                level.value, {"signalements": 0, "observations_distinctes": 0}
            )
            rows.append(
                (
                    f"{SEVERITY_LABELS_FR[level]} ({level.value})",
                    info["signalements"],
                    info["observations_distinctes"],
                )
            )
        self.add(
            md_table(
                pd.DataFrame(rows, columns=["Gravité", "Signalements", "Observations distinctes"])
            )
        )
        status_rows = [
            (STATUS_LABELS_FR[DiagnosticStatus(k)], v["signalements"], v["observations_distinctes"])
            for k, v in c["par_diagnostic"].items()
        ]
        self.add("Par nature du diagnostic :\n")
        self.add(
            md_table(
                pd.DataFrame(
                    status_rows, columns=["Diagnostic", "Signalements", "Observations distinctes"]
                )
            )
        )
        if self.r.errors:
            self.add(f"**Contrôles en échec** : {self.r.errors}\n")

    def s05_categories(self) -> None:
        self.add("## 5. Analyse par catégorie d'anomalies\n")
        a = self.r.anomalies
        obs = a[a["scope"] == "observation"]
        rows = []
        for cat, block in a.groupby("category"):
            worst = min(block["severity"], key=_SEVERITY_RANK.get)
            rows.append(
                (
                    _CATEGORY_LABELS.get(cat, cat),
                    len(block),
                    obs.loc[obs["category"] == cat, "row_index"].nunique(),
                    worst,
                    block["rule_id"].nunique(),
                )
            )
        table = pd.DataFrame(
            rows,
            columns=[
                "Catégorie",
                "Signalements",
                "Observations distinctes",
                "Gravité maximale",
                "Règles déclenchées",
            ],
        )
        self.add(md_table(table.sort_values("Signalements", ascending=False)))
        self.figure("04_signalements_par_categorie", "Signalements par catégorie et gravité")
        self.add("Détail par règle :\n")
        detail = self.synthesis.drop(columns=["variables"]).rename(
            columns={
                "rule_id": "Règle",
                "titre": "Intitulé",
                "categorie": "Catégorie",
                "gravite": "Gravité",
                "diagnostic": "Diagnostic",
                "n_signalements": "Signalements",
                "n_observations_distinctes": "Observations",
            }
        )
        self.add(md_table(detail))

    def s06_variables(self) -> None:
        self.add("## 6. Analyse par variable\n")
        quality = quality_by_variable(self.r)
        cols = [
            c
            for c in [
                "variable",
                "type_attendu",
                "type_observe",
                "pct_manquants",
                "n_critical",
                "n_high",
                "n_medium",
                "n_low",
                "n_observations_concernees_hors_info",
                "pct_observations_concernees_hors_info",
            ]
            if c in quality.columns
        ]
        top = quality.sort_values("n_observations_concernees_hors_info", ascending=False)
        self.add(
            "Variables classées par nombre d'observations concernées par un signalement de "
            "gravité supérieure à INFO (15 premières ; tableau complet : "
            "`qualite_variables.csv`) :\n"
        )
        self.add(md_table(top[cols], max_rows=15))
        self.figure("05_signalements_par_variable", "Variables les plus concernées")
        self.figure("01_valeurs_manquantes_par_variable", "Valeurs manquantes par variable")
        self.figure("02_carte_valeurs_manquantes", "Carte des valeurs manquantes")
        missing = self.r.summaries.get("missing_values", {})
        if missing:
            kinds = missing.get("par_nature", {})
            self.add(
                f"Valeurs manquantes : {_fmt_int(missing['n_cellules_manquantes'])} cellules "
                f"({_pct(missing['taux_cellules_manquantes'])}), "
                f"{_fmt_int(missing['n_observations_avec_manquant'])} observations avec au moins "
                f"une valeur manquante. Nature : {kinds.get('native', 0)} natives, "
                f"{kinds.get('deguisee', 0)} déguisées, {kinds.get('espaces_seuls', 0)} espaces "
                f"seuls, {kinds.get('null_textuel', 0)} NULL textuels. Les valeurs déguisées "
                "expliquent la lecture en texte de plusieurs colonnes numériques.\n"
            )

    def s07_severity(self) -> None:
        self.add("## 7. Répartition par gravité\n")
        a = self.r.anomalies
        pivot = pd.crosstab(a["category"].map(_CATEGORY_LABELS), a["severity"]).reindex(
            columns=[s.value for s in SEVERITY_ORDER], fill_value=0
        )
        self.add(md_table(pivot.reset_index().rename(columns={"category": "Catégorie"})))
        self.figure("03_signalements_par_gravite", "Répartition par gravité")
        self.figure(
            "06_signalements_par_observation", "Nombre de signalements (≥ LOW) par observation"
        )

    def s08_business(self) -> None:
        self.add("## 8. Principales incohérences métier\n")
        subset = self.synthesis[
            self.synthesis["categorie"].isin([Category.DOMAIN.value, Category.CONSISTENCY.value])
        ]
        if subset.empty:
            self.add("Aucune violation de domaine ni incohérence entre variables.\n")
            return
        table = subset.assign(
            justification=subset["rule_id"].map(lambda r: RULES[r].justification)
        )[
            [
                "rule_id",
                "titre",
                "gravite",
                "diagnostic",
                "n_signalements",
                "n_observations_distinctes",
                "variables",
                "justification",
            ]
        ]
        self.add(md_table(table))
        self.figure("12_incoherences_metier", "Violations de domaine et incohérences")
        self.figure("13_ue_validees_vs_inscrites_s1", "UE validées vs inscrites (S1)")
        controls = self.r.summaries.get("consistency", {}).get("controles", {})
        zero = sorted(k for k, v in controls.items() if v == 0)
        if zero:
            self.add(
                "Contrôles exécutés sans aucune incohérence détectée (sur les valeurs du "
                f"domaine) : {', '.join(f'`{z}`' for z in zero)}.\n"
            )

    def s09_duplicates(self) -> None:
        self.add("## 9. Analyse des doublons\n")
        d = self.r.summaries.get("duplicates")
        if not d:
            self.add("_Contrôle non exécuté._\n")
            return
        self.add(
            md_table(
                pd.DataFrame(
                    [
                        (
                            "Lignes en double exact (occurrences supplémentaires)",
                            d["n_lignes_doublons_exacts"],
                        ),
                        ("Groupes de doublons exacts", d["n_groupes_doublons_exacts"]),
                        ("Lignes partageant un identifiant", d["n_lignes_identifiant_repete"]),
                        ("Identifiants répétés", d["n_identifiants_repetes"]),
                        (
                            "Groupes d'identifiants aux informations divergentes",
                            d["n_groupes_identifiant_divergent"],
                        ),
                        (
                            "Groupes de contenu identique sous des identifiants différents",
                            d["n_groupes_contenu_identique_id_differents"],
                        ),
                        (
                            "Groupes de doublons révélés après normalisation",
                            d["n_groupes_doublons_normalises"],
                        ),
                    ],
                    columns=["Indicateur", "Valeur"],
                )
            )
        )
        if d["n_groupes_doublons_exacts"] and not d["n_groupes_identifiant_divergent"]:
            self.add(
                "Tous les identifiants répétés correspondent à des copies strictement "
                "identiques : il s'agit de doubles exports d'un même enregistrement, sans conflit "
                "d'information. Ils doivent être traités **avant** la séparation "
                "apprentissage/test (décision D-005), faute de quoi un même étudiant pourrait "
                "figurer dans les deux ensembles.\n"
            )

    def s10_outliers(self) -> None:
        self.add("## 10. Analyse des valeurs atypiques\n")
        table = self.r.tables.get("valeurs_atypiques")
        if table is not None and not table.empty:
            cols = [
                c
                for c in [
                    "variable",
                    "echelle",
                    "queue_examinee",
                    "n_analyses",
                    "mediane",
                    "borne_basse_iqr",
                    "borne_haute_iqr",
                    "methodes_applicables",
                    "n_atypiques_iqr",
                    "n_atypiques_z",
                    "n_atypiques_mad",
                    "n_atypiques_extremes",
                    "n_signalements_consensus",
                ]
                if c in table.columns
            ]
            self.add(md_table(table[cols]))
            self.add(
                "Lecture : une valeur atypique est **rare**, pas **fausse**. Les âges élevés "
                "(reprises d'études, voie « Plus de 23 ans ») ou les nombres d'UE élevés "
                "(parcours avec équivalences) sont plausibles. Les zéros structurels (note nulle "
                "sans UE validée, aucune UE inscrite) sont exclus des calculs ; pour les "
                "comptages, seule la queue haute est examinée. Les valeurs impossibles sont "
                "traitées par le domaine métier, pas ici.\n"
            )
        self.figure("07_boxplots_variables_numeriques", "Boxplots des variables numériques")
        self.figure("08_histogrammes_atypiques", "Histogrammes et valeurs signalées")
        rare = self.r.tables.get("modalites_rares")
        if rare is not None and not rare.empty:
            self.add("Modalités rares (après harmonisation) :\n")
            self.add(md_table(rare))
        multi = self.r.summaries.get("multivariate")
        if multi and multi.get("statut") == "executee":
            self.add(
                f"Analyse multivariée (périmètre d'ajustement : `{multi['perimetre_ajustement']}`) "
                f"sur {len(multi['variables'])} variables : "
                f"{multi['n_isolation_forest']} observations signalées par Isolation Forest, "
                f"{multi['n_lof']} par LOF, **{multi['n_consensus']} par les deux**. Les scores "
                "sont des rangs d'atypicité relatifs ; la part signalée est fixée par le "
                "paramètre de contamination.\n"
            )
        else:
            self.add("Analyse multivariée non exécutée (facultative : option `--multivariate`).\n")

    def s11_redundancy(self) -> None:
        self.add("## 11. Analyse des redondances\n")
        table = self.r.tables.get("redondances")
        self.add(md_table(table))
        pairs = self.r.tables.get("paires_documentees")
        if pairs is not None and not pairs.empty:
            self.add("Paires documentées par le dictionnaire :\n")
            self.add(md_table(pairs))
        self.add(
            "Distinction : `RED_DETERMINISTIC`, `RED_NEAR_DUPLICATE` et `RED_IDENTICAL_COLUMNS` "
            "signalent une **redondance réelle** (information dupliquée) ; "
            "`RED_HIGH_CORRELATION` et `RED_CATEGORICAL_ASSOCIATION` une **association** "
            "statistique, qui ne justifie pas seule une exclusion. Aucune variable n'est "
            "supprimée par l'audit.\n"
        )
        self.figure("10_redondances_documentees", "Redondances documentées")
        self.figure("09_matrice_correlation", "Matrice de corrélation de Spearman")

    def s12_risks(self) -> None:
        self.add("## 12. Risques méthodologiques pour le Machine Learning\n")
        risks = methodological_risks(self.r)
        risks = risks[risks["category"] != Category.REDUNDANCY.value]
        self.add(md_table(risks[["rule_id", "severity", "column", "description"]]))
        classes = self.r.tables.get("repartition_classes")
        if classes is not None:
            self.add("Répartition de la cible :\n")
            self.add(md_table(classes))
        self.figure("11_repartition_classes", "Répartition des classes")
        assoc = self.r.tables.get("association_cible")
        if assoc is not None and not assoc.empty:
            self.add(
                "Association des variables avec la cible (10 plus fortes, usage descriptif) :\n"
            )
            self.add(
                md_table(
                    assoc[["variable", "disponibilite", "mesure", "valeur", "lecture"]], max_rows=10
                )
            )
        self.add(
            "Rappels de protocole : séparation stratifiée 80/20 (graine 42) **après** le "
            "traitement des doublons et **avant** tout traitement appris ; aucun étudiant commun "
            "entre ensembles ni entre plis ; transformations apprises dans des pipelines "
            "ajustés sur l'apprentissage de chaque pli ; les seuils de cet audit ne doivent pas "
            "être réutilisés comme paramètres de prétraitement.\n"
        )

    def s13_recommendations(self) -> None:
        self.add("## 13. Recommandations de nettoyage\n")
        self.add(
            "Synthèse au format attendu par la SAÉ (problème, variables, diagnostic, "
            "conséquences, solution envisagée). Ces propositions sont à **valider et "
            "consigner** dans `docs/decision_log.md` ; l'audit n'en applique aucune.\n"
        )
        subset = self.synthesis[self.synthesis["gravite"] != Severity.INFO.value]
        rows = []
        for row in subset.itertuples(index=False):
            rule = RULES[row.rule_id]
            rows.append(
                (
                    f"{rule.title} (`{row.rule_id}`)",
                    row.variables or rule.columns,
                    f"{row.gravite} · {STATUS_LABELS_FR[DiagnosticStatus(row.diagnostic)]} · "
                    f"{_fmt_int(row.n_signalements)} signalement(s)",
                    rule.potential_impact,
                    rule.suggested_action,
                )
            )
        self.add(
            md_table(
                pd.DataFrame(
                    rows,
                    columns=[
                        "Problème",
                        "Variables",
                        "Diagnostic",
                        "Conséquences potentielles",
                        "Solution envisagée",
                    ],
                )
            )
        )
        self.add(
            "Ordre de traitement suggéré (nettoyage déterministe, sans paramètre appris, "
            "applicable avant la séparation) : (1) doublons exacts ; (2) harmonisation des "
            "modalités et des formats numériques ; (3) recodage des valeurs manquantes "
            "déguisées et des codes sentinelles en valeurs manquantes ; (4) recodage des "
            "valeurs impossibles en valeurs manquantes ; (5) décision sur les incohérences "
            "certaines ; (6) choix des variables redondantes et métadonnées à exclure. "
            "L'imputation, la mise à l'échelle et l'encodage relèvent des pipelines appris.\n"
        )

    def s14_limits(self) -> None:
        self.add("## 14. Limites du système\n")
        self.add(
            "- Les seuils de `niveau_dossier` (120/140/160) et le format d'identifiant sont "
            "**inférés du fichier**, non documentés au dictionnaire.\n"
            "- Plusieurs règles reposent sur des **hypothèses** signalées comme telles "
            "(plage d'âge plausible, validation à 10/20, UE créditées comptées comme validées) "
            "et produisent des anomalies potentielles, jamais des erreurs confirmées.\n"
            "- Une divergence entre deux variables ne dit pas laquelle est fausse ; l'audit "
            "n'arbitre pas.\n"
            "- Les méthodes statistiques signalent la rareté, pas l'erreur ; leurs résultats "
            "dépendent des seuils (configurables) et sont calculés sur l'ensemble du fichier "
            "(usage descriptif).\n"
            "- Les méthodes multivariées dépendent du choix des variables, de la préparation "
            "(imputation médiane, échelle robuste) et du taux de contamination fixé.\n"
            "- Le rapprochement avant/après nettoyage repose sur `id_etudiant` : il est "
            "fragile si les identifiants sont modifiés ou dupliqués.\n"
            "- Les variantes orthographiques non triviales (hors casse, accents, espaces, "
            "synonymes connus) ne sont que suggérées (`FMT_SIMILAR_CATEGORIES`).\n"
        )

    def s15_conclusion(self) -> None:
        c = self.counts
        fired = set(self.synthesis["rule_id"])
        self.add("## 15. Conclusion\n")
        sentences = [
            f"L'audit recense {_fmt_int(c['n_signalements'])} signalements portant sur "
            f"{_fmt_int(c['n_observations_distinctes'])} observations distinctes ; "
            f"{_fmt_int(c['n_observations_critique_ou_elevee'])} observations portent au moins "
            "une anomalie CRITICAL ou HIGH."
        ]
        low = self.synthesis[self.synthesis["gravite"] == Severity.LOW.value]
        if not low.empty:
            sentences.append(
                f"{_fmt_int(int(low['n_signalements'].sum()))} anomalies de représentation "
                "(formats, modalités) relèvent d'un nettoyage déterministe documenté."
            )
        if fired & {"RED_DETERMINISTIC", "RED_NEAR_DUPLICATE", "RED_IDENTICAL_COLUMNS"}:
            sentences.append(
                "Des redondances réelles sont confirmées : une seule version de chaque "
                "information devrait être conservée."
            )
        if "STR_CONSTANT_COLUMN" in fired:
            sentences.append("Les colonnes constantes n'ont aucune valeur prédictive.")
        if "IMB_CLASS_IMBALANCE" in fired:
            sentences.append(
                "Le déséquilibre des classes impose une séparation et des plis stratifiés et une "
                "métrique adaptée."
            )
        sentences.append(
            "Ces constats alimentent les décisions D-005 à D-009 du registre ; aucune "
            "correction n'a été appliquée par l'audit."
        )
        self.add(" ".join(sentences) + "\n")


# ============================================================================== catalogue
def write_rules_catalog(path: Path | str) -> Path:
    """Génère le catalogue Markdown des règles à partir du registre central."""
    path = Path(path)
    frame = rules_frame()
    lines = [
        "# Catalogue des règles d'audit",
        "",
        "> Généré automatiquement depuis `src/data_quality/rules.py` "
        "(`python -m src.data_quality --catalog`). Ne pas modifier à la main : modifier le "
        "registre puis régénérer.",
        "",
        "Gravité : CRITICAL > HIGH > MEDIUM > LOW > INFO. Diagnostic : "
        + ", ".join(f"`{s.value}` ({STATUS_LABELS_FR[s]})" for s in DiagnosticStatus)
        + ". La gravité de certaines règles peut être ajustée au cas par cas "
        "(ex. `STR_TYPE_MISMATCH`, `LEA_TECHNICAL_METADATA`, `IMB_CLASS_IMBALANCE`).",
        "",
    ]
    for detector, block in frame.groupby("detecteur", sort=False):
        lines += [f"## Détecteur `{detector}`", ""]
        for row in block.itertuples(index=False):
            lines += [
                f"### `{row.rule_id}` — {row.titre}",
                "",
                f"- **Gravité** : {row.gravite} · **Diagnostic** : {row.diagnostic} · "
                f"**Catégorie** : {row.categorie}",
                f"- **Variables** : {row.variables}",
                f"- **Justification** : {row.justification}",
                f"- **Méthode** : {row.methode}",
                f"- **Impact ML** : {row.impact_ml}",
                f"- **Action envisagée** : {row.action_envisagee}",
                "",
            ]
    hypotheses = [(v.name, v.hypothesis) for v in VARIABLE_SPECS.values() if v.hypothesis]
    if hypotheses:
        lines += ["## Hypothèses d'audit (absentes du dictionnaire)", ""]
        lines += [f"- `{name}` : {text}" for name, text in hypotheses]
        lines += [
            "- `niveau_dossier` : seuils 120 / 140 / 160 inférés du fichier.",
            "- `id_etudiant` : motif `ET` + 6 chiffres observé dans le fichier.",
            "",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
