from spendiq.db import execute_query
from spendiq.sql_tool import run_sql_tool
from spendiq.documents import DocumentStore
from spendiq.agent import SpendIQAgent

rows = execute_query("""
    SELECT vendor_name, category, preferred_status
    FROM vendors
    LIMIT 5
""")
print("Phase 1 Test Results:")
for row in rows:
    print(row)


## SQL Joins test

questions = [
    "What is our total spend with Stratos Cloud Services over the last 12 months?",
    "Who are our top 10 vendors by year-to-date spend?",
    "How many active contracts do we have, broken down by category?",
    "Which contracts auto-renew in the next 90 days?",
    "Which vendors have more than USD 50,000 in year-to-date spend but no active contract?",
    "Find invoices whose billed payment terms are shorter than the terms stated in the underlying contract.",
    "Flag contracts where cumulative invoice spend has exceeded the stated total contract value cap.",
]

print("Phase 2 Test Results:")
for question in questions:
    print("\n" + "=" * 100)
    print("QUESTION:", question)

    result = run_sql_tool(question)

    print("ANSWER:", result["answer"])
    print("SOURCES:", result["sources"])

    rows = result.get("rows", [])
    print("ROWS RETURNED:", len(rows))

    for row in rows[:5]:
        print(row)



## documents test


store = DocumentStore()
store.load_documents()
store.build_index()

query = "auto renewal terms and notice period"
results = store.search(query)

print("\nPhase 3 Test Results:\n")
for r in results:
    print("SOURCE:", r["source"])
    print("SCORE:", r["score"])
    print("TEXT:", r["text"][:300])
    print("-" * 80)

## agent test


from spendiq.agent import SpendIQAgent

agent = SpendIQAgent()

questions = [
    "What is total spend with Stratos Cloud Services over the last 12 months?",
    "What is the notice period for Stratos Cloud contract?",
    "Which contracts auto-renew in next 90 days and what are notice periods?",
    "Find invoices whose billed payment terms are shorter than the terms stated in the underlying contract.",
    "What does our procurement policy say about splitting purchase orders?",
]

for q in questions:
    print("\n" + "=" * 100)
    print("QUESTION:", q)

    result = agent.answer(q)

    print("\nANSWER:")
    print(result["answer"])

    print("\nTOOLS USED:")
    print(result["tools_used"])

    print("\nSOURCES:")
    print(result["sources"])