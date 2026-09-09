# ruff: noqa: E501
"""56.3C bounded ActiveMQ TEXT execution; no labels, fitting or reserve access.

Run with the frozen .venv-xai-s56 runtime. Outputs are staged and hashed before
interpretation. A failed gate terminates execution; no recovery campaign exists.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "audits/q1-bounded-complementary-e1-xai/1.0.0"
BRANCH = "sprint-10/q1-bounded-complementary-e1-xai"
HEAD = "4220e31de426e3defe5392cf6f8ae40e9fb2b022"
PROJECT = "apache/activemq"
FAMILIES = {
    "LR": "Logistic Regression",
    "RF": "Random Forest",
    "XGB": "XGBoost",
    "LGB": "LightGBM",
}
SCALES = {
    "LR": "LOGIT",
    "RF": "POSITIVE_CLASS_OUTPUT",
    "XGB": "RAW_MARGIN",
    "LGB": "RAW_MARGIN",
}
SEEDS = list(range(20260901, 20260921))
R4 = ROOT / "audits/q1-e1-prospective-train-representations/1.0.0"
TRAIN = R4 / "representations/apache_activemq/TEXT"
R3 = ROOT / "audits/q1-e1-prospective-reconstructed-representation-protocol/1.0.0"
R4B = ROOT / "audits/q1-e1-canonical-apachejit-train-reentry/1.0.0"
RUNTIME = ROOT / "audits/q1-xai-runtime-freeze/1.0.0"
STORE = ROOT / "audits/q1-xai-reconstruction-execution/1.0.0"
E2 = ROOT / "audits/q1-primary-xai-e1-input-e2-reference-resolution/1.0.0"
FREEZE = ROOT / "audits/q1-apachejit-final-dataset-freeze/1.0.0"
C54 = ROOT / "audits/q1-t1-confirmatory-execution/1.0.0/block8_final_closure/1.0.0"
DENIED = [
    "T1_LABEL_ACCESS",
    "T2_ACCESS",
    "SOURCE_RECOVERY_REOPEN",
    "CODE_RECOVERY_REOPEN",
    "PROCESS_RECOVERY_REOPEN",
    "RETRAIN",
    "REFIT",
    "RECALIBRATION",
    "HYPERPARAMETER_TUNING",
    "MODEL_SELECTION",
    "PREDICTIVE_METRIC_RECOMPUTATION",
    "E2_RECOMPUTATION",
    "E2_MUTATION",
    "APPROXIMATE_SHAP",
    "KERNELSHAP",
    "LIME",
    "COMMIT",
    "PUSH",
    "PR",
]
ZERO = [
    "T1_LABEL_ACCESS_COUNT",
    "T2_ACCESS_COUNT",
    "T2_IDENTITY_READ_COUNT",
    "T2_FEATURE_READ_COUNT",
    "T2_LABEL_READ_COUNT",
    "T2_MODEL_QUERY_COUNT",
    "RETRAIN_COUNT",
    "REFIT_COUNT",
    "RECALIBRATION_COUNT",
    "HYPERPARAMETER_TUNING_COUNT",
    "MODEL_SELECTION_COUNT",
    "PREDICTIVE_METRIC_RECOMPUTATION_COUNT",
    "E2_RECOMPUTATION_COUNT",
    "E2_MUTATION_COUNT",
]
COUNTERS = {
    k: 0
    for k in ZERO
    + [
        "T1_METADATA_ACCESS_COUNT",
        "T1_IDENTITY_ACCESS_COUNT",
        "T1_FEATURE_VALUE_ACCESS_COUNT",
        "T1_MODEL_QUERY_COUNT",
        "MODEL_LOAD_COUNT",
        "MODEL_QUERY_COUNT",
        "SHAP_EXECUTION_COUNT",
        "ANALYTICAL_ATTRIBUTION_EXECUTION_COUNT",
        "E1_ATTRIBUTION_COUNT",
        "FIGURE_GENERATION_COUNT",
    ]
}
COUNTERS["T1_PREDICTIVE_HISTORICAL_EXECUTION"] = "1/1"
LIMITATIONS = [
    "E1 bounded to ActiveMQ TEXT and a single project.",
    "No CODE/PROCESS feature attribution.",
    "E1 complements the primary E2 multimodal explanation.",
    "Representations are RECONSTRUCTED, not original Sprint 54 matrices.",
    "Predictors remain RECONSTRUCTED despite prior functional equivalence.",
    "TF-IDF contributions are model associations, not causal effects.",
    "Cross-model heterogeneity limits a universal feature narrative.",
    "E1 does not mathematically propagate into E2.",
    "No generalization beyond this bounded explanatory case study.",
    "Stability concerns fixed populations, not sampling or reference robustness.",
    "Raw attribution magnitudes have different output scales across families.",
    "E1/E2 continuity is architectural unless exact same-row probability linkage is independently established.",
]


def enc(x):
    return (
        json.dumps(
            x, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode()


def sha_bytes(x):
    return hashlib.sha256(x).hexdigest()


def sha(p):
    return sha_bytes(Path(p).read_bytes())


def read(p):
    return json.loads(Path(p).read_text())


def rows(p):
    return [
        json.loads(line) for line in Path(p).read_text().splitlines() if line.strip()
    ]


def save(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(enc(value))


def ledger(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"".join(enc(v) for v in value))


def rel(p):
    return str(Path(p).relative_to(ROOT))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def authorize(project, modality, family, partition="T1", labels=False):
    if (
        project != PROJECT
        or modality != "TEXT"
        or family not in FAMILIES
        or partition not in ("TRAIN", "T1")
        or labels
    ):
        raise PermissionError(
            "Only label-free ActiveMQ TEXT TRAIN/T1 and four frozen families admitted"
        )


def branch_gate(branch, head):
    require(branch == BRANCH and head == HEAD, "Branch/base mismatch: STOP")


def verify_manifest(base, name="MANIFEST.sha256"):
    base = Path(base)
    entries = {}
    for line in (base / name).read_text().splitlines():
        h, n = line.split("  ", 1)
        p = base / n
        require(
            not Path(n).is_absolute()
            and ".." not in Path(n).parts
            and n not in entries
            and not p.is_symlink(),
            "Unsafe manifest",
        )
        require(sha(p) == h, "Manifest mismatch: " + str(p))
        entries[n] = h
    return entries


def manifest():
    entries = {
        str(p.relative_to(OUT)): sha(p)
        for p in sorted(OUT.rglob("*"))
        if p.is_file() and p != OUT / "MANIFEST.sha256"
    }
    (OUT / "MANIFEST.sha256").write_text(
        "".join(f"{h}  {n}\n" for n, h in entries.items())
    )
    require(verify_manifest(OUT) == entries, "Output manifest failure")
    return len(entries)


def parent_snapshot():
    # Only TRAIN/protocol namespaces and explicit label-free E2 metadata. Never
    # hash a mixed source container or historical labelled T1 prediction file.
    files = [p for base in [R3, R4, R4B] for p in base.rglob("*") if p.is_file()]
    files += [
        p
        for p in E2.iterdir()
        if p.is_file() and (p.name.startswith("e2_") or p.name == "MANIFEST.sha256")
    ]
    files += [
        C54 / n
        for n in [
            "sprint54_final_scientific_state.json",
            "sprint54_integrity_closure.json",
            "MANIFEST.sha256",
        ]
    ]
    return {rel(p): sha(p) for p in sorted(files)}


def sample(records, purpose, cap, representation):
    require(0 < cap <= (8 if purpose == "local" else 256), "Population cap")

    def key(r):
        v = dict(
            seed=SEEDS[0],
            purpose=purpose,
            project=PROJECT,
            representation_identity=representation,
            row_identifier=r["row_identifier"],
        )
        return sha_bytes(
            json.dumps(
                v, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode()
        ), r["row_identifier"]

    require(
        len({r["row_identifier"] for r in records}) == len(records),
        "Duplicate population identity",
    )
    return [{**r, "selection_key": key(r)[0]} for r in sorted(records, key=key)[:cap]]


def preflight():
    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, text=True
    ).strip()
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    branch_gate(branch, head)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", "a438dee", head], cwd=ROOT, check=True
    )
    require(not OUT.exists(), "Existing execution namespace: no automatic rerun")
    OUT.mkdir(parents=True)
    save(
        "preflight.json",
        dict(
            branch=branch,
            head=head,
            parent_merge="PR #121",
            status=subprocess.check_output(
                ["git", "status", "--short"], cwd=ROOT, text=True
            ),
            log=subprocess.check_output(
                ["git", "log", "-5", "--oneline", "--decorate"], cwd=ROOT, text=True
            ),
        ),
    )
    route = read(R4B / "protocol_summary.json")
    require(
        route["source_recovery_closed"]
        and route["article_route"]
        == "ARTICLE_ROUTE_C_E2_PRIMARY_PLUS_BOUNDED_COMPLEMENTARY_E1",
        "R4B route not closed",
    )
    s54 = read(C54 / "sprint54_integrity_closure.json")
    require(
        s54["status"] == "PASS_SPRINT54_INTEGRITY_CLOSED"
        and s54["predictive_scoring_count"] == 1
        and s54["t2_state"] == "DENY_SEALED_REVIEWER_RESERVE",
        "Sprint54 state mismatch",
    )
    require(
        read(R4 / "parent_r3_verification.json")["verified"], "R3 acceptance missing"
    )
    for p in [R3, R4B]:
        verify_manifest(p)
    before = parent_snapshot()
    save("parent_integrity_before.json", before)
    save(
        "e2_parent_integrity_before.json",
        {p: h for p, h in before.items() if p.startswith(rel(E2))},
    )
    save(
        "parent_scientific_state_verification.json",
        dict(
            status="PASS",
            sprint54=s54,
            r3=read(R3 / "protocol_summary.json"),
            r4=read(R4 / "protocol_summary.json"),
            r4b=route,
            sprint55_methods=read(RUNTIME / "explainer_contract.json"),
            e2=read(
                ROOT
                / "audits/q1-primary-xai-alternative-design/1.0.0/e2_integrity_preservation.json"
            ),
            no_original_predictor_claim=True,
        ),
    )
    save(
        "non_iteration_contract.json",
        {
            **{k: "DENY" for k in DENIED},
            "maximum_bounded_repair_attempts": 1,
            "automatic_followup_sprints": False,
        },
    )
    save(
        "bounded_t1_feature_access_authorization.json",
        dict(
            project=PROJECT,
            modality="TEXT",
            partitions=["TRAIN", "T1"],
            T1_LABEL_ACCESS="DENY",
            T2="DENY_SEALED_REVIEWER_RESERVE",
            authority="User Sprint 56.3C sections 7 and 10",
            frozen_transform_only=True,
        ),
    )
    save(
        "bounded_e1_scope_registry.json",
        dict(
            projects=[PROJECT],
            modalities=["TEXT"],
            families=FAMILIES,
            no_performance_selection=True,
            model_state="RECONSTRUCTED",
        ),
    )
    save(
        "xai_claim_hierarchy.json",
        dict(
            E2_ROLE="PRIMARY_MULTIMODAL_XAI",
            E1_ROLE="BOUNDED_COMPLEMENTARY_FEATURE_LEVEL_XAI",
        ),
    )
    save(
        "e1_e2_continuity_contract.json",
        dict(
            chain=[
                "TEXT features",
                "TEXT unimodal predictor",
                "TEXT probability",
                "frozen E2 modality input",
                "frozen late fusion",
                "multimodal prediction",
            ],
            connection=["ARCHITECTURAL", "TRACEABLE", "INTERPRETIVE"],
            algebraic_propagation="DENY",
            same_row_empirical_claim="REQUIRES_SEPARATE_PROOF",
        ),
    )
    save(
        "e1_output_scale_registry.json",
        dict(
            scales=SCALES, cross_family_magnitude_comparison="Not directly comparable"
        ),
    )
    save(
        "e1_method_registry.json",
        dict(
            LR="EXACT_CENTERED_ANALYTICAL_LOGIT_DECOMPOSITION",
            RF="EXACT_TREESHAP_POSITIVE_CLASS",
            XGB="EXACT_TREESHAP_RAW_MARGIN",
            LGB="EXACT_TREESHAP_RAW_MARGIN",
            approximate=False,
            feature_perturbation="tree_path_dependent",
            data=None,
            background_role="LR centered reference; tree diagnostics only",
            tolerances=read(RUNTIME / "xai_fidelity_contract.json"),
            stability=read(RUNTIME / "xai_stability_contract.json"),
            comparisons=dict(k=[3, 10], jaccard=0.60, spearman=0.70, sign=0.80),
            selection_amendment="56.3C identity-only shared populations; no label stratification or new risk strata",
        ),
    )
    save(
        "e1_research_questions.json",
        {
            "RQ-E1.1": "Which TEXT features most strongly influence ActiveMQ unimodal predictions?",
            "RQ-E1.2": "Are explanations faithful to the frozen reconstructed predictors?",
            "RQ-E1.3": "Are explanations stable under the frozen protocol?",
            "RQ-E1.4": "How consistent are explanations across LR, RF, XGB and LGB?",
            "RQ-E1.5": "How does bounded E1 complement primary E2?",
        },
    )
    save("e1_limitations.json", LIMITATIONS)
    save(
        "prohibited_claims.json",
        [
            "All modalities explained at feature level",
            "E1 represents all ApacheJIT projects",
            "ActiveMQ generalizes to ApacheJIT",
            "SHAP proves causality",
            "TEXT tokens cause defects",
            "E1 mathematically decomposes E2",
            "Reconstructed representations or predictors are ORIGINAL",
            "All algorithms rely on the same features",
            "Feature-level XAI validates predictive accuracy",
        ],
    )
    return before


def bounded_serialization_repair():
    global TRAIN
    target = OUT / "representations/train_verified_copy"
    require(not target.exists(), "Only one bounded repair permitted")
    target.mkdir(parents=True)
    changes = []
    for line in (TRAIN / "MANIFEST.sha256").read_text().splitlines():
        h, n = line.split("  ", 1)
        b = (TRAIN / n).read_bytes()
        if sha_bytes(b) != h:
            require(
                n.endswith((".json", ".jsonl")) and sha_bytes(b + b"\n") == h,
                "Not an exact terminal-LF repair: STOP",
            )
            changes.append(
                dict(
                    file=n,
                    before=sha_bytes(b),
                    after=h,
                    operation="append exactly one terminal LF in child copy",
                )
            )
            b += b"\n"
        (target / n).write_bytes(b)
    (target / "MANIFEST.sha256").write_bytes((TRAIN / "MANIFEST.sha256").read_bytes())
    save(
        "bounded_repair_attempt.json",
        dict(
            attempt=1,
            blocker="Five inherited text files lack one terminal LF required by representation manifest",
            changes=changes,
            parent_modified=False,
            scientific_content_changed=False,
        ),
    )
    TRAIN = target


def train_integrity():
    import numpy as np
    from scipy.sparse import csr_matrix

    from src.evaluation import (
        q1_e1_prospective_train_representation_reconstruction as r4,
    )

    r4.verify_persistence(TRAIN)
    shape = read(TRAIN / "csr_shape.json")["shape"]
    x = csr_matrix(
        (
            np.fromfile(TRAIN / "csr_data.f64", dtype="<f8"),
            np.fromfile(TRAIN / "csr_indices.u64", dtype="<u8").astype("int64"),
            np.fromfile(TRAIN / "csr_indptr.u64", dtype="<u8").astype("int64"),
        ),
        shape=shape,
    )
    state = read(TRAIN / "transform_state.json")
    rr = rows(TRAIN / "row_registry.jsonl")
    evidence = r4.integrity(x, [r["train_row_id"] for r in rr], state["feature_order"])
    require(
        sha_bytes(r4.matrix_objects(x)["matrix.bin"])
        == read(TRAIN / "digests.json")["matrix_digest"],
        "CSR and canonical matrix mismatch",
    )
    save(
        "text_train_representation_integrity.json",
        {
            **evidence,
            "digests": read(TRAIN / "digests.json"),
            "manifest": sha(TRAIN / "MANIFEST.sha256"),
            "read_only": True,
        },
    )
    return x, state, [{**r, "row_identifier": r["train_row_id"]} for r in rr]


def materialize(state):
    import base64

    import numpy as np
    from scipy.sparse import save_npz

    from src.evaluation import (
        q1_e1_prospective_train_representation_reconstruction as r4,
    )

    spec = read(
        ROOT
        / "audits/q1-primary-xai-t2-semantic-boundary-amendment/1.0.0/frozen_partition_function_spec.json"
    )["projects"][0]
    require(
        spec["project"] == PROJECT
        and [
            spec[k]
            for k in [
                "TRAIN_end_exclusive",
                "VALIDATION_end_exclusive",
                "T1_end_exclusive",
            ]
        ]
        == [3675, 4900, 5145],
        "Frozen ordinal boundary mismatch",
    )
    # Byte-at-a-time decompression with max_length=1 stops exactly at the last
    # authorized LF; neither gzip buffering nor full-container hashing is used.
    # A compressed byte can contain shared deflate bits; no T2 decoded byte is
    # requested or returned. Pre-T1 label-free prefix traversal is explicit.
    save(
        "representations/source_admission_before_payload.json",
        dict(
            producer="src/dataset/apachejit_final_dataset_freeze.py:817-839",
            boundary=spec,
            paths=["temporal_partition_manifest.jsonl.gz", "text_dataset.jsonl.gz"],
            fields_contain_labels=False,
            max_decoded_lines=5145,
            read_unit_bytes=1,
            decode_limit_bytes=1,
            compressed_safety_ceiling=2_000_000,
            pre_t1_prefix="TRAIN and VALIDATION label-free transport traversal; not XAI populations",
            no_tail_scan=True,
        ),
    )
    output = {}
    for name in ["temporal_partition_manifest.jsonl.gz", "text_dataset.jsonl.gz"]:
        raw, consumed = r4.bounded_prefix(FREEZE / name, 5145, 2_000_000)
        rr = [json.loads(line) for line in raw.splitlines()]
        output[name] = rr
        save(
            "representations/" + name + ".access.json",
            dict(
                compressed_bytes_read=consumed,
                decompressed_lines=5145,
                prefix_sha256=sha_bytes(raw),
                t1_rows=245,
                pre_t1_rows=4900,
                T2_decoded_bytes=0,
            ),
        )
    ids = output["temporal_partition_manifest.jsonl.gz"]
    require(
        all(
            r["project"] == PROJECT
            and r["partition"]
            == ("TRAIN" if i < 3675 else "VALIDATION" if i < 4900 else "T1")
            for i, r in enumerate(ids)
        ),
        "Partition routing mismatch",
    )
    require(
        sha_bytes(enc([r["row_identifier"] for r in ids[4900:]]))
        == spec["historical_T1_membership_digest"],
        "T1 historical membership mismatch",
    )
    msgs = output["text_dataset.jsonl.gz"]
    require(
        [r["row_identifier"] for r in msgs] == [r["row_identifier"] for r in ids],
        "TEXT identity/order mismatch",
    )
    selected = []
    for r in msgs[4900:]:
        require(
            set(r)
            == {
                "row_identifier",
                "raw_commit_message",
                "raw_commit_message_bytes_base64",
                "raw_commit_message_sha256",
            },
            "Unexpected TEXT schema",
        )
        b = base64.b64decode(r["raw_commit_message_bytes_base64"], validate=True)
        require(
            sha_bytes(b) == r["raw_commit_message_sha256"]
            and b.decode("utf-8") == r["raw_commit_message"],
            "Message integrity mismatch",
        )
        selected.append(r["raw_commit_message"])
    rr = [
        dict(
            row_index=i,
            row_identifier=r["row_identifier"],
            commit_identity=r["order_key"][1],
            order_key=r["order_key"],
            project=PROJECT,
            partition="T1",
        )
        for i, r in enumerate(ids[4900:])
    ]
    COUNTERS["T1_METADATA_ACCESS_COUNT"] += 1
    COUNTERS["T1_IDENTITY_ACCESS_COUNT"] += len(rr)
    COUNTERS["T1_FEATURE_VALUE_ACCESS_COUNT"] += len(rr)
    ledger("representations/t1_row_registry.jsonl", rr)
    ledger("representations/t1_raw_message_registry.jsonl", msgs[4900:])
    before = sha_bytes(enc(state))
    x = r4.transform_text(selected, state)
    replay = r4.transform_text(selected, state)
    require(before == sha_bytes(enc(state)), "Vectorizer state changed")
    exact = (
        x.shape == replay.shape
        and x.dtype == replay.dtype
        and all(
            np.array_equal(getattr(x, k), getattr(replay, k))
            for k in ["indices", "indptr", "data"]
        )
    )
    require(exact, "T1 repeatability failure")
    save_npz(OUT / "representations/t1_text.npz", x)
    for n, b in r4.matrix_objects(x).items():
        (OUT / "representations" / n).write_bytes(b)
    d = dict(
        matrix=sha(OUT / "representations/matrix.bin"),
        row_order=sha_bytes(enc([r["row_identifier"] for r in rr])),
        feature_order=sha_bytes(enc(state["feature_order"])),
        transform=sha(TRAIN / "transform_state.json"),
        source=sha(OUT / "representations/t1_raw_message_registry.jsonl"),
    )
    save(
        "t1_text_representation_registry.json",
        dict(
            status="RECONSTRUCTED_T1_TEXT_REPRESENTATION",
            shape=list(x.shape),
            dtype=str(x.dtype),
            digests=d,
            column_registry=rel(TRAIN / "column_registry.jsonl"),
            vectorizer_reference=rel(TRAIN / "transform_state.json"),
            runtime="e1_xai_runtime.json",
            historical_original=False,
        ),
    )
    save(
        "t1_text_representation_repeatability.json",
        dict(
            status="EXACT_REPEATABILITY",
            replays=1,
            shape=list(x.shape),
            dtype=str(x.dtype),
            CSR_indices=True,
            CSR_indptr=True,
            values=True,
            row_order=True,
            column_order=True,
            digests=d,
            vocabulary_unchanged=True,
            idf_unchanged=True,
            refit=False,
        ),
    )
    return x, rr


def freeze_runtime():
    import numpy as np
    from threadpoolctl import threadpool_info

    packages = {
        p: importlib.metadata.version(p)
        for p in [
            "numpy",
            "scipy",
            "scikit-learn",
            "shap",
            "numba",
            "xgboost",
            "lightgbm",
        ]
    }
    save(
        "e1_xai_runtime.json",
        dict(
            python=sys.version,
            packages=packages,
            platform=platform.platform(),
            architecture=platform.machine(),
            CPU=platform.processor(),
            threads={
                k: os.environ.get(k)
                for k in [
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS",
                ]
            },
            blas=threadpool_info(),
            seed=SEEDS[0],
            stability_seeds=SEEDS,
            determinism="single thread; exact algorithms; fixed populations; no upgrades after generation",
            numpy=np.__version__,
        ),
    )


def prepare(resume=False):
    before = read(OUT / "parent_integrity_before.json") if resume else preflight()
    if resume:
        bounded_serialization_repair()
    train, state, tr = train_integrity()
    freeze_runtime()
    t1, rr = materialize(state)
    identity = (
        read(TRAIN / "digests.json")["transform_digest"]
        + ":"
        + read(TRAIN / "digests.json")["column_order_digest"]
    )
    bg = sample(tr, "background", 256, identity)
    fg = sample(rr, "foreground", 256, identity)
    local = sample(fg, "local", 8, identity)
    for n, r in [
        ("train_background", bg),
        ("t1_global_foreground", fg),
        ("local_case", local),
    ]:
        ledger("e1_" + n + "_population.jsonl", r)
    save(
        "populations/freeze.json",
        dict(
            before_attribution=True,
            background=len(bg),
            foreground=len(fg),
            local=len(local),
            source_T1=len(rr),
            source_TRAIN=len(tr),
            labels_used=False,
            identity=identity,
            seed=SEEDS[0],
        ),
    )
    save("governance_counters.json", COUNTERS)
    manifest()
    return before, train, state, t1, bg, fg, local


def alignment(family, pipe, record, state, g4):
    import numpy as np

    authorize(PROJECT, "TEXT", family)
    vector = pipe.named_steps["tfidf"]
    model = pipe.named_steps["model"]
    require(
        vector.get_feature_names_out().tolist() == state["feature_order"],
        "Feature order mismatch",
    )
    require(
        vector.vocabulary_ == state["vocabulary"]
        and np.array_equal(vector.idf_, state["idf"]),
        "Vectorizer mismatch",
    )
    for k, v in state["parameters"].items():
        require(
            vector.get_params()[k] == (tuple(v) if k == "ngram_range" else v),
            "Preprocessing mismatch: " + k,
        )
    require(
        model.n_features_in_ == 2557 and model.classes_.tolist() == [0, 1],
        "Feature count / class semantics mismatch",
    )
    require(
        g4["G4_outcome"] == "G4_PASS_ROW_LEVEL_RAW_EQUIVALENCE",
        "Prior equivalence required",
    )
    require(
        g4["model_identity_sha256"]
        in record["canonical_state"]["provenance"]["consuming_model_identity_sha256"],
        "Model identity lineage mismatch",
    )
    require(
        record["text_representation"]["sha256"]
        == read(TRAIN / "digests.json")["transform_digest"],
        "Frozen vectorizer identity mismatch",
    )
    return dict(
        family=family,
        project=PROJECT,
        modality="TEXT",
        status="ALIGNMENT_PASS_WITH_PREDECLARED_LIMITATION",
        model_state="RECONSTRUCTED",
        model_identity=g4["model_identity_sha256"],
        model_digest=record["executable"]["sha256"],
        feature_count=2557,
        feature_order_digest=read(TRAIN / "digests.json")["column_order_digest"],
        vectorizer_digest=record["text_representation"]["sha256"],
        preprocessing="EXACT_PERSISTED_VOCABULARY_IDF_PARAMETERS",
        classes=[0, 1],
        scale=SCALES[family],
        prior_equivalence=g4["G4_outcome"],
        limitation="Prospective representation; no original historical matrix-byte claim",
    )


def fidelity(phi, base, output, tol):
    import numpy as np

    residual = np.abs(base + phi.sum(axis=1) - output)
    require(
        np.isfinite(phi).all() and np.isfinite(residual).all(), "Nonfinite attribution"
    )
    failures = int(np.sum(residual > tol * (1 + np.abs(output))))
    return dict(
        status="FIDELITY_PASS" if failures == 0 else "FIDELITY_FAIL",
        n_evaluated=len(output),
        max_residual=float(residual.max()),
        mean_residual=float(residual.mean()),
        median_residual=float(np.median(residual)),
        p95_residual=float(np.quantile(residual, 0.95)),
        failures=failures,
        tolerance=f"{tol} * (1 + abs(model_output))",
    ), residual


def ranking(phi, names):
    import numpy as np

    mean = np.abs(phi).mean(axis=0)
    return sorted(range(len(names)), key=lambda j: (-mean[j], names[j]))


def consistency(a, b, names, k):
    import numpy as np
    from scipy.stats import spearmanr

    aa = np.abs(a).mean(axis=0)
    bb = np.abs(b).mean(axis=0)
    ra = ranking(a, names)[:k]
    rb = ranking(b, names)[:k]
    shared = sorted(set(ra) & set(rb))
    union = sorted(set(ra) | set(rb))
    rho = (
        float(spearmanr(aa[union], bb[union]).statistic)
        if len(union) > 1 and np.ptp(aa[union]) and np.ptp(bb[union])
        else None
    )

    def signed(x):
        return np.where(np.abs(x) <= 1e-12, 0, np.sign(x))

    sign = (
        float(np.mean(signed(a.mean(axis=0)[shared]) == signed(b.mean(axis=0)[shared])))
        if shared
        else None
    )
    row_sign = (
        float(np.mean(signed(a[:, shared]) == signed(b[:, shared]))) if shared else None
    )
    return dict(
        k=k,
        jaccard=len(shared) / len(union),
        spearman_union=rho,
        signed_mean_agreement_shared=sign,
        row_feature_sign_agreement_shared=row_sign,
        shared=[names[j] for j in shared],
        union_count=len(union),
        spearman_support="union of top-k; average tied ranks; native-scale magnitudes ranked within family",
        sign_zero_band=1e-12,
    )


def execute():
    require(
        not (OUT / "protocol_summary.json").exists(), "Closed execution cannot be rerun"
    )
    global TRAIN
    import itertools

    import joblib
    import numpy as np
    import shap
    from scipy.sparse import load_npz
    from scipy.special import expit
    from threadpoolctl import threadpool_limits

    verify_manifest(OUT)
    branch_gate(
        subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip(),
        subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    )
    COUNTERS.update(read(OUT / "governance_counters.json"))
    TRAIN = OUT / "representations/train_verified_copy"
    train, state, _ = train_integrity()
    t1 = load_npz(OUT / "representations/t1_text.npz")
    fg = rows(OUT / "e1_t1_global_foreground_population.jsonl")
    bg = rows(OUT / "e1_train_background_population.jsonl")
    local = rows(OUT / "e1_local_case_population.jsonl")
    require(
        read(OUT / "populations/freeze.json")["before_attribution"],
        "Populations not frozen",
    )
    x = t1[[r["row_index"] for r in fg]]
    COUNTERS["T1_IDENTITY_ACCESS_COUNT"] += len(fg) + len(local)
    COUNTERS["T1_FEATURE_VALUE_ACCESS_COUNT"] += t1.shape[0]
    mu = np.asarray(train[[r["row_index"] for r in bg]].mean(axis=0)).ravel()
    names = state["feature_order"]
    journal = {
        r["logical_id"]: r
        for r in rows(STORE / "repetitions/rep_01/component_journal.jsonl")
    }
    g4 = {
        r["algorithm"]: r
        for r in rows(
            ROOT
            / "audits/q1-xai-reconstruction-equivalence-g4/1.0.0/g4_scope_results.jsonl"
        )
        if r["project"] == PROJECT and r["configuration"] == "T"
    }
    aligned = (
        rows(OUT / "e1_model_representation_alignment.jsonl")
        if (OUT / "e1_model_representation_alignment.jsonl").exists()
        else []
    )
    fidelities = (
        read(OUT / "e1_fidelity_results.json")
        if (OUT / "e1_fidelity_results.json").exists()
        else {}
    )
    stabilities = (
        read(OUT / "e1_stability_results.json")
        if (OUT / "e1_stability_results.json").exists()
        else {}
    )
    vectors = {
        f: np.load(OUT / f"attributions/{f.lower()}_rep_01.npz")["values"]
        for f in fidelities
    }
    global_rows = (
        rows(OUT / "e1_global_feature_importance.jsonl")
        if (OUT / "e1_global_feature_importance.jsonl").exists()
        else []
    )
    locals_out = (
        rows(OUT / "e1_local_explanations.jsonl")
        if (OUT / "e1_local_explanations.jsonl").exists()
        else []
    )
    failures = (
        read(OUT / "family_execution_failures.json")
        if (OUT / "family_execution_failures.json").exists()
        else {}
    )
    (OUT / "attributions").mkdir(exist_ok=True)
    for family, full in FAMILIES.items():
        if family in fidelities or family in failures:
            continue
        print("START", family, flush=True)
        record = journal[f"{PROJECT}|{full}|FINAL_BASE|T"]
        p = STORE / record["executable"]["path"]
        require(
            sha(p) == record["executable"]["sha256"], "Model artifact digest mismatch"
        )
        COUNTERS["MODEL_LOAD_COUNT"] += 1
        save("governance_counters.json", COUNTERS)
        pipe = joblib.load(p)
        a = alignment(family, pipe, record, state, g4[full])
        aligned.append(a)
        ledger("e1_model_representation_alignment.jsonl", aligned)
        model = pipe.named_steps["model"]
        with threadpool_limits(limits=1):
            if family == "LR":
                output = model.decision_function(x)
                probability = model.predict_proba(x)[:, 1]
                require(
                    np.max(np.abs(expit(output) - probability)) <= 1e-10,
                    "LR sigmoid fidelity failure",
                )
                queries = 2
                base = float(model.intercept_[0] + mu @ model.coef_[0])
                explainer = None
            else:
                if family == "RF":
                    output = model.predict_proba(x)[:, 1]
                elif family == "XGB":
                    output = model.predict(x, output_margin=True)
                else:
                    output = model.predict(x, raw_score=True)
                queries = 1
                explainer = shap.TreeExplainer(
                    model,
                    data=None,
                    feature_perturbation="tree_path_dependent",
                    model_output="raw",
                )
            COUNTERS["MODEL_QUERY_COUNT"] += queries
            COUNTERS["T1_MODEL_QUERY_COUNT"] += queries
            repeats = []
            rep_f = []
            for i, seed in enumerate(SEEDS):
                np.random.seed(seed)
                if family == "LR":
                    phi = (x.toarray() - mu) * model.coef_[0]
                    COUNTERS["ANALYTICAL_ATTRIBUTION_EXECUTION_COUNT"] += 1
                else:
                    # XGBoost retains sparse missing-value semantics. sklearn RF
                    # and LightGBM use dense zero values as in the frozen smoke.
                    COUNTERS["SHAP_EXECUTION_COUNT"] += 1
                    save("governance_counters.json", COUNTERS)
                    try:
                        values = explainer.shap_values(
                            x if family == "XGB" else x.toarray(),
                            approximate=False,
                            check_additivity=True,
                        )
                    except Exception as error:
                        failures[family] = dict(
                            status="INELIGIBLE_EXACT_TREESHAP_FAILURE",
                            attempts=1,
                            error=str(error),
                            values_published=False,
                            repair="No method switch or tolerance relaxation",
                        )
                        save("family_execution_failures.json", failures)
                        break
                    phi = np.asarray(values)
                    base = explainer.expected_value
                    if family == "RF":
                        require(phi.shape == (len(fg), 2557, 2), "RF class-axis shape")
                        phi = phi[:, :, 1]
                        base = base[1]
                    base = float(np.asarray(base).reshape(-1)[0])
                require(phi.shape == (len(fg), 2557), "Attribution shape mismatch")
                f, res = fidelity(phi, base, output, 1e-10 if family == "LR" else 1e-6)
                COUNTERS["E1_ATTRIBUTION_COUNT"] += len(fg)
                np.savez_compressed(
                    OUT / f"attributions/{family.lower()}_rep_{i + 1:02d}.npz",
                    values=phi,
                    base=np.asarray(base),
                    output=output,
                    residual=res,
                    seed=np.asarray(seed),
                )
                repeats.append(phi.copy())
                rep_f.append(f)
                save("governance_counters.json", COUNTERS)
                print(
                    f"{family} repetition {i + 1}/20 residual={f['max_residual']:.3g}",
                    flush=True,
                )
                require(f["failures"] == 0, "Material fidelity failure: STOP")
        if family in failures:
            continue
        primary = repeats[0]
        vectors[family] = primary
        primary_name = (
            f"{family.lower()}_e1_attributions.npz"
            if family == "LR"
            else f"{family.lower()}_e1_shap_values.npz"
        )
        (OUT / primary_name).write_bytes(
            (OUT / f"attributions/{family.lower()}_rep_01.npz").read_bytes()
        )
        save(
            f"{family.lower()}_e1_expected_values.json",
            dict(
                base=base,
                scale=SCALES[family],
                reference="TRAIN centered mean"
                if family == "LR"
                else "TRAIN tree path counts",
            ),
        )
        save(
            "attributions/" + family.lower() + "_array_hashes.json",
            {
                str(p.relative_to(OUT)): sha(p)
                for p in sorted(
                    (OUT / "attributions").glob(f"{family.lower()}_rep_*.npz")
                )
            },
        )
        f = {
            **rep_f[0],
            "repetitions": 20,
            "total_evaluated": len(fg) * 20,
            "max_residual_all_repetitions": max(r["max_residual"] for r in rep_f),
            "repetition_fidelity": rep_f,
        }
        fidelities[family] = f
        save(f"{family.lower()}_e1_fidelity.json", f)
        pairs = []
        for i, j in itertools.combinations(range(20), 2):
            diff = float(np.max(np.abs(repeats[i] - repeats[j])))
            ma = np.abs(repeats[i]).mean(axis=0)
            mb = np.abs(repeats[j]).mean(axis=0)
            tv = (
                float(0.5 * np.abs(ma / ma.sum() - mb / mb.sum()).sum())
                if ma.sum() and mb.sum()
                else None
            )
            pairs.append(
                dict(
                    repetition_a=i + 1,
                    repetition_b=j + 1,
                    max_absolute_difference=diff,
                    total_variation=tv,
                    metrics=[
                        consistency(repeats[i], repeats[j], names, k) for k in [3, 10]
                    ],
                )
            )
        stable = all(
            r["max_absolute_difference"] <= 1e-12
            and r["total_variation"] is not None
            and all(
                m["jaccard"] >= 0.6
                and m["spearman_union"] is not None
                and m["spearman_union"] >= 0.7
                and m["signed_mean_agreement_shared"] is not None
                and m["signed_mean_agreement_shared"] >= 0.8
                and m["row_feature_sign_agreement_shared"] >= 0.8
                for m in r["metrics"]
            )
            for r in pairs
        )
        stabilities[family] = dict(
            status="STABILITY_PASS" if stable else "STABILITY_MIXED",
            repetitions=20,
            pairs_evaluated=190,
            max_absolute_difference=max(r["max_absolute_difference"] for r in pairs),
            pairs=pairs,
            limitation="Fixed-population numerical/ranking repeatability; no population reselection",
        )
        rank = ranking(primary, names)
        mean = np.abs(primary).mean(axis=0)
        signed = primary.mean(axis=0)
        for rank_i, j in enumerate(rank, 1):
            global_rows.append(
                dict(
                    family=family,
                    rank=rank_i,
                    column=j,
                    token=names[j],
                    mean_absolute_attribution=float(mean[j]),
                    signed_mean_attribution=float(signed[j]),
                    nonzero_feature_support=int(x[:, j].count_nonzero()),
                    foreground_n=len(fg),
                    scale=SCALES[family],
                )
            )
        for case in local:
            i = next(
                i
                for i, r in enumerate(fg)
                if r["row_identifier"] == case["row_identifier"]
            )

            def features(positive):
                jj = [
                    j
                    for j in range(2557)
                    if (primary[i, j] > 0 if positive else primary[i, j] < 0)
                ]
                jj = sorted(jj, key=lambda j: (-abs(primary[i, j]), names[j]))[:10]
                return [
                    dict(
                        token=names[j],
                        column=j,
                        feature_value=float(x[i, j]),
                        attribution=float(primary[i, j]),
                        direction="increases model output"
                        if positive
                        else "decreases model output",
                    )
                    for j in jj
                ]

            locals_out.append(
                dict(
                    commit_identity=case["commit_identity"],
                    row_identifier=case["row_identifier"],
                    foreground_index=i,
                    family=family,
                    model_output=float(output[i]),
                    base_value=base,
                    scale=SCALES[family],
                    top_positive_features=features(True),
                    top_negative_features=features(False),
                    complete_attribution_reference=primary_name,
                    fidelity_residual=float(abs(base + primary[i].sum() - output[i])),
                )
            )
        save("e1_fidelity_results.json", fidelities)
        save("e1_stability_results.json", stabilities)
        ledger("e1_global_feature_importance.jsonl", global_rows)
        ledger("e1_local_explanations.jsonl", locals_out)
        manifest()
        print("COMPLETE", family, flush=True)
    cross = []
    for fa, fb in itertools.combinations(vectors, 2):
        for k in [3, 10]:
            m = consistency(vectors[fa], vectors[fb], names, k)
            m.update(family_a=fa, family_b=fb)
            m["thresholds_pass"] = (
                m["jaccard"] >= 0.6
                and m["spearman_union"] is not None
                and m["spearman_union"] >= 0.7
                and m["signed_mean_agreement_shared"] is not None
                and m["signed_mean_agreement_shared"] >= 0.8
            )
            cross.append(m)
    n = sum(r["thresholds_pass"] for r in cross)
    status = (
        "MODEL_EXPLANATIONS_CONSISTENT"
        if n == len(cross)
        else "MODEL_EXPLANATIONS_PARTIALLY_CONSISTENT"
        if n
        else "MODEL_DEPENDENT_EXPLANATIONS"
    )
    save(
        "e1_cross_model_consistency.json",
        dict(
            status=status,
            comparisons=cross,
            thresholds=dict(jaccard=0.6, spearman=0.7, sign=0.8),
            scales_caveat="Ranks/overlap are compared; raw attribution magnitudes are not pooled",
        ),
    )
    top = {f: set(ranking(v, names)[:10]) for f, v in vectors.items()}
    core = set.intersection(*top.values())
    save(
        "e1_explanation_heterogeneity.json",
        dict(
            status="PARTIAL_OVERLAP" if core else "HIGH_HETEROGENEITY",
            consistent_core_features=[names[j] for j in sorted(core)],
            model_specific_features={
                f: [
                    names[j]
                    for j in sorted(
                        s - set.union(*(v for k, v in top.items() if k != f))
                    )
                ]
                for f, s in top.items()
            },
            cross_model_status=status,
            universal_narrative=False,
        ),
    )
    e2_decisions = read(E2 / "e2_primary_reference_decision.json")
    # Use frozen metadata only, never historical labelled prediction payloads.
    scopes = e2_decisions.get("scopes", [])
    ledger(
        "e1_to_e2_traceability.jsonl",
        [
            dict(
                project=PROJECT,
                modality="TEXT",
                family=a["family"],
                e1_model_identity=a["model_identity"],
                e1_model_digest=a["model_digest"],
                e1_vectorizer=a["vectorizer_digest"],
                e2_reference=rel(E2 / "e2_primary_reference_decision.json"),
                e2_reference_digest=sha(E2 / "e2_primary_reference_decision.json"),
                e2_configurations=["C+T", "P+T", "C+P+T"],
                continuity="ARCHITECTURAL",
                same_row_probability_link="NOT_REMEASURED",
                algebraic_propagation=False,
                matching_frozen_scope_records=sum(
                    r.get("project") == PROJECT
                    and r.get("algorithm") == FAMILIES[a["family"]]
                    for r in scopes
                ),
            )
            for a in aligned
        ],
    )
    after = parent_snapshot()
    before = read(OUT / "parent_integrity_before.json")
    require(before == after, "Parent mutation: FAIL")
    save("parent_integrity_after.json", after)
    save("parent_integrity_diff.json", dict(status="UNCHANGED", changed=[]))
    save(
        "e2_parent_integrity_after.json",
        {p: h for p, h in after.items() if p.startswith(rel(E2))},
    )
    save(
        "e2_parent_integrity_diff.json",
        dict(status="UNCHANGED", changed=[], recomputation=0, mutation=0),
    )
    save(
        "governance_counters.json",
        {
            **COUNTERS,
            "counter_units": {
                "T1_IDENTITY_ACCESS_COUNT": "rows read in materialization and execution phases",
                "T1_FEATURE_VALUE_ACCESS_COUNT": "raw/transformed rows loaded",
                "MODEL_QUERY_COUNT": "explicit prediction API calls; TreeSHAP calls separately counted",
                "E1_ATTRIBUTION_COUNT": "row attribution vectors, including 20 repetitions",
                "SHAP_EXECUTION_COUNT": "exact explainer calls including internal additivity checks",
            },
        },
    )
    manifest()
    print("ALL FAMILIES ACCOUNTED FOR; VALID RESULTS PERSISTED", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--bounded-repair", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare(resume=args.bounded_repair)
    elif args.execute:
        execute()
    else:
        raise SystemExit("Select --prepare or --execute")


if __name__ == "__main__":
    main()
