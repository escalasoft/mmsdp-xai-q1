#!/usr/bin/env python3
"""Execute the sealed-TEST Qt unimodal baseline specification."""

import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy
import scipy
import sklearn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from experimentation.qt_unimodal_baselines import (  # noqa: E402
    QtBaselineBoundaryError,
    load_qt_model_ready,
    run_qt_baselines,
)

source = (
    ROOT
    / "artifacts/qtbase/datasets"
    / "a1af25290bbd078628e362d4b704a047853d620c"
    / "qt-model-inputs.json"
)
config_path = ROOT / "configs/experiments/qt_unimodal_baselines_1.0.0.json"
configuration = json.loads(config_path.read_text())
destination = ROOT / "outputs/metrics/qt-unimodal-baselines-1.0.0.json"
prepared = load_qt_model_ready(source)
try:
    result = run_qt_baselines(prepared, configuration)
except QtBaselineBoundaryError as error:

    def distribution(values):
        positive = sum(value == 1 for value in values)
        return {
            "count": len(values),
            "negative_count": len(values) - positive,
            "positive_count": positive,
            "positive_rate": positive / len(values),
        }

    result = {
        "schema_version": "qt-unimodal-baseline-blocked-results-1.0.0",
        "status": "blocked-before-fit",
        "reason": str(error),
        "configuration": configuration,
        "source_model_input_identity_digest": (
            prepared.source_model_input_identity_digest
        ),
        "preparation_identity_digest": prepared.preparation_identity_digest,
        "text_policy_digest": prepared.representation_policy.policy_digest,
        "text_state_digest": prepared.text_state.state_digest,
        "partition_identity_digests": {
            name: hashlib.sha256(
                json.dumps(
                    list(getattr(prepared, name).identifiers),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            for name in ("train", "validation", "test")
        },
        "partition_counts": dict(prepared.partition_counts),
        "feature_counts": {
            "CODE": len(prepared.code_feature_names),
            "PROCESS": len(prepared.process_feature_names),
            "TEXT": len(prepared.text_feature_names),
        },
        "class_distributions": {
            "train": distribution(prepared.train.y),
            "validation": distribution(prepared.validation.y),
        },
        "software_versions": {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "runs": [
            {
                "modality": modality,
                "model": model,
                "status": "blocked-before-fit",
                "reason": "single-class TRAIN and VALIDATION",
            }
            for modality in ("CODE", "PROCESS", "TEXT")
            for model in ("LR", "RF")
        ],
        "test_sealing": {
            "structural_checks_only": True,
            "predict_called": False,
            "targets_used_for_metrics": False,
            "outcomes_persisted": False,
        },
        "scientific_exclusions": {
            "fusion": False,
            "calibration": False,
            "xai": False,
            "human_18c_consumed": False,
            "test_predictive_evaluation": False,
        },
    }
    result["results_identity_digest"] = hashlib.sha256(
        json.dumps(
            result, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()
    report = ROOT / "outputs/reports/qt-unimodal-baselines-1.0.0.md"
    report.write_text(
        "# Qt unimodal baseline execution 1.0.0\n\n"
        "Status: **blocked before model fitting**.\n\n"
        f"Reason: {error}. TRAIN contains 0 positive and 11,718 negative observations; "
        "VALIDATION contains 0 positive and 2,511 negative observations. Binary "
        "LR/RF fitting "
        "and ROC-AUC/PR-AUC evaluation are therefore scientifically undefined.\n\n"
        "All six CODE/PROCESS/TEXT × LR/RF runs were blocked before fit. No "
        "predictions or probabilities were produced. TEST participated only in "
        "reconstruction and structural alignment checks; no TEST predictive outcome "
        "was inspected. No fusion, calibration, "
        "XAI, resampling, refitting, or human 18C evidence was used.\n",
        encoding="utf-8",
    )
destination.write_text(
    json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
)
print(destination)
