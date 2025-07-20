import pandas as pd
import re
from functools import lru_cache


@lru_cache(maxsize=1)
def load_courses() -> pd.DataFrame:
    """Load course catalog from CSV."""
    df = pd.read_csv("data/towson_courses.csv")
    return df


def parse_prereqs(prereq_str: str) -> list[str]:
    """Return list of prerequisite course IDs."""
    if pd.isna(prereq_str) or prereq_str == "":
        return []
    parts = re.split(r"[;,]", prereq_str)
    return [p.strip() for p in parts if p.strip()]
