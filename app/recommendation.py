# app/recommendation.py
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def recommendation_system(df):
    """Return dictionary of recommended pages based on similarity."""
    if df.empty:
        return {}   # no data → no recommendations

    if "PagePath" not in df.columns or df["PagePath"].empty:
        return {}

    content_mapping = {category: idx for idx, category in enumerate(df["PagePath"].unique())}
    df["Page_Encoded"] = df["PagePath"].map(content_mapping)

    # If fewer than 2 pages, we can’t compute similarity
    if df["Page_Encoded"].nunique() < 2:
        return {}

    # Cosine similarity
    similarity_matrix = cosine_similarity(df[["Page_Encoded"]])

    recommendations = {}
    for i in range(len(df)):
        similar_pages = np.argsort(-similarity_matrix[i])[1:4]  # top 3
        recommendations[df.loc[i, "PagePath"]] = df.loc[similar_pages, "PagePath"].values.tolist()

    return recommendations


def recommend_events(events):
    if not events:
        return []

    # Simple recommendation: events with best like/dislike ratio
    scored = []
    for e in events:
        total = e["likes"] + e["dislikes"]
        score = e["likes"] / total if total > 0 else 0
        scored.append((score, e))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [e for _, e in scored[:5]]  # top 5 events