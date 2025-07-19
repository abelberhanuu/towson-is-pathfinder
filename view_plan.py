import pandas as pd

df = pd.read_excel("data/cis-degree-plan.xlsx", header=None)

start_row = 17
rows_per_semester = 4

semester_blocks = {
    "Fall 2023": (1, 4),
    "Spring 2024": (6, 9),
    "Fall 2024": (10, 13),
    "Spring 2025": (14, 16)
}

completed_courses = []

for semester, (start_col, end_col) in semester_blocks.items():
    block = df.iloc[start_row:start_row + rows_per_semester, start_col:end_col]

    print(f"\n📅 {semester}")
    print(f"Shape: {block.shape}")

    if block.shape[1] == 3:
        block.columns = ["Course", "Units", "Prerequisite"]
    elif block.shape[1] == 2:
        block.columns = ["Course", "Units"]
        print("⚠️ Column mismatch — fallback to 2 headers")
    else:
        block.columns = [f"Col{i}" for i in range(block.shape[1])]
        print("⚠️ Column mismatch — using fallback column names")

    # Filter out empty rows or totals
    filtered = block[~block["Course"].isin([None, "Total", 0, "0"]) & block["Course"].notna()]

    print(filtered)

    # Store course names only
    completed_courses.extend(filtered["Course"].dropna().tolist())

print("\n✅ Completed Courses:")
print(completed_courses)
