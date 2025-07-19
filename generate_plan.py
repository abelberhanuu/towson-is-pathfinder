import pandas as pd
from typing import List, Tuple, Dict, Set

# Sets of interchangeable courses that satisfy the same requirement
INTERCHANGEABLE_SETS: List[Set[str]] = [
    {"MATH211", "MATH273"},  # Calculus requirement
    {"MATH231", "MATH330"},  # Statistics requirement
    {"ART102", "ART103"},    # 2D Process for Interface Design
    {"CIS212", "COSC236"},   # Programming Intro (Systems)
]

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

    # helper to check prerequisites
    def met_prereqs(prereq_str: str, done: set) -> bool:
        if pd.isna(prereq_str) or prereq_str.strip() == '':
            return True
        prereq_list = []
        for part in prereq_str.replace(';', ',').split(','):
            part = part.strip()
            if part:
                prereq_list.append(part)
        return all(pr in done for pr in prereq_list)

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
            available = remaining[remaining['prerequisites'].apply(lambda x: met_prereqs(x, done_set))]
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
                more = remaining[remaining['prerequisites'].apply(lambda x: met_prereqs(x, done_set))]
                fits = False
                for u in more['units'].astype(int).tolist():
                    if credits + u <= max_credits:
                        fits = True
                        break
                if not fits:
                    break

        if sem_courses:
            plan.append({'semester': f'Semester {sem}', 'courses': sem_courses, 'credits': credits})
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
