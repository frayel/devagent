import datetime
import os

now = datetime.datetime.now()
filename = f"docs/runs/{now.strftime('%Y-%m-%d-%H%M')}.md"
os.makedirs("docs/runs", exist_ok=True)

report_content = """# Run Report

## Task
Identify and implement ONE small performance improvement that makes the application measurably faster or more efficient.

## Action
Added a database index `idx_ibovespa_cache_timestamp` on the `timestamp DESC` column in `ibovespa_cache` table to optimize the `ORDER BY timestamp DESC LIMIT 1` query in `get_latest_ibovespa_data()`.

## Result
Optimization implemented successfully. Tests pass, and no regression introduced.
"""

with open(filename, "w") as f:
    f.write(report_content)

print(f"Report created at {filename}")
