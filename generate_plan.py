import pandas as pd
from typing import List, Tuple, Dict

def generate_plan(track: str, completed_courses: List[str], max_credits: int = 16) -> Tuple[List[Dict], List[Dict]]:
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

    completed = set(completed_courses)
    # remove completed courses
    df = df[~df['course_id'].isin(completed)].copy()

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
    scheduled = []
    done_set = set(completed_courses)

    for sem in range(1, 9):
        sem_courses = []
        credits = 0
        while True:
            # courses whose prereqs are met
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
                done_set.add(row['course_id'])
                remaining = remaining.drop(idx)
                placed = True
                break
            if not placed:
                break
            if credits >= max_credits:
                break
        if sem_courses:
            plan.append({'semester': f'Semester {sem}', 'courses': sem_courses, 'credits': credits})
        if remaining.empty:
            break
    unscheduled = remaining[['course_id', 'course_name', 'category']].to_dict('records')
    return plan, unscheduled
