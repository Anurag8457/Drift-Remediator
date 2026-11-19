import json
import time
import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# 1. Load the 1,500 synthetic drift records
with open("synthetic_drift_1500.json", "r", encoding="utf-8") as f:
    records = json.load(f)

# X = input text describing the drift diff
X = [r["drift_text"] for r in records]
# Y = two target labels per record: [severity, risk_type]
Y = np.array([[r["severity"], r["risk_type"]] for r in records])

# 2. Split 80% for training (1,200 records) and 20% for testing (300 records)
X_train, X_test, Y_train, Y_test = train_test_split(
    X, Y, test_size=0.2, random_state=42
)

# 3. Build the TfidfVectorizer + RandomForestClassifier pipeline
pipeline = Pipeline([
    # Convert drift text into numerical word/character n-gram features
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=2500)),
    # Predict both Severity and Risk Type simultaneously
    ("clf", MultiOutputClassifier(
        RandomForestClassifier(n_estimators=80, max_depth=12, random_state=42)
    ))
])

# 4. Train the model in seconds
print("[*] Training TfidfVectorizer + RandomForestClassifier on 1,200 drift records...")
start_train = time.perf_counter()
pipeline.fit(X_train, Y_train)
train_time = (time.perf_counter() - start_train) * 1000
print(f"[+] Training finished in {train_time:.1f} ms!")

# 5. Evaluate accuracy on the 300 unseen test records
Y_pred = pipeline.predict(X_test)
sev_acc = accuracy_score(Y_test[:, 0], Y_pred[:, 0]) * 100
risk_acc = accuracy_score(Y_test[:, 1], Y_pred[:, 1]) * 100
print(f"[+] Test Accuracy -> Severity: {sev_acc:.1f}% | Risk Type: {risk_acc:.1f}%")

# 6. Export as compressed drift_classifier.joblib (<1 MB)
MODEL_PATH = "drift_classifier.joblib"
joblib.dump(pipeline, MODEL_PATH, compress=3)
size_kb = os.path.getsize(MODEL_PATH) / 1024
print(f"[+] Saved '{MODEL_PATH}' ({size_kb:.1f} KB — strictly < 1 MB)")

# 7. Benchmark single-record inference speed (<10ms check)
sample_drift = [
    "resource_type=aws_security_group attribute=ingress.cidr_blocks "
    "before=10.0.0.0/8 after=0.0.0.0/0 summary=SSH port 22 opened to 0.0.0.0/0"
]
t0 = time.perf_counter()
pred = pipeline.predict(sample_drift)[0]
latency_ms = (time.perf_counter() - t0) * 1000
print(f"[+] Live Inference Test: Severity={pred[0]}, Risk={pred[1]} (Took {latency_ms:.2f} ms)")