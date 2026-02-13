from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Optional, Union


PathLike = Union[str, Path]


def _package_dir() -> Path:
    return Path(__file__).resolve().parent


def _project_root() -> Path:
    """
    Best-effort project root resolver.

    Assumes this file lives at:
        <root>/app/ai_agent_models/__init__.py
    """
    return Path(__file__).resolve().parents[2]


def _default_training_csv() -> Path:
    """
    Default CSV used to generate purchase_training.jsonl if caller doesn't provide one.
    """
    return _project_root() / "test_data" / "Ekonomi_copyfor_testingaa.csv"


def ensure_category_model(
    *,
    csv_path: Optional[PathLike] = None,
    force_retrain: bool = False,
) -> Path:
    """
    Ensure a trained category model exists.

    If the model file doesn't exist (or force_retrain=True), this will:
      1) Generate purchase_training.jsonl from a CSV (swedish_csv_to_training)
      2) Train and save the model (train_category_model)

    Notes:
      - If joblib isn't installed, training will save a pickle fallback:
            category_model.joblib.pkl
        (assuming you've implemented the fallback in train_category_model.py)

    Returns:
      The preferred model path (category_model.joblib). The actual file may be
      category_model.joblib.pkl if joblib is unavailable.
    """
    base_dir = _package_dir()
    data_path = base_dir / "purchase_training.jsonl"
    model_joblib_path = base_dir / "category_model.joblib"
    model_pickle_path = model_joblib_path.with_suffix(model_joblib_path.suffix + ".pkl")

    model_exists = model_joblib_path.exists() or model_pickle_path.exists()

    if model_exists and not force_retrain:
        return model_joblib_path

    # 1) Ensure training data exists (or regenerate)
    if force_retrain or not data_path.exists():
        from .swedish_csv_to_training import ConvertConfig, convert_csv_to_jsonl

        if csv_path is None:
            csv_path = _default_training_csv()

        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(
                "Training CSV not found.\n"
                f"Looked for: {csv_path}\n"
                "Pass csv_path=... to ensure_category_model(), or put the file in test_data/."
            )

        convert_csv_to_jsonl(ConvertConfig(csv_path=csv_path, out_jsonl=data_path))

    # 2) Train and save model
    from .train_category_model import TrainConfig, train_and_save

    cfg = TrainConfig()
    cfg = replace(cfg, data_path=data_path, model_out=model_joblib_path)
    train_and_save(cfg)

    return model_joblib_path


__all__ = ["ensure_category_model"]