import csv
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sql_file = root / "hive" / "analysis_queries.sql"
output_dir = root / "hive" / "output"

filenames = [
    "revenue_by_category.csv",
    "monthly_sales.csv",
    "top_10_customers.csv",
    "best_selling_products.csv",
    "payment_method_analysis.csv",
    "overall_sales_kpis.csv",
    "category_sales.csv",
    "top_products_by_revenue.csv",
    "quantity_sold_by_product.csv",
    "discount_analysis.csv",
    "customer_purchase_frequency.csv",
    "repeat_customers.csv",
    "regional_distribution.csv",
    "region_wise_revenue.csv",
    "payment_preferences.csv",
]

sql = sql_file.read_text(encoding="utf-8")
sql = re.sub(r"--.*", "", sql)
statements = [
    statement.strip()
    for statement in sql.split(";")
    if statement.strip() and not statement.strip().upper().startswith("USE ")
]

if len(statements) != 15:
    sys.exit(f"Expected 15 queries, found {len(statements)}. No files changed.")

temporary_files = []

for index, (query, filename) in enumerate(zip(statements, filenames), 1):
    result = subprocess.run(
        [
            "beeline",
            "-u", "jdbc:hive2://localhost:10000/retail_db",
            "-n", "meghana_b_m",
            "--hiveconf", "hive.execution.engine=mr",
            "--silent=true",
            "--showHeader=true",
            "--outputformat=csv2",
            "-e", query,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        sys.exit(f"Query {index} failed. No existing CSV files were replaced.\n{result.stderr}")

    lines = result.stdout.splitlines()
    header_index = next(
        (
            i for i, line in enumerate(lines)
            if "," in line and not line.startswith(("2026-", "SLF4J:", "WARNING:", "INFO "))
            and not line.startswith("WARN ")
        ),
        None,
    )

    if header_index is None:
        sys.exit(f"Could not locate CSV header for query {index}. No existing CSV files were replaced.")

    csv_text = "\n".join(lines[header_index:]).strip() + "\n"

    try:
        rows = list(csv.reader(csv_text.splitlines()))
        if len(rows) < 2 or any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("Invalid or empty CSV result")
    except Exception as error:
        sys.exit(f"CSV validation failed for query {index}: {error}. No existing CSV files were replaced.")

    temp_path = output_dir / (filename + ".tmp")
    temp_path.write_text(csv_text, encoding="utf-8")
    temporary_files.append((temp_path, output_dir / filename))
    print(f"Validated {index}/15: {filename} ({len(rows) - 1} rows)")

for temp_path, final_path in temporary_files:
    temp_path.replace(final_path)

print("\nAll 15 CSV files exported and validated successfully.")
