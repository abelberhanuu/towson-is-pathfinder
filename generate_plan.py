import pandas as pd
from typing import List, Tuple, Dict, Set

# Semester labels for each term
SEMESTER_LABELS = [
    "Fall 2023", "Spring 2024", "Fall 2024", "Spring 2025",
    "Fall 2025", "Spring 2026", "Fall 2026", "Spring 2027",
]

# Sets of interchangeable courses that satisfy the same requirement
INTERCHANGEABLE_SETS: List[Set[str]] = [
    {"MATH211", "MATH273"},  # Calculus requirement
    {"MATH231", "MATH330"},  # Statistics requirement
    {"ART102", "ART103"},    # 2D Process for Interface Design
    {"CIS212", "COSC236"},   # Programming Intro (Systems)
]

# Explicit prerequisite mapping by course ID
PREREQ_MAP: Dict[str, List[str]] = {
    "COSC236": ["COSC175"],
    "COSC237": ["COSC236"],
    "CIS239": ["CIS211"],
    "CIS379": ["CIS211"],
    "CIS458": ["CIS379"],
    "CIS479": ["CIS379"],
    "CIS475": ["CIS479", "CIS458"],
    "COSC418": ["ENGL102"],
    "ENGL317": ["ENGL102"],
    "CIS334": ["CIS379"],
    "CIS328": ["CIS211"],
    "CIS428": ["CIS328", "CIS334"],
    "CIS468": ["MATH231", "CIS334"],
    "CIS436": ["CIS379"],
    "ART217": ["ART103"],
    "COSC336": ["COSC237"],
    "COSC412": ["COSC336"],
    "COSC436": ["COSC336"],
    "COSC484": ["COSC336"],
    "ACCT202": ["ACCT201"],
    "ACCT301": ["ACCT202"],
    "ACCT341": ["ACCT202"],
    "EBTM419": ["EBTM365"],
    "EBTM454": ["EBTM365"],
    "HCMN305": ["HLTH207"],
    "MNGT395": ["MNGT361"],
    "ITEC427": ["ITEC231"],
    "ITEC345": ["COSC236", "MATH263"],
    "ITEC423": ["ITEC231"],
}


def generate_plan(track: str, completed_courses: List[str], max_credits: int = 18) -> Tuple[List[Dict], List[Dict]]:
    df = pd.read_csv('data/towson_courses.csv')
    df = df[(df['track'] == 'All') | (df['track'] == track)].copy()

    done_set: Set[str] = set(completed_courses)

    for course_set in INTERCHANGEABLE_SETS:
        if done_set.intersection(course_set):
            done_set.update(course_set)

    df = df[~df['course_id'].isin(done_set)].copy()

    def met_prereqs(course_id: str, prereq_str: str, done: set) -> bool:
        prereqs = PREREQ_MAP.get(course_id)
        if prereqs is None:
            if pd.isna(prereq_str) or prereq_str.strip() == '':
                prereqs = []
            else:
                prereqs = [p.strip() for p in prereq_str.replace(';', ',').split(',') if p.strip()]
        return all(pr in done for pr in prereqs)

    def label(row: pd.Series) -> str:
        if row['core_required'] == 'yes' and row['track'] == 'All':
            return 'Core'
        if row['core_required'] == 'yes' and row['track'] == track:
            return 'Track Core'
        if row['elective'] == 'yes' and row['track'] == track:
            return 'Track Elective'
        if row['elective'] == 'yes':
            return 'Elective'
        return 'Other'

    df['category'] = df.apply(label, axis=1)
    df['priority'] = df['category'].map({
        'Core': 0, 'Track Core': 1, 'Track Elective': 2, 'Elective': 3, 'Other': 4
    })

    plan = []
    remaining = df.copy()

    for sem in range(1, 9):
        sem_courses = []
        credits = 0

        while credits < max_credits:
            available = remaining[remaining.apply(lambda r: met_prereqs(r['course_id'], r['prerequisites'], done_set), axis=1)]
            if available.empty:
                break

            available = available.sort_values(by=['priority', 'course_id'])
            placed = False

            for idx, row in available.iterrows():
                units = int(row['units'])
                if credits + units > max_credits:
                    continue

                sem_courses.append({
                    'course_id': row['course_id'],
                    'course_name': row['course_name'],
                    'units': units,
                    'category': row['category']
                })
                credits += units
                course_id = row['course_id']
                done_set.add(course_id)

                for cset in INTERCHANGEABLE_SETS:
                    if course_id in cset:
                        done_set.update(cset)
                        remaining = remaining[~remaining['course_id'].isin(cset)]
                        break
                else:
                    remaining = remaining.drop(idx)

                placed = True
                break

            if not placed:
                break

            if credits >= 15:
                more = remaining[remaining.apply(lambda r: met_prereqs(r['course_id'], r['prerequisites'], done_set), axis=1)]
                fits = any(credits + int(u) <= max_credits for u in more['units'].astype(int).tolist())
                if not fits:
                    break

        if sem_courses:
            label = SEMESTER_LABELS[sem - 1] if sem - 1 < len(SEMESTER_LABELS) else f"Semester {sem}"
            plan.append({'semester': label, 'courses': sem_courses, 'credits': credits})

        if remaining.empty:
            break

    unscheduled = remaining[['course_id', 'course_name', 'category']].to_dict('records')
    return plan, unscheduled


if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser(description="Generate 4-year plan")
    parser.add_argument("--track", required=True, help="Selected track")
    parser.add_argument("--completed", nargs="*", default=[], help="Completed course IDs")
    parser.add_argument("--max-credits", type=int, default=18, dest="max_credits", help="Maximum credits per semester")
    args = parser.parse_args()

    plan, unscheduled = generate_plan(args.track, args.completed, args.max_credits)
    print(json.dumps({"plan": plan, "unscheduled": unscheduled}, indent=2))
