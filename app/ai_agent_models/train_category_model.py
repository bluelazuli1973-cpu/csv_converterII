# category_learner/train_category_model.py
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
from collections import Counter
import math

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


@dataclass
class TrainConfig:
    data_path: Path = Path(__file__).with_name("purchase_training.jsonl")
    model_out: Path = Path(__file__).with_name("category_model.joblib")
    test_size: float = 0.2
    random_state: int = 42


def load_jsonl(path: Path) -> Tuple[List[str], List[str]]:
    texts, labels = [], []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "text" not in obj or "label" not in obj:
                raise ValueError(f"Line {line_no}: expected keys 'text' and 'label'")
            texts.append(str(obj["text"]))
            labels.append(str(obj["label"]))
    if not texts:
        raise ValueError(f"No training rows found in {path}")
    return texts, labels


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=2,
                max_features=20000,
                lowercase=True,
            )),
            ("clf", LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                n_jobs=None,  # keep default for Windows compatibility
            )),
        ]
    )


def _can_stratify(labels: List[str], test_size: float) -> bool:
    """
    Stratified splitting requires:
      - at least 2 samples in every class (scikit-learn requirement)
      - enough room in both splits so each class can appear at least once
    """
    counts = Counter(labels)
    if len(counts) <= 1:
        return False

    min_count = min(counts.values())
    if min_count < 2:
        return False

    n_samples = len(labels)
    n_classes = len(counts)

    n_test = int(math.ceil(n_samples * float(test_size)))
    n_train = n_samples - n_test

    # Each split must be able to contain at least one sample per class.
    if n_test < n_classes or n_train < n_classes:
        return False

    return True


def train_and_save(cfg: TrainConfig) -> None:
    texts, labels = load_jsonl(cfg.data_path)

    use_stratify = _can_stratify(labels, cfg.test_size)
    stratify_arg = labels if use_stratify else None

    if not use_stratify:
        counts = Counter(labels)
        rare = [k for k, v in counts.items() if v < 2]
        print(
            "Warning: disabling stratified split because the dataset is too small or has rare classes.\n"
            f"Total samples: {len(labels)} | classes: {len(counts)} | rare(<2): {rare}\n"
            "Tip: add more examples per category (recommended) to enable stratification."
        )

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=cfg.test_size,
        random_state=cfg.random_state,
        stratify=stratify_arg,
    )

    model = build_pipeline()
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    print(classification_report(y_test, y_pred, zero_division=0))

    joblib.dump(model, cfg.model_out)
    print(f"Saved model to: {cfg.model_out.resolve()}")


if __name__ == "__main__":
    train_and_save(TrainConfig())