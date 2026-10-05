import os

dirs = [
    "backend/app/api",
    "backend/app/agents",
    "backend/app/db",
    "backend/app/models",
    "backend/app/services",
    "backend/app/schemas",
    "data/sample_tenders",
    "data/company_docs",
    "frontend"
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

print("Directories created.")
