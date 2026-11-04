from pathlib import Path
import pandas as pd

csv_path = Path("data/jobs.csv")
workbook_path = Path("data/Job Application Tracker.xlsx")

jobs = pd.read_csv(csv_path)
job_tracker = pd.read_excel(
    workbook_path,
    sheet_name="Job Tracker",
    engine="openpyxl",
)

print(f"jobs.csv rows: {len(jobs)}")
print(f"Job Tracker rows: {len(job_tracker)}")

if len(jobs) == 0:
    raise SystemExit("jobs.csv contains no jobs.")

required_csv_columns = {
    "title",
    "company",
    "url",
    "status",
    "date_applied",
    "last_updated",
    "notes",
}

missing_csv = required_csv_columns - set(jobs.columns)
if missing_csv:
    raise SystemExit(
        f"jobs.csv is missing columns: {sorted(missing_csv)}"
    )

required_job_tracker_columns = {
    "Company Name",
    "Position/Title",
    "Job Posting URL",
    "Date Applied",
    "Current Status",
    "Notes",
}

missing_job_tracker = required_job_tracker_columns - set(job_tracker.columns)
if missing_job_tracker:
    raise SystemExit(
        "Excel Job_Tracker is missing columns: "
        f"{sorted(missing_job_tracker)}"
    )

print("Pipeline output validation passed.")
