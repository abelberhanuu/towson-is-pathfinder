import pandas as pd
from typing import List, Tuple, Dict, Set

# Labels for semester display
SEMESTER_LABELS = [
    "Fall 2023", "Spring 2024", "Fall 2024", "Spring 2025",
    "Fall 2025", "Spring 2026", "Fall 2026", "Spring 2027",
]

# Interchangeable course sets (only one needed)
INTERCHANGEABLE_SETS: List[Set[str]] = [
    {"MATH211", "MATH273"},  # Calculus
    {"MATH231", "MATH330"},  # Statistics
    {"ART102", "ART103"},    # 2D Art
    {"CIS212", "COSC236"},   # Intro to programming
]

def generate_plan(track: str, completed_courses: List[str], max_credits: int = 18) -> Tuple[List[Dict], List[Dict]]:
    df = pd.read_csv('data/towson_courses.csv')

    # Track filtering
    df = df[(df['track'] == 'All') | (df['track'] == track)].copy()

    done_set: Set[str] = set(completed_courses)

    # Fulfill interchangeable requirements
    for course_set in INTERCHANGEABLE_SETS:
        if done_set.intersection(course_set):
            done_set.update(course_set)

    # Remove completed/interchangeable courses
    df = df[~df['course_id'].isin(done_set)].copy()

    # Determine if prerequisites are met
    def met_prereqs(prereq_str: str, done: set) -> bool:
        if pd.isna(prereq_str) or prereq_str.strip() == '':
            return True
        prereq_list = []
        for part in prereq_str.replace(';', ',').split(','):
            part = part.strip()
            if part:
                prereq_list.append(part)
        return all(pr in done for pr in prereq_list)

    # Label courses
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
            available = remaining[remaining['prerequisites'].apply(lambda x: met_prereqs(x, done_set))]
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
                fits = any(
                    credits + int(u) <= max_credits
                    for u in remaining[remaining['prerequisites'].apply(lambda x: met_prereqs(x, done_set))]['units'].astype(int)
                )
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
    parser.add_argument("--max-credits", type=int, default=18, help="Maximum credits per semester")
    args = parser.parse_args()
    plan, unscheduled = generate_plan(args.track, args.completed, args.max_credits)
    print(json.dumps({"plan": plan, "unscheduled": unscheduled}, indent=2))
