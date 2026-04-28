<!-- # SpendIQ: Candidate Package

Welcome, and thanks for taking on the SpendIQ challenge. Everything you need is in this folder.

## Start here

1. **`CANDIDATE_BRIEF.pdf`** (or `CANDIDATE_BRIEF.md`). Read this first. Scenario, goals, sample questions, ground rules, and the 2-hour milestone plan.
2. **`DATA_DICTIONARY.md`**. Schema and field reference. Keep this open while you build your ingestion.

## Data

- `data/*.csv`. Five structured files (departments, vendors, contracts, purchase_orders, invoices).
- `docs/contracts/`. 15 contract documents; 12 are Markdown, 3 are PDF. Your ingestion should handle both.
- `docs/policies/`. 3 policy documents (procurement, AP/expense, vendor risk).

**Reference date:** the dataset is anchored so that "today" is **2026-04-21**. Use this when interpreting questions like *"contracts expiring in the next 90 days"*.

## Ground rules (summary; see the brief for details)

- 2 hours, self-paced. Use the full window.
- AI coding assistants encouraged (Claude Code, Codex, Cursor, etc.). Be prepared to talk through where they helped and where they went wrong.
- Recommended stack: Python backend, Postgres (with `pgvector` if you want), Next.js / React frontend. Not enforced; use what you know.
- LLM provider: your choice, bring your own key. We can provide a short-lived Anthropic or OpenAI key at the interview if needed.
- Submit whatever you have at the 2-hour mark, even if partial. Clear thinking plus partial implementation beats a polished demo with weak design choices.

## Interview format

The interview is remote, over **Microsoft Teams** with screen share. You will run your app on your own machine and demo it live. Have everything pre-started 5 minutes before the call.

## What to submit

A zip (or private Git link) with:

- Your code
- Reproducible ingestion and run instructions in a project `README.md`
- A short `DESIGN_NOTES.md` covering architecture, key decisions, limitations, and what you would do with more time

Good luck, and have fun with it.

 -->

# 💸 SpendIQ Copilot

SpendIQ is a finance and procurement copilot that answers business questions across structured data (vendors, contracts, invoices) and unstructured documents (contracts, policies) using a hybrid AI + data approach.

---

## 🚀 Overview

SpendIQ enables users to ask natural language questions such as:

- What is our total spend with Stratos Cloud Services?
- Which contracts auto-renew in the next 90 days?
- What is the notice period for a contract?
- Are any invoices violating contract payment terms?
- What does our procurement policy say about splitting purchase orders?

The system intelligently routes each question to the appropriate data source and returns **grounded, explainable answers**.

---

## 🧠 System Architecture

```

User Question
↓
Streamlit UI
↓
SpendIQ Agent
↓
Tool Routing
├── SQL Tool (structured data)
├── Document Retrieval Tool (contracts & policies)
└── Ollama (LLM synthesis layer)
↓
Final Answer + Tools Used + Sources

```

### Design Principles

- **SQL is the source of truth** for numerical and structured queries  
- **Documents provide context** for clauses and policies  
- **LLM is used only for synthesis**, not decision-making  
- **No hallucination** by enforcing strict grounding rules  

---

## 📁 Project Structure

```

SpendIQ/
├── app.py                  # Streamlit UI
├── requirements.txt
├── README.md
├── spendiq/
│   ├── config.py          # Paths, constants, reference date
│   ├── db.py              # SQLite connection helpers
│   ├── ingest.py          # Load CSVs into SQLite
│   ├── sql_tool.py        # Deterministic SQL queries
│   ├── documents.py       # Document parsing + retrieval (TF-IDF)
│   ├── llm.py             # Ollama integration
│   └── agent.py           # Core orchestration logic
├── data/                  # CSV datasets
└── docs/                  # Contracts & policy documents

````

---

## ⚙️ Setup

### 1. Create environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
````

---

### 2. Load data into SQLite

```bash
python3 -m spendiq.ingest
```

This will:

* Load CSVs into SQLite
* Normalize columns
* Verify table row counts

---

### 3. Start Ollama (optional but recommended)

```bash
ollama serve
```

Make sure you have:

```bash
ollama list
```

Example:

```
llama3.2:3b
```

---

### 4. Run the UI

```bash
streamlit run app.py
```

Open:

```
http://localhost:8501
```

---

## 🔍 How It Works

### 1. Structured Data (SQL Tool)

Handled via deterministic SQL queries:

* Spend calculations → invoices table
* Vendor insights → vendors table
* Contract terms → contracts table
* Compliance checks → joins across tables

👉 Ensures accuracy and avoids hallucination.

---

### 2. Document Retrieval

* Loads Markdown and PDF documents
* Splits into chunks
* Uses TF-IDF + cosine similarity
* Returns top relevant snippets

👉 Used for:

* notice periods
* termination clauses
* policy rules

---

### 3. Agent Logic

The agent decides:

* SQL only → return directly
* Document only → use retrieval + LLM
* Hybrid → combine SQL + documents
* Special routing for:

  * notice periods
  * payment terms

👉 Prevents incorrect reasoning and ensures reliability.

---

### 4. LLM (Ollama)

Used only for:

* summarizing document evidence
* answering policy questions
* generating natural language responses

NOT used for:

* SQL generation
* numerical reasoning

---

## 📊 Example Queries

### SQL

```
What is total spend with Stratos Cloud Services?
```

### Document

```
What is the notice period for Stratos Cloud contract?
```

### Hybrid

```
Which contracts auto-renew in next 90 days and what are notice periods?
```

### Policy

```
What does procurement policy say about splitting purchase orders?
```

---

## 🧪 Key Features

* Deterministic SQL for accuracy
* Document retrieval with explainable scores
* Hybrid reasoning across data sources
* LLM guardrails to prevent hallucination
* Source transparency (SQL tables + document paths)
* Simple UI for interactive querying

---

## ⚠️ Limitations

* TF-IDF retrieval (not semantic embeddings)
* SQLite (not production-grade database)
* No caching or query optimization
* Limited query classification

---

## 🚀 Future Improvements

* Replace TF-IDF with embedding-based retrieval
* Add schema-aware text-to-SQL
* Use Postgres + pgvector
* Add caching and observability
* Improve query routing with ML
* Add evaluation framework for accuracy

---

## 🎯 Key Design Decision

> Structured data is always treated as the source of truth.
> The LLM is only used for grounded synthesis, not for reasoning over numbers.

---

## 👨‍💻 Author

Gowtham Pentela
AI / ML Engineer

---

## 🏁 Summary

SpendIQ demonstrates how to build a **reliable, explainable AI system** that combines:

* structured data (SQL)
* unstructured data (documents)
* controlled LLM usage

without relying on black-box reasoning.

```

