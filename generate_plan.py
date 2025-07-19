import pandas as pd
from typing import List, Tuple, Dict, Set

# Labels used when returning the semester-by-semester plan
SEMESTER_LABELS = [
    "Fall 2023",
    "Spring 2024",
    "Fall 2024",
    "Spring 2025",
    "Fall 2025",
    "Spring 2026",
    "Fall 2026",
    "Spring 2027",
]

# Sets of interchangeable courses that satisfy the same requirement
INTERCHANGEABLE_SETS: List[Set[str]] = [
    {"MATH211", "MATH273"},  # Calculus requirement
    {"MATH231", "MATH330"},  # Statistics requirement
    {"ART102", "ART103"},    # 2D Process for Interface Design
    {"CIS212", "COSC236"},   # Programming Intro (Systems)
]

# Mapping of prerequisites by course ID for consistent lookup
PREREQ_MAP: Dict[str, List[str]] = {
    # Global core requirements
    "COSC236": ["COSC175"],
    "COSC237": ["COSC236"],
    "CIS239": ["CIS211"],
    "CIS350": [],
    "CIS377": [],
    "CIS379": ["COSC237"],
    "CIS435": [],
    "CIS458": ["CIS239"],
    "CIS479": ["CIS379"],
    "CIS475": ["CIS479", "CIS458"],
    "ENGL317": ["ENGL102"],
    "COSC418": ["ENGL102"],

    # Data Analytics track
    "CIS328": ["CIS211"],
    "CIS334": ["CIS379"],
    "CIS428": ["CIS328", "CIS334"],  # simplified AND requirement
    "CIS468": ["MATH231", "CIS334"],
    "ITEC336": [],
    "COSC336": ["COSC237"],
    # Track electives
    "CIS265": [],
    "CIS397": ["CIS334"],
    "CIS426": ["CIS328"],
    "CIS436": ["CIS379"],
    "ITEC427": ["ITEC231"],

    # Systems track
    "COSC412": ["COSC336"],
    "COSC436": ["COSC336"],
    "COSC484": ["COSC336"],
    "CIS212": [],
    "CIS425": ["CIS379", "MATH231"],
    "CIS440": ["CIS379"],
    "CIS495": [],
    "ITEC345": ["COSC236", "MATH263"],
    "ITEC423": ["ITEC231"],

    # Interface design
    "ART102": [],
    "ART103": [],
    "ART217": ["ART103"],
    "ART322": ["ART217"],

    # Business track
    "ACCT201": [],
    "ECON201": [],
    "ECON203": [],
    "ECON205": ["ECON201"],
    "LEGL225": [],
    "MKTG341": ["ECON201"],
    "MNGT361": ["ECON201"],
    "FIN331": ["ACCT201", "ECON205"],

    # Additional business electives
    "ACCT202": ["ACCT201"],
    "ACCT301": ["ACCT202"],
    "ACCT341": ["ACCT202"],
    "EBTM419": ["EBTM365"],
    "EBTM454": ["EBTM365"],
    "HCMN305": ["HLTH207"],
    "MNGT395": ["MNGT361"],
    "ITEC433": [],
}


def generate_plan(track: str, completed_courses: List[str], max_credits: int = 18) -> Tuple[List[Dict], List[Dict]]:
    """Generate a semester-by-semester plan.

    Parameters
    ----------
    track: str
        Selected track (Business, Data Analytics, Interface Design, Systems)
    completed_courses: list of course IDs already taken
    max_credits: maximum credits allowed per semester

    Returns
    -------
    plan: list of dictionaries for each semester
    remaining: list of unscheduled courses (if any)
    """
    df = pd.read_csv('data/towson_courses.csv')

    # Filter to only courses relevant to the selected track
    df = df[(df['track'] == 'All') | (df['track'] == track)].copy()

    done_set: Set[str] = set(completed_courses)

    # Mark all courses within an interchangeable set as done if any are completed
    for course_set in INTERCHANGEABLE_SETS:
        if done_set.intersection(course_set):
            done_set.update(course_set)

    # Remove completed courses from the dataframe
    df = df[~df['course_id'].isin(done_set)].copy()

    # helper to check prerequisites using only the explicit map
    def met_prereqs(course_id: str, done: Set[str]) -> bool:
        prereqs = PREREQ_MAP.get(course_id, [])
        return all(pr in done for pr in prereqs)

    # label course category
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
    priority_order = {'Core': 0, 'Track Core': 1, 'Track Elective': 2, 'Elective': 3, 'Other': 4}
    df['priority'] = df['category'].map(priority_order)

    plan = []
    remaining = df.copy()

    for sem in range(1, 9):
        sem_courses = []
        credits = 0
        while credits < max_credits:
            # courses whose prerequisites are met
            available = remaining[remaining.apply(lambda r: met_prereqs(r['course_id'], done_set), axis=1)]
            if available.empty:
                break

            # sort by priority then course id for stability
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

                # If this course belongs to an interchangeable set, mark others as done
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

            # stop if we've hit minimum target credits and nothing else fits
            if credits >= 15:
                # check if any course can still fit without exceeding max
                more = remaining[remaining.apply(lambda r: met_prereqs(r['course_id'], done_set), axis=1)]
                fits = False
                for u in more['units'].astype(int).tolist():
                    if credits + u <= max_credits:
                        fits = True
                        break
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
