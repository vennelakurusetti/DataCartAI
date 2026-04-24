"""
DataCartAI — ML Model Loader
Loads the ONE recommender model (LightGBM or RandomForest)
once at server startup. Keeps it in memory for fast serving.

After running the Colab notebook, paste these files into
backend/app/ml/models/ :
    lgbm_model.txt       (LightGBM — preferred)
    rf_model.pkl         (RandomForest — fallback)
    label_encoder.pkl    (class name decoder)
    metadata.json        (feature list + class names)
"""
from __future__ import annotations
import json, logging
from pathlib import Path

log = logging.getLogger("model_loader")

MODELS_DIR = Path(__file__).parent / "models"

# ── Global model references (populated at startup) ───────────
_lgbm_model    = None   # LightGBM Booster
_rf_model      = None   # scikit-learn RandomForest (fallback)
_label_encoder = None   # sklearn LabelEncoder
_metadata      = {}     # dict from metadata.json


# ─────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────

def load_all_models():
    """
    Called once when FastAPI starts.
    Tries LightGBM first, then RF, then rule-based fallback.
    """
    global _lgbm_model, _rf_model, _label_encoder, _metadata
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 1 ── Load LightGBM (preferred — faster and more accurate)
    lgb_path = MODELS_DIR / "lgbm_model.txt"
    if lgb_path.exists():
        try:
            import lightgbm as lgb
            _lgbm_model = lgb.Booster(model_file=str(lgb_path))
            log.info("✅ LightGBM recommender model loaded")
        except Exception as e:
            log.warning(f"LightGBM load failed: {e}")

    # 2 ── Load RandomForest as fallback
    rf_path = MODELS_DIR / "rf_model.pkl"
    if rf_path.exists():
        try:
            import joblib
            _rf_model = joblib.load(str(rf_path))
            log.info("✅ RandomForest recommender model loaded")
        except Exception as e:
            log.warning(f"RF load failed: {e}")

    # 3 ── Load Label Encoder (needed to decode predictions)
    le_path = MODELS_DIR / "label_encoder.pkl"
    if le_path.exists():
        try:
            import joblib
            _label_encoder = joblib.load(str(le_path))
            log.info("✅ Label encoder loaded")
        except Exception as e:
            log.warning(f"Label encoder load failed: {e}")

    # 4 ── Load metadata JSON
    meta_path = MODELS_DIR / "metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                _metadata = json.load(f)
            log.info(f"✅ Metadata loaded — best model: {_metadata.get('best_model','?')}")
        except Exception as e:
            log.warning(f"Metadata load failed: {e}")

    # Status summary
    if _lgbm_model is None and _rf_model is None:
        log.warning(
            "⚠️  No trained model found in backend/app/ml/models/ — "
            "using rule-based scoring fallback. "
            "Run the Colab notebook and copy model files here."
        )
    else:
        model_type = "LightGBM" if _lgbm_model else "RandomForest"
        log.info(f"Model ready: {model_type}")


# ─────────────────────────────────────────────────────────────
# GETTERS  (used by recommender.py)
# ─────────────────────────────────────────────────────────────

def get_lgbm_model():
    """Returns LightGBM booster or None."""
    return _lgbm_model

def get_rf_model():
    """Returns sklearn RF model or None."""
    return _rf_model

def get_best_model():
    """Returns whichever model is available (LightGBM preferred)."""
    return _lgbm_model or _rf_model

def get_label_encoder():
    """Returns sklearn LabelEncoder or None."""
    return _label_encoder

def get_metadata() -> dict:
    """Returns metadata dict from Colab training."""
    return _metadata

def model_is_loaded() -> bool:
    return _lgbm_model is not None or _rf_model is not None

def model_type() -> str:
    if _lgbm_model:  return "LightGBM"
    if _rf_model:    return "RandomForest"
    return "rule-based"