import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=8000,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    solver="liblinear",
                ),
            ),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train complaint category classifier.")
    parser.add_argument("--input", default="data/sample_complaints.csv", help="CSV with text,category columns.")
    parser.add_argument("--output", default="models/complaint_classifier.joblib", help="Model output path.")
    args = parser.parse_args()

    dataset = pd.read_csv(args.input)
    required_columns = {"text", "category"}
    missing = required_columns - set(dataset.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    x_train, x_test, y_train, y_test = train_test_split(
        dataset["text"],
        dataset["category"],
        test_size=0.25,
        random_state=42,
        stratify=dataset["category"] if dataset["category"].value_counts().min() > 1 else None,
    )

    model = build_pipeline()
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)

    print(classification_report(y_test, predictions, zero_division=0))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)
    print(f"Saved model to {output_path}")


if __name__ == "__main__":
    main()

