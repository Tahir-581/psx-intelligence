"""ML announcement classifier with rule-based fallback."""

from __future__ import annotations

CATEGORIES = [
    "financial_results",
    "board_change",
    "dividend",
    "credit_rating",
    "insider_trade",
    "material_contract",
    "rights_issue",
    "agm_egm",
    "delisting",
    "show_cause",
    "corporate_action",
    "governance",
    "other",
]

RULES: list[tuple[str, str]] = [
    ("financial result", "financial_results"),
    ("quarterly", "financial_results"),
    ("board of director", "board_change"),
    ("appointment", "board_change"),
    ("resignation", "board_change"),
    ("cash dividend", "dividend"),
    ("interim dividend", "dividend"),
    ("credit rating", "credit_rating"),
    ("insider", "insider_trade"),
    ("director's interest", "insider_trade"),
    ("material contract", "material_contract"),
    ("rights issue", "rights_issue"),
    ("agm", "agm_egm"),
    ("egm", "agm_egm"),
    ("delisting", "delisting"),
    ("show cause", "show_cause"),
]


def classify_announcement(title: str, body: str | None = None) -> tuple[str, float]:
    text = f"{title} {body or ''}".lower()
    for phrase, category in RULES:
        if phrase in text:
            return category, 0.85
    try:
        return _ml_classify(text)
    except Exception:
        return "other", 0.5


def _ml_classify(text: str) -> tuple[str, float]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB

    train_texts = [phrase for phrase, _ in RULES] + ["general notice", "market update"]
    train_labels = [cat for _, cat in RULES] + ["other", "other"]
    vec = TfidfVectorizer(max_features=200)
    X = vec.fit_transform(train_texts)
    clf = MultinomialNB()
    clf.fit(X, train_labels)
    pred = clf.predict(vec.transform([text[:2000]]))[0]
    proba = max(clf.predict_proba(vec.transform([text[:2000]]))[0])
    return pred, float(proba)
