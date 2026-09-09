# ruff: noqa: E501
"""Publication renderer: persisted 56.3C source tables only; no model access."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "audits/q1-bounded-complementary-e1-xai/1.0.0"
FAMILIES = ["LR", "RF", "XGB", "LGB"]
COLORS = {"LR": "#215a82", "RF": "#777777", "XGB": "#137d79", "LGB": "#9b4d28"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(n):
    return json.loads((OUT / n).read_text())


def table(n):
    return list(csv.DictReader((OUT / "tables" / n).open()))


def main():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "savefig.facecolor": "white",
        }
    )
    (OUT / "figures").mkdir(exist_ok=True)
    runtime = dict(
        python=sys.version,
        matplotlib=matplotlib.__version__,
        numpy=np.__version__,
        platform=platform.platform(),
        role="Separate rendering environment; frozen XAI environment unchanged",
    )
    (OUT / "figures/runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
    registry = []

    def export(fig, ident, source, caption, interpretation, scale, population, rule):
        outputs = []
        for ext in ["svg", "png"]:
            p = OUT / f"figures/{ident}.{ext}"
            fig.savefig(p, dpi=300, bbox_inches="tight")
            outputs.append(dict(path=str(p.relative_to(OUT)), sha256=sha(p)))
        registry.append(
            dict(
                figure_id=ident,
                source_data_path="tables/" + source,
                source_data_digest=sha(OUT / "tables" / source),
                generation_script="src/evaluation/q1_bounded_complementary_e1_figures.py",
                generation_script_digest=sha(__file__),
                runtime="figures/runtime.json",
                filters="ActiveMQ TEXT only; RF attribution unavailable",
                sort_order=rule,
                top_k_rule=rule,
                caption=caption,
                interpretation=interpretation,
                model=FAMILIES,
                population=population,
                scale=scale,
                outputs=outputs,
            )
        )
        plt.close(fig)

    data = table("E1-2_top20.csv")
    fig, axes = plt.subplots(2, 2, figsize=(13, 11), layout="constrained")
    for f, ax in zip(FAMILIES, axes.flat, strict=True):
        rr = [r for r in data if r["family"] == f]
        if not rr:
            ax.axis("off")
            ax.text(
                0.5,
                0.6,
                "RF — attribution unavailable",
                ha="center",
                fontsize=15,
                weight="bold",
                transform=ax.transAxes,
            )
            ax.text(
                0.5,
                0.43,
                "Exact TreeSHAP failed additivity.\nNo feature ranking is reported.",
                ha="center",
                linespacing=1.7,
                transform=ax.transAxes,
                color="#555555",
            )
            continue
        rr = rr[::-1]
        ax.barh(
            [r["token"] for r in rr],
            [float(r["mean_absolute_attribution"]) for r in rr],
            color=COLORS[f],
        )
        ax.tick_params(axis="y", labelsize=9)
        ax.set_title(f + " · " + rr[0]["scale"], loc="left", weight="bold")
        ax.set_xlabel("Mean absolute contribution")
        ax.grid(axis="x", alpha=0.15)
        ax.set_axisbelow(True)
    fig.suptitle("ActiveMQ TEXT · top 20 features by model", fontsize=17, weight="bold")
    export(
        fig,
        "E1-F1",
        "E1-2_top20.csv",
        "Mean absolute feature contributions over all 245 frozen ActiveMQ T1 rows. LR uses centered analytical logit decomposition; XGB and LGB use exact TreeSHAP on native raw margins. RF failed exact additivity and is excluded. Horizontal scales are independent.",
        "Feature rankings vary across the three reportable families. Magnitudes are not pooled across output scales.",
        "Family-specific",
        "245 T1 rows",
        "Top 20 descending mean absolute contribution; lexical token ties",
    )
    cross = table("E1-4_consistency.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), layout="constrained")
    for k, ax in zip([3, 10], axes, strict=True):
        mat = np.full((4, 4), np.nan)
        for i, f in enumerate(FAMILIES):
            if f != "RF":
                mat[i, i] = 1
        for r in cross:
            if int(r["k"]) == k:
                i = FAMILIES.index(r["family_a"])
                j = FAMILIES.index(r["family_b"])
                mat[i, j] = mat[j, i] = float(r["jaccard"])
        cmap = plt.get_cmap("YlGnBu").copy()
        cmap.set_bad("#eeeeee")
        im = ax.imshow(mat, vmin=0, vmax=1, cmap=cmap)
        for i in range(4):
            for j in range(4):
                ax.text(
                    j,
                    i,
                    "N/A" if np.isnan(mat[i, j]) else f"{mat[i, j]:.2f}",
                    ha="center",
                    va="center",
                    color="white" if mat[i, j] > 0.7 else "#222222",
                )
        ax.set_xticks(range(4), FAMILIES)
        ax.set_yticks(range(4), FAMILIES)
        ax.set_title(f"Top {k} · Jaccard overlap", weight="bold")
    fig.colorbar(im, ax=axes, label="Intersection / union", shrink=0.8)
    export(
        fig,
        "E1-F2",
        "E1-4_consistency.csv",
        "Pairwise Jaccard overlap of top-3 and top-10 feature sets. RF cells are unavailable. The frozen overlap threshold is 0.60; full consistency additionally requires rank correlation ≥0.70 and sign agreement ≥0.80.",
        "No reportable pair meets all frozen consistency criteria. Diagonal self-overlap is not cross-model evidence.",
        "Rank/set comparison",
        "245 T1 rows",
        "Fixed model order LR, RF, XGB, LGB; k=3,10",
    )
    local = table("figure_local_source.csv")
    fig, ax = plt.subplots(figsize=(9, 6), layout="constrained")
    vals = [float(r["attribution"]) for r in local][::-1]
    labels = [r["token"] for r in local][::-1]
    ax.barh(labels, vals, color=["#a34c32" if v > 0 else "#246282" for v in vals])
    ax.axvline(0, color="#333333", lw=0.8)
    ax.set_xlabel("Centered contribution to LR logit")
    ax.set_title(
        "ActiveMQ TEXT · frozen local case 1 · LR", loc="left", weight="bold", pad=32
    )
    ax.text(
        0,
        1.02,
        "Commit "
        + local[0]["commit_identity"][:12]
        + f" · base {float(local[0]['base_value']):.4f} · output {float(local[0]['model_output']):.4f}",
        transform=ax.transAxes,
        fontsize=9,
    )
    export(
        fig,
        "E1-F3",
        "figure_local_source.csv",
        "First identity-selected local case, shown with LR (fixed family order). Twelve largest absolute centered logit contributions and the signed sum of all remaining features are displayed. Positive and negative contributions increase and decrease the model logit relative to the TRAIN reference.",
        "The display preserves contribution to absent TF-IDF tokens and groups omitted features without discarding their net contribution. This is an association with the predictor output, not a causal explanation.",
        "LR logit",
        "First of 8 frozen local identities",
        "12 descending absolute contributions plus signed sum of all other features",
    )
    arch = table("E1-5_hierarchy.csv")
    fig, ax = plt.subplots(figsize=(12, 5), layout="constrained")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.axis("off")
    labels = [
        "TEXT features\nTF-IDF",
        "TEXT unimodal\npredictor",
        "TEXT output\nprobability",
        "Late-fusion\npredictor",
        "Multimodal\nprediction",
    ]
    for i, label in enumerate(labels):
        x = 0.15 + i * 2.4
        ax.add_patch(
            FancyBboxPatch(
                (x, 2.25),
                2.05,
                1,
                boxstyle="round,pad=0.06",
                facecolor="#eaf2f7" if i < 3 else "#e8f3ee",
                edgecolor="#536b78",
            )
        )
        ax.text(x + 1.025, 2.75, label, ha="center", va="center", fontsize=11)
        if i < 4:
            ax.add_patch(
                FancyArrowPatch(
                    (x + 2.12, 2.75),
                    (x + 2.32, 2.75),
                    arrowstyle="-|>",
                    mutation_scale=13,
                    color="#465c68",
                )
            )
    ax.text(
        2.5,
        4.15,
        "E1 · complementary",
        ha="center",
        fontsize=16,
        weight="bold",
        color="#215a82",
    )
    ax.text(
        8.7,
        4.15,
        "E2 · primary multimodal XAI",
        ha="center",
        fontsize=16,
        weight="bold",
        color="#137d79",
    )
    ax.text(2.5, 3.65, arch[0]["question"], ha="center", fontsize=10)
    ax.text(8.7, 3.65, arch[1]["question"], ha="center", fontsize=10)
    ax.text(
        6,
        1.4,
        "CODE and PROCESS join TEXT at the frozen late-fusion level",
        ha="center",
        fontsize=11,
    )
    ax.text(
        6,
        0.75,
        "Architectural and interpretive continuity · no algebraic propagation of E1 values into E2",
        ha="center",
        fontsize=10,
        color="#555555",
    )
    export(
        fig,
        "E1-F4",
        "E1-5_hierarchy.csv",
        "Hierarchical explainability architecture. Bounded E1 provides within-modality evidence for ActiveMQ TEXT, while E2 explains between-modality late fusion. Arrows show architectural continuity, not an additive mapping of feature attributions into fusion attributions.",
        "E2 remains the primary multimodal contribution. This diagram does not assert a newly verified same-row probability bridge.",
        "Conceptual architecture",
        "ActiveMQ TEXT E1; inherited E2",
        "Fixed architectural order; no numerical data",
    )
    (OUT / "e1_figure_registry.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in registry)
    )
    (OUT / "figures/captions.md").write_text(
        "\n\n".join("**" + r["figure_id"] + "** " + r["caption"] for r in registry)
        + "\n"
    )


if __name__ == "__main__":
    main()
