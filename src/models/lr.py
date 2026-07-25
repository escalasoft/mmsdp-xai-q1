"""Scikit-learn logistic regression adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Sized
from dataclasses import dataclass, field
from typing import Self

from sklearn.linear_model import LogisticRegression as _LogisticRegression

from models.base import BaseModel

__all__ = ["LogisticRegressionModel"]


@dataclass(frozen=True, slots=True)
class _LogisticRegressionMetadata:
    """Metadata used to initialize a logistic regression model."""

    model_name: str
    algorithm: str
    modality: str
    class_labels: Sequence[object]
    configuration: Mapping[str, object] = field(default_factory=dict)


class LogisticRegressionModel(BaseModel[object, object, object, object]):
    """Framework-neutral adapter for scikit-learn logistic regression.

    Args:
        class_labels: Labels in the required probability-column order.
        modality: Name of the single input modality represented by the features.
        configuration: Keyword arguments accepted by
            :class:`sklearn.linear_model.LogisticRegression`.
    """

    def __init__(
        self,
        class_labels: Sequence[object] = (0, 1),
        *,
        modality: str = "GENERIC",
        configuration: Mapping[str, object] | None = None,
    ) -> None:
        """Initialize an unfitted logistic regression adapter."""
        labels = tuple(class_labels)
        if not labels:
            raise ValueError("class_labels must not be empty")
        if len(set(labels)) != len(labels):
            raise ValueError("class_labels must not contain duplicates")

        settings = {} if configuration is None else dict(configuration)
        metadata = _LogisticRegressionMetadata(
            model_name=type(self).__name__,
            algorithm="logistic-regression",
            modality=modality,
            class_labels=labels,
            configuration=settings,
        )
        super().__init__(metadata)
        self._estimator = _LogisticRegression(**settings)

    def fit(self, features: object, targets: object, /) -> Self:
        """Fit logistic regression and return this adapter."""
        self._require_not_none(features, "features")
        self._require_not_none(targets, "targets")
        if isinstance(features, Sized) and isinstance(targets, Sized):
            self._require_same_length(features, targets)

        self._mark_unfitted()
        estimator = _LogisticRegression(**dict(self.metadata.configuration))
        estimator.fit(features, targets)
        fitted_labels = tuple(estimator.classes_)
        declared_labels = tuple(self.metadata.class_labels)
        if len(fitted_labels) != len(declared_labels) or set(fitted_labels) != set(
            declared_labels
        ):
            raise ValueError(
                "fitted target classes must exactly match metadata.class_labels"
            )

        self._estimator = estimator
        self._mark_fitted()
        return self

    def predict(self, features: object, /) -> object:
        """Predict one class label for each observation."""
        self._require_not_none(features, "features")
        self._require_fitted()
        return self._estimator.predict(features)

    def predict_proba(self, features: object, /) -> object:
        """Predict probabilities in the declared metadata label order."""
        self._require_not_none(features, "features")
        self._require_fitted()
        probabilities = self._estimator.predict_proba(features)
        column_by_label = {
            label: index for index, label in enumerate(self._estimator.classes_)
        }
        ordered_columns = [
            column_by_label[label] for label in self.metadata.class_labels
        ]
        return probabilities[:, ordered_columns]
