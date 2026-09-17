"""Evaluation metrics for the cervical multimodal prognosis task."""
import numpy as np
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, average_precision_score,
                             confusion_matrix, roc_curve, precision_recall_curve)
from lifelines.utils import concordance_index


def classification_metrics(y_true, y_score, threshold=0.5):
    """Return a dict of classification metrics. y_score is logit/probability of positive class."""
    y_pred = (np.asarray(y_score) >= threshold).astype(int)
    y_true = np.asarray(y_true)
    out = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    if len(np.unique(y_true)) > 1:
        out["auc"] = roc_auc_score(y_true, y_score)
        out["auprc"] = average_precision_score(y_true, y_score)
    else:
        out["auc"] = float("nan")
        out["auprc"] = float("nan")
    return out


def c_index(event_time, event_indicator, risk_score):
    """Concordance index for survival (higher risk = worse outcome)."""
    try:
        return concordance_index(event_time, -np.asarray(risk_score), event_indicator)
    except Exception:
        return float("nan")


def roc_pr_curves(y_true, y_score):
    fpr, tpr, _ = roc_curve(y_true, y_score)
    prec, rec, _ = precision_recall_curve(y_true, y_score)
    return {"fpr": fpr, "tpr": tpr, "precision": prec, "recall": rec}


def confusion(y_true, y_score, threshold=0.5):
    y_pred = (np.asarray(y_score) >= threshold).astype(int)
    return confusion_matrix(np.asarray(y_true), y_pred)
