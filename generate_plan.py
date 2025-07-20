from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Set, Tuple

import pandas as pd
from utils import load_courses, parse_prereqs


def generate_semester_labels() -> List[str]:
    current_year = datetime.now().year
    start_season = "Spring" if datetime.now().month <= 6 else "Fall"
    season = start_season
    year = current_year
    labels = []
    for _ in range(8):
        labels.append(f"{season} {year}")
        if season == "Fall":
            season = "Spring"
            year += 1
        else:
            season = "Fall"
    return labels


SEMESTER_LABELS = generate_semester_labels()

INTERCHANGEABLE_SETS: List[Set[str]] = [
    {"MATH211", "MATH273"},
    {"MATH231", "MATH330"},
    {"ART102", "ART103"},
    {"CIS212", "COSC236"},
]


def generate_plan(
    track: str, completed_courses: List[str], max_credits: int = 18
) -> Tuple[List[Dict], List[Dict]]:
    df = load_courses()
    df = df[(df["track"] == "All") | (df["track"] == track)].copy()

    done_set: Set[str] = set(completed_courses)
    for course_set in INTERCHANGEABLE_SETS:
        if done_set.intersection(course_set):
            done_set.update(course_set)

    df = df[~df["course_id"].isin(done_set)].copy()

    def met_prereqs(course_id: str) -> bool:
        row = df[df["course_id"] == course_id].iloc[0]
        prereqs = parse_prereqs(row.get("prerequisites", ""))
        return all(pr in done_set for pr in prereqs)

    def label(row: pd.Series) -> str:
        if row["core_required"] == "yes" and row["track"] == "All":
            return "Core"
        if row["core_required"] == "yes" and row["track"] == track:
            return "Track Core"
        if row["elective"] == "yes" and row["track"] == track:
            return "Track Elective"
        if row["elective"] == "yes":
            return "Elective"
        return "Other"

    df["category"] = df.apply(label, axis=1)
    df["priority"] = df["category"].map(
        {"Core": 0, "Track Core": 1, "Track Elective": 2, "Elective": 3, "Other": 4}
    )

    plan = []
    remaining = df.copy()

    for sem in range(8):
        sem_courses = []
        credits = 0

        while credits < max_credits:
            available = remaining[remaining["course_id"].apply(met_prereqs)]
            if available.empty:
                break

            available = available.sort_values(by=["priority", "course_id"])
            placed = False

            for idx, row in available.iterrows():
                units = int(row["units"])
                if credits + units > max_credits:
                    continue

                sem_courses.append(
                    {
                        "course_id": row["course_id"],
                        "course_name": row["course_name"],
                        "units": units,
                        "category": row["category"],
                        "prerequisites": parse_prereqs(row.get("prerequisites", "")),
                    }
                )
                credits += units
                course_id = row["course_id"]
                done_set.add(course_id)

                for cset in INTERCHANGEABLE_SETS:
                    if course_id in cset:
                        done_set.update(cset)
                        remaining = remaining[~remaining["course_id"].isin(cset)]
                        break
                else:
                    remaining = remaining.drop(idx)

                placed = True
                break

            if not placed:
                break

            if credits >= 15:
                more = remaining[remaining["course_id"].apply(met_prereqs)]
                fits = any(
                    credits + int(u) <= max_credits
                    for u in more["units"].astype(int).tolist()
                )
                if not fits:
                    break

        if sem_courses:
            label = SEMESTER_LABELS[sem]
            plan.append({"semester": label, "courses": sem_courses, "credits": credits})
        if remaining.empty:
            break

    remaining = remaining.copy()
    remaining["prerequisites"] = remaining["prerequisites"].apply(parse_prereqs)
    unscheduled = remaining[
        ["course_id", "course_name", "category", "prerequisites"]
    ].to_dict("records")
    return plan, unscheduled


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Generate 4-year plan")
    parser.add_argument("--track", required=True, help="Selected track")
    parser.add_argument(
        "--completed", nargs="*", default=[], help="Completed course IDs"
    )
    parser.add_argument(
        "--max-credits", type=int, default=18, help="Maximum credits per semester"
    )
    args = parser.parse_args()

    plan, unscheduled = generate_plan(args.track, args.completed, args.max_credits)
    print(json.dumps({"plan": plan, "unscheduled": unscheduled}, indent=2))
