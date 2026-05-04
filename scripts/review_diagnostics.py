"""
Validity review diagnostic script.
Run: conda run -n py311_ds python scripts/review_diagnostics.py
"""
import warnings
warnings.filterwarnings('ignore')

import json
import pickle
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import mapclassify
from pathlib import Path
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss
from sklearn.inspection import permutation_importance

ROOT      = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / 'data' / 'processed'
OUTPUTS   = ROOT / 'outputs'
MODELS    = ROOT / 'models'
RAW       = ROOT / 'data' / 'raw'

with open(PROCESSED / 'selected_features_v2.json') as f:
    feat_meta = json.load(f)
# The saved best models were trained with 27 features (et and soil_moisture
# were added to selected_features_v2.json AFTER the models were saved).
# Use the 27-feature subset that matches the actual models.
FEATURES_ADDED_AFTER_TRAINING = {'et', 'soil_moisture'}
MODEL_FEATURES = [f for f in feat_meta['all_model_features']
                  if f not in FEATURES_ADDED_AFTER_TRAINING]
CONT_FEATURES  = [f for f in feat_meta['continuous_features']
                  if f not in FEATURES_ADDED_AFTER_TRAINING]

train = pd.read_csv(PROCESSED / 'train_v2.csv')
test  = pd.read_csv(PROCESSED / 'test_v2.csv')
df    = pd.read_csv(PROCESSED / 'dataset_v2.csv')

X_train = train[MODEL_FEATURES].values
y_train = train['label'].values
X_test  = test[MODEL_FEATURES].values
y_test  = test['label'].values

with open(MODELS / 'lightgbm_v2_best.pkl', 'rb') as f:
    lgbm = pickle.load(f)

proba = lgbm.predict_proba(X_test)[:, 1]

# ──────────────────────────────────────────────────────────────────────────────
print('\n' + '='*70)
print('1. FEATURE UNIQUE VALUES (detect resolution issue)')
print('='*70)
for col in MODEL_FEATURES:
    if col in df.columns:
        n = df[col].nunique()
        flag = ' *** LOW ***' if n < 5000 else ''
        print(f'  {col:35s}: {n:6d} unique{flag}')

# ──────────────────────────────────────────────────────────────────────────────
print('\n' + '='*70)
print('2. CLASS BALANCE TRAIN vs TEST (GroupShuffleSplit not stratified)')
print('='*70)
print(f'  Train: {len(train):,}  fire_rate={train.label.mean():.4f}  blocks={train.block_id.nunique()}')
print(f'  Test:  {len(test):,}   fire_rate={test.label.mean():.4f}   blocks={test.block_id.nunique()}')
delta = abs(train.label.mean() - test.label.mean())
flag = 'WARN' if delta > 0.05 else 'OK'
print(f'  Delta: {delta:.4f}  [{flag}]')

# ──────────────────────────────────────────────────────────────────────────────
print('\n' + '='*70)
print('3. CALIBRATION (LightGBM best, holdout test)')
print('='*70)
frac_pos, mean_pred = calibration_curve(y_test, proba, n_bins=10)
for mp, fp in zip(mean_pred, frac_pos):
    d = abs(fp - mp)
    bar = '#' * int(fp * 20)
    flag = ' <-- OVERCONFIDENT' if d > 0.1 else ''
    print(f'  pred={mp:.3f}  actual={fp:.3f}  delta={d:.3f}  {bar}{flag}')
ece = np.mean(np.abs(frac_pos - mean_pred))
brier = brier_score_loss(y_test, proba)
flag = 'FAIL' if ece > 0.05 else 'OK'
print(f'  ECE={ece:.4f} [{flag}]  Brier={brier:.4f}')
print(f'  Prob: p<0.3={100*(proba<0.3).mean():.1f}%  0.3-0.7={100*((proba>=0.3)&(proba<=0.7)).mean():.1f}%  p>0.7={100*(proba>0.7).mean():.1f}%')

# ──────────────────────────────────────────────────────────────────────────────
print('\n' + '='*70)
print('4. SENSITIVITY OF 80% METRIC TO CLASSIFICATION SCHEME')
print('='*70)

viirs = gpd.read_file(PROCESSED / 'firms_viirs.gpkg')
viirs['date'] = viirs['date'].astype(str)
viirs_val = viirs[(viirs['date'] >= '2023-01-01') & (viirs['date'] <= '2024-12-31')]
lons_fire = viirs_val.geometry.x.values
lats_fire = viirs_val.geometry.y.values
coords_fire = list(zip(lons_fire, lats_fire))

with rasterio.open(OUTPUTS / 'susceptibility.tif') as src:
    fire_samples = list(src.sample(coords_fire))
    prob_band = src.read(1).ravel()

fire_proba = np.array([s[0] for s in fire_samples], dtype=float)
valid = ~np.isnan(fire_proba)
fire_proba = fire_proba[valid]
prob_valid = prob_band[~np.isnan(prob_band)]
print(f'  Fire points validated: {valid.sum():,}')

def pct_high(classes):
    return 100 * (classes >= 3).sum() / len(classes)

# 1. Jenks (current)
jk = mapclassify.NaturalBreaks(prob_valid, k=4)
jk_bins = jk.bins
jk_fire = np.digitize(fire_proba, bins=jk_bins[:3]) + 1
jk_fire = np.clip(jk_fire, 1, 4)
print(f'  Jenks (current):       High+VH = {pct_high(jk_fire):.1f}%  breaks={jk_bins.round(3)}')

# 2. Quantile (on global grid probabilities)
q25, q50, q75 = np.percentile(prob_valid, [25, 50, 75])
qt_fire = np.digitize(fire_proba, bins=[q25, q50, q75]) + 1
qt_fire = np.clip(qt_fire, 1, 4)
print(f'  Quantile (25/50/75):   High+VH = {pct_high(qt_fire):.1f}%  breaks=[{q25:.3f},{q50:.3f},{q75:.3f}]')

# 3. Equal interval
emin, emax = prob_valid.min(), prob_valid.max()
ei_breaks = [emin + (emax-emin)*t for t in [0.25, 0.50, 0.75]]
ei_fire = np.digitize(fire_proba, bins=ei_breaks) + 1
ei_fire = np.clip(ei_fire, 1, 4)
print(f'  Equal interval:        High+VH = {pct_high(ei_fire):.1f}%  breaks={[round(b,3) for b in ei_breaks]}')

# 4. Fixed thresholds
fx_fire = np.where(fire_proba > 0.7, 4, np.where(fire_proba > 0.5, 3, np.where(fire_proba > 0.3, 2, 1)))
print(f'  Fixed (0.3/0.5/0.7):   High+VH = {pct_high(fx_fire):.1f}%')

# 5. Null model (random proba, same Jenks breaks)
rng = np.random.default_rng(42)
rand_proba = rng.uniform(0, 1, len(fire_proba))
rand_fire = np.digitize(rand_proba, bins=jk_bins[:3]) + 1
rand_fire = np.clip(rand_fire, 1, 4)
print(f'  Null (random proba):   High+VH = {pct_high(rand_fire):.1f}%  <-- baseline')

# ──────────────────────────────────────────────────────────────────────────────
print('\n' + '='*70)
print('5. PERMUTATION IMPORTANCE vs FEATURE IMPORTANCE')
print('='*70)
fi = lgbm.feature_importances_
fi_sorted = sorted(zip(MODEL_FEATURES, fi), key=lambda x: -x[1])
print('  LightGBM feature_importances_ (top 10):')
for feat, imp in fi_sorted[:10]:
    print(f'    {feat:35s}: {imp:6d}')

print('\n  Computing permutation importance (may take ~30s)...')
pi_result = permutation_importance(lgbm, X_test, y_test, n_repeats=5,
                                   random_state=42, scoring='roc_auc', n_jobs=-1)
pi_sorted = sorted(zip(MODEL_FEATURES, pi_result.importances_mean),
                   key=lambda x: -x[1])
print('  Permutation importance - mean AUC drop (top 10):')
for feat, imp in pi_sorted[:10]:
    flag = ''
    fi_rank = [f[0] for f in fi_sorted].index(feat) + 1
    pi_rank = [f[0] for f in pi_sorted].index(feat) + 1
    if abs(fi_rank - pi_rank) > 5:
        flag = f'  <-- RANK DISAGREE (fi={fi_rank}, pi={pi_rank})'
    print(f'    {feat:35s}: {imp:.4f}{flag}')

# ──────────────────────────────────────────────────────────────────────────────
print('\n' + '='*70)
print('6. PHASE1 SOIL UNIQUE VALUES (SoilGrids resolution)')
print('='*70)
for f in ['soc','clay','phh2o']:
    n = df[f].nunique() if f in df.columns else 'MISSING'
    print(f'  {f}: {n} unique')

# ──────────────────────────────────────────────────────────────────────────────
print('\n' + '='*70)
print('7. BOOTSTRAP CI FOR TEST AUC (500 resamples)')
print('='*70)
from sklearn.metrics import roc_auc_score
rng2 = np.random.default_rng(42)
aucs = []
for _ in range(500):
    idx = rng2.integers(0, len(y_test), len(y_test))
    try:
        a = roc_auc_score(y_test[idx], proba[idx])
        aucs.append(a)
    except Exception:
        pass
aucs = np.array(aucs)
print(f'  AUC mean={aucs.mean():.4f}  95% CI=[{np.percentile(aucs,2.5):.4f}, {np.percentile(aucs,97.5):.4f}]')

print('\nDone.')
