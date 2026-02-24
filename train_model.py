import pymssql
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from imblearn.over_sampling import SMOTE
import pickle
import os
import random

random.seed(42)
np.random.seed(42)

# ── اتصل بالـ DB ──────────────────────────────────────
conn = pymssql.connect(
    server='MOHAMED',
    user='sa',
    password='Mhmd02042004',
    database='CarMaintenanceDB'
)
print("✅ Connected to DB")

# ── جيب الداتا ────────────────────────────────────────
query = """
SELECT 
    b.Id                AS booking_id,
    b.TechnicianId      AS technician_id,
    t.Specialization    AS tech_specialization,
    b.Status            AS booking_status,
    ISNULL(r.Rating, 0) AS review_rating,
    (SELECT STRING_AGG(s.Category, ',') 
     FROM BookingServices bs
     JOIN Services s ON bs.ServiceId = s.Id
     WHERE bs.BookingId = b.Id) AS service_categories,
    CASE WHEN b.Status = 2 THEN 1 ELSE 0 END AS was_successful
FROM Bookings b
JOIN Technicians t ON b.TechnicianId = t.Id
LEFT JOIN Reviews r ON r.BookingId = b.Id
WHERE b.TechnicianId IS NOT NULL
AND b.Id >= 4
"""

df = pd.read_sql(query, conn)
conn.close()
print(f"✅ Loaded {len(df)} records")

# ── Technician Profiles ───────────────────────────────
TECH_PROFILES = {
    'tech-001': {'base_success': 0.88, 'base_rating': 4.7, 'experience': 8},
    'tech-002': {'base_success': 0.82, 'base_rating': 4.5, 'experience': 5},
    'tech-003': {'base_success': 0.78, 'base_rating': 4.3, 'experience': 4},
    'tech-004': {'base_success': 0.85, 'base_rating': 4.6, 'experience': 6},
    'tech-005': {'base_success': 0.74, 'base_rating': 4.2, 'experience': 3},
}

# ── Feature Engineering ───────────────────────────────

def calc_spec_match(tech_specs, service_cats):
    if not service_cats or not tech_specs:
        return 0.5
    specs = [s.strip().lower() for s in str(tech_specs).split(',')]
    cats  = [c.strip().lower() for c in str(service_cats).split(',')]
    matches = sum(1 for c in cats if c in specs)
    return round(matches / len(cats), 3)


rows = []
for _, row in df.iterrows():
    tech_id  = row['technician_id']
    profile  = TECH_PROFILES.get(tech_id, {})

    spec_match = calc_spec_match(row['tech_specialization'], row['service_categories'])

    base_rating = profile.get('base_rating', 4.0) / 5.0
    avg_rating  = round(base_rating + np.random.normal(0, 0.02), 3)
    avg_rating  = min(max(avg_rating, 0.0), 1.0)

    base_sr      = profile.get('base_success', 0.75)
    success_rate = round(base_sr + np.random.normal(0, 0.03), 3)
    success_rate = min(max(success_rate, 0.1), 1.0)

    workload_score = round(random.choices(
        [1.0, 0.82, 0.55, 0.25],
        weights=[25, 35, 25, 15]
    )[0] + np.random.normal(0, 0.03), 3)
    workload_score = min(max(workload_score, 0.1), 1.0)

    exp_score = round(min(profile.get('experience', 3) / 10.0, 1.0), 3)

    rows.append({
        'specialization_match': spec_match,
        'avg_rating':           avg_rating,
        'success_rate':         success_rate,
        'workload_score':       workload_score,
        'experience_score':     exp_score,
        'was_successful':       row['was_successful']
    })

df_features = pd.DataFrame(rows)

print(f"\n📊 Feature Stats:")
print(df_features.drop('was_successful', axis=1).describe().round(3))
print(f"\n🎯 Target Distribution:")
print(df_features['was_successful'].value_counts())

# ── Features و Target ─────────────────────────────────
features = ['specialization_match', 'avg_rating', 'success_rate', 'workload_score', 'experience_score']
X = df_features[features]
y = df_features['was_successful']

# ── SMOTE ─────────────────────────────────────────────
sm = SMOTE(random_state=42, k_neighbors=3)
X_balanced, y_balanced = sm.fit_resample(X, y)

print(f"\n✅ After SMOTE:")
print(f"   Success: {sum(y_balanced == 1)}")
print(f"   Failure: {sum(y_balanced == 0)}")

# ── Train/Test Split ──────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X_balanced, y_balanced, test_size=0.2, random_state=42, stratify=y_balanced
)

# ── Train Model ───────────────────────────────────────
model = XGBClassifier(
    n_estimators=100,
    max_depth=3,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    random_state=42,
    eval_metric='logloss'
)

model.fit(X_train, y_train)

# ── Evaluate ──────────────────────────────────────────
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\n✅ Model Accuracy: {accuracy:.2%}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))
print("\n📊 Feature Importance:")
for feat, imp in zip(features, model.feature_importances_):
    print(f"  {feat}: {imp:.3f}")

# ── Save ──────────────────────────────────────────────
os.makedirs('models/ml', exist_ok=True)
with open('models/ml/technician_model.pkl', 'wb') as f:
    pickle.dump({
        'model':    model,
        'features': features,
        'version':  '2.0'
    }, f)

print("\n✅ Model saved: models/ml/technician_model.pkl")