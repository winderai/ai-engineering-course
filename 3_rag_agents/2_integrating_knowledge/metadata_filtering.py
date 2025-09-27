
documents = [
    {
        "id": "doc_001",
        "content": "Q3 brewing production increased by 15%",
        "metadata": {
            "source": "quarterly_report",
            "date": "2024-10-01",
            "department": "production",
            "confidence": 0.95,
            "version": 2,
        },
    },
    {
        "id": "doc_002",
        "content": "New hop supplier contract signed",
        "metadata": {
            "source": "email",
            "date": "2024-10-15",
            "department": "procurement",
            "confidence": 1.0,
            "version": 1,
        },
    },
]


# Filter by metadata
def filter_docs(docs, **filters):
    filtered = []
    for doc in docs:
        match = True
        for key, value in filters.items():
            if doc["metadata"].get(key) != value:
                match = False
                break
        if match:
            filtered.append(doc)
    return filtered


# Find procurement documents
procurement_docs = filter_docs(documents, department="procurement")
print("Procurement documents:")
for doc in procurement_docs:
    print(f"  - {doc['content']}")

# Find recent documents (last 30 days)
recent_date = "2024-10-01"
recent_docs = [d for d in documents if d["metadata"]["date"] >= recent_date]
print(f"\nRecent documents (since {recent_date}):")
for doc in recent_docs:
    print(f"  - {doc['content']} (from {doc['metadata']['date']})")
