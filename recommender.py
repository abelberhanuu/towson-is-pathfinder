import pandas as pd

def recommend_courses(track, completed_courses):
    df = pd.read_csv('data/towson_courses.csv')

    # Convert completed list for quick lookup
    completed_set = set(completed_courses)

    # Filter out already completed courses
    df = df[~df['course_id'].isin(completed_set)]

    # Filter out courses whose prerequisites are NOT met
    def has_met_prereqs(prereq_str):
        if pd.isna(prereq_str) or prereq_str.strip() == "":
            return True
        prereqs = [pr.strip() for pr in prereq_str.split(',')]
        return all(pr in completed_set for pr in prereqs)

    df = df[df['prerequisites'].apply(has_met_prereqs)]

    # Score each course based on relevance
    def score_course(row):
        score = 0
        if row['core_required'] == 'yes':
            score += 3
        if row['track'] == track:
            score += 2
        if row['elective'] == 'yes':
            score += 1
        return score

    df['score'] = df.apply(score_course, axis=1)

    # Return top recommendations (sorted by score then course ID)
    recommendations = df.sort_values(by=['score', 'course_id'], ascending=[False, True])
    return recommendations[['course_id', 'course_name', 'score']].to_dict(orient='records')
