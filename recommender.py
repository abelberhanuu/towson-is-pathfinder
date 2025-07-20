from __future__ import annotations

import pandas as pd

from utils import load_courses, parse_prereqs


def recommend_courses(track: str, completed_courses: list[str]):
    """Return recommended and locked courses for the given track."""
    df = load_courses()

    # Convert completed list for quick lookup
    completed_set = set(completed_courses)

    # Filter out already completed courses
    df = df[~df["course_id"].isin(completed_set)]

    locked: list[dict] = []
    available_rows = []

    for _, row in df.iterrows():
        prereqs = parse_prereqs(row["prerequisites"])
        unmet = [p for p in prereqs if p not in completed_set]
        if unmet:
            locked.append({"course_id": row["course_id"], "missing": unmet})
        else:
            available_rows.append(row)

    if available_rows:
        df = pd.DataFrame(available_rows)
    else:
        df = pd.DataFrame(columns=df.columns)

    # Score each course based on relevance
    def score_course(row):
        score = 0
        if row["core_required"] == "yes":
            score += 3
        if row["track"] == track:
            score += 2
        if row["elective"] == "yes":
            score += 1
        return score

    df["score"] = df.apply(score_course, axis=1)

    # Return top recommendations (sorted by score then course ID)
    recommendations = df.sort_values(by=["score", "course_id"], ascending=[False, True])
    recs = recommendations[["course_id", "course_name", "score"]].to_dict(
        orient="records"
    )
    return recs, locked
