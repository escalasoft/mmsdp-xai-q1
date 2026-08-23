# Sprint 10.8.2.37 — DEVELOPMENT Decision-Curve / Practical-Utility Protocol Declaration

## 1. Scientific decision

**SPRINT_10.8.2.37_GO_WITH_LIMITATIONS**. The DEVELOPMENT-only protocol is frozen and outcome-independent. This does not select a final model, calibrator, or threshold and does not authorize TEST access.

## 2. Branch / starting HEAD

`sprint-10/q1-development-practical-utility-protocol` from `abce993b1cf4664d3554a6ecbe58d33debba41bb`.

## 3. Purpose of Sprint 37

Predeclare practical-utility methods before execution, removing researcher degrees of freedom. No decision curve or utility comparison was calculated.

## 4. Prior evidence inherited from Sprint 36

Equal-weight leakage-safe C+T remains a reference, not a final model. ISOTONIC passed aggregate calibration adequacy but gains were modest and it introduced discrimination degradation/ties. No final calibrator or threshold was selected. Sprint 36 concluded `DECISION_CURVE_PROTOCOL_NOT_READY`; this sprint supplies the missing fixed cost and threshold contracts.

## 5. JIT-SDP operational decision semantics

At each commit the predictor emits a defect-proneness probability. Crossing a threshold flags the commit for additional quality attention (review, testing, inspection prioritization, or alert). Predictive classification is distinct from an operational intervention; no empirical industrial deployment cost is claimed.

## 6. TP/FP/TN/FN interpretation

TP is a defect-prone commit correctly flagged; FP is a non-defect-prone commit unnecessarily flagged; TN is a non-defect-prone commit correctly not flagged; FN is a missed opportunity to flag a defect-prone commit.

## 7. Frozen cost scenarios

Normalized `C_TP=C_TN=0`, `C_FP=1`; FN/FP ratios are **1, 2, 5, 10, 20**. These are sensitivity scenarios, not monetary or organization-specific costs, and cannot be changed after observing outcomes.

## 8. Frozen threshold grid

**0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95**. The grid is identical across origins, calibration states, and candidates. `0.50` is the historical non-optimized reference. No post-hoc threshold addition or optimization is permitted.

## 9. Decision-curve formulation

`NB(t) = TP(t) / N - FP(t) / N * t / (1 - t)`, compared with Treat None / Flag None, Treat All / Flag All, and the reference predictor(s).

## 10. Practical-utility formulation

`ExpectedCost(t, r) = FP(t) * C_FP + FN(t) * C_FN(r)`, where `C_FN(r)=r`; `NormalizedCost(t, r) = ExpectedCost(t, r) / N`. Lower is better. Utility is not composited with discrimination, calibration, MCC, or F1.

## 11. Calibration states eligible for future comparison

UNCALIBRATED, PLATT, and ISOTONIC remain eligible for descriptive DEVELOPMENT comparison. This preserves Sprint 36's mixed evidence and makes no final-calibrator claim.

## 12. Temporal membership governance

Verdict: **MATCHES_FROZEN_SPRINT_36_DEVELOPMENT_MEMBERSHIPS**. O1–O5 and their train, calibration, evaluation, project support, prevalence, exclusions, membership digests, and source hashes are persisted. Boundaries and difficult origins cannot be moved or dropped.

## 13. Metric hierarchy

Every origin × calibration state × threshold must report TP, FP, TN, FN, recall, specificity, precision, MCC, predicted-positive rate, prevalence, net benefit, and normalized costs. ROC-AUC, PR-AUC, Brier, and ECE remain probability-level diagnostics. Accuracy or F1 cannot be sole evidence; F1 is descriptive only.

## 14. Dispersion policy

Across origins report median, minimum, maximum, Q1, Q3, and IQR; add mean, standard deviation, and confidence intervals where defensible. Article evidence must support box/distribution plots, not a single average.

## 15. Statistical-inference / BH-FDR policy

No inference occurred. Future multiple comparisons report magnitude/effect size first, uncertainty, raw p-values where applicable, and Benjamini–Hochberg FDR-adjusted p-values for the predeclared family. Neutral results remain; `p>=0.05` is not equivalence. Five origins give limited resolution, and commits are not independent experimental replications.

## 16. Advancement rule

Advancement jointly considers leakage safety, temporal validity, reproducibility, discrimination, calibration, utility, parsimony, stability, and absence of outcome tuning. No single best metric suffices. The simplest defensible candidate may advance despite a marginally lower isolated score. No candidate is selected here.

## 17. Destefanis et al. methodological alignment

The machine-readable checklist maps applicable R1–R10, R14, and R15 recommendations. It is not a new validated scientific score.

## 18. Reproducibility / hashes

Configuration, historical Sprint 32–36 artifacts, memberships, generated artifacts, version, seed, branch, and starting HEAD are hash-addressed in the manifests.

## 19. TEST governance

TEST remains sealed: scoring, predictive scoring, model selection, threshold optimization, calibration fitting, and XAI are all zero and unauthorized.

## 20. Execution ledger

Model fits, meta-learner fits, calibration fits, decision curves, utility scoring, threshold optimizations, hyperparameter searches, XAI, external acquisitions, and every TEST counter are zero. Sprint 37 declares only.

## 21. Quality-gate results

Focused Sprint 37 tests: **10 passed**. Relevant temporal, calibration,
evaluation, and governance tests: **105 passed**. Full pytest: **1394 passed,
1 skipped**. Sprint 37 Ruff, Python compilation, and `git diff --check`:
**PASS**. Full-repository Ruff is reported separately if historical findings
remain.

## 22. Limitations

Costs are normalized scenarios rather than observed industrial costs; only five origins limit inference; calibration evidence is DEVELOPMENT-only; C+T and all calibrators remain candidates; no utility outcomes or external validity are established.

## 23. Exact recommended next sprint

Sprint 10.8.2.38 — Execute Frozen DEVELOPMENT Decision-Curve and Practical-Utility Evaluation. Execute this protocol on DEVELOPMENT only; keep TEST sealed.
