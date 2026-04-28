from __future__ import annotations

from typing import Any

from spendiq.documents import DocumentStore
from spendiq.llm import ollama_generate
from spendiq.sql_tool import run_sql_tool


class SpendIQAgent:
    def __init__(self):
        self.doc_store = DocumentStore()
        self.doc_store.load_documents()
        self.doc_store.build_index()

    def _needs_documents(self, question: str) -> bool:
        q = question.lower()
        keywords = [
            "contract",
            "policy",
            "clause",
            "notice",
            "renewal",
            "auto-renew",
            "auto renew",
            "terms",
            "exit",
            "splitting",
            "split purchase",
            "threshold",
        ]
        return any(keyword in q for keyword in keywords)

    def _build_context(
        self,
        sql_result: dict[str, Any],
        doc_results: list[dict[str, Any]],
    ) -> str:
        context_parts = []

        rows = sql_result.get("rows", [])
        if rows:
            context_parts.append("STRUCTURED DATA RESULTS:")
            for i, row in enumerate(rows[:10], start=1):
                clean_row = ", ".join(f"{k}: {v}" for k, v in row.items())
                context_parts.append(f"{i}. {clean_row}")

        if doc_results:
            context_parts.append("\nDOCUMENT RESULTS:")
            for i, doc in enumerate(doc_results[:5], start=1):
                context_parts.append(
                    f"{i}. Source: {doc['source']}\n"
                    f"Score: {doc['score']:.4f}\n"
                    f"Text: {doc['text'][:1200]}"
                )

        return "\n".join(context_parts)

    def _synthesize_answer(
        self,
        question: str,
        sql_result: dict[str, Any],
        doc_results: list[dict[str, Any]],
    ) -> str:
        context = self._build_context(sql_result, doc_results)

        if not context.strip():
            return (
                "I could not find enough structured or document evidence to answer this question. "
                "Try asking about vendor spend, active contracts, invoices, payment terms, renewal clauses, or procurement policy."
            )

        prompt = f"""
You are SpendIQ, a finance and procurement copilot.

You MUST follow these rules:
1. Use ONLY the provided evidence.
2. DO NOT assume anything not explicitly shown.
3. DO NOT contradict the structured data.
4. If structured data already answers the question, DO NOT reinterpret it.
5. If unsure, say "insufficient evidence".

User question:
{question}

Evidence:
{context}

Instructions:
- If a clear value exists (like notice period), state it directly first.
- Then optionally add supporting clause.
- Only use document text to add supporting details like clauses or notice periods.
- Be precise.
- Do not guess.
- End with a short "Sources used" section.

Answer:
"""
        return ollama_generate(prompt)

    def _filter_docs_by_structured_context(
        self,
        sql_result: dict[str, Any],
        doc_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not doc_results:
            return []

        rows = sql_result.get("rows", [])
        if not rows:
            return doc_results

        contract_ids = {
            str(row.get("contract_id"))
            for row in rows
            if row.get("contract_id")
        }

        vendor_tokens = set()
        for row in rows:
            vendor_name = row.get("vendor_name")
            if vendor_name:
                for token in str(vendor_name).lower().replace("-", " ").split():
                    if len(token) >= 4:
                        vendor_tokens.add(token)

        filtered_docs = []
        for doc in doc_results:
            source = doc.get("source", "").lower()
            text = doc.get("text", "").lower()

            contract_match = any(
                contract_id.lower() in source or contract_id.lower() in text
                for contract_id in contract_ids
            )

            vendor_match = any(
                token in source or token in text
                for token in vendor_tokens
            )

            if contract_match or vendor_match:
                filtered_docs.append(doc)

        return filtered_docs if filtered_docs else doc_results

    def _format_hybrid_answer(self, sql_result: dict[str, Any]) -> str:
        rows = sql_result.get("rows", [])

        notice_summary = []
        for row in rows[:10]:
            contract = row.get("contract_id")
            vendor = row.get("vendor_name")
            notice = row.get("notice_period_days")
            end_date = row.get("end_date")

            if contract and vendor and notice:
                if end_date:
                    notice_summary.append(
                        f"- {contract} ({vendor}) ends on {end_date} -> {notice} days notice"
                    )
                else:
                    notice_summary.append(
                        f"- {contract} ({vendor}) -> {notice} days notice"
                    )

        if notice_summary:
            return (
                sql_result["answer"]
                + "\n\nNotice periods from structured contract data:\n"
                + "\n".join(notice_summary)
                + "\n\nSupporting contract/policy context is shown below."
            )

        return (
            sql_result["answer"]
            + "\n\nSupporting contract/policy context is shown below."
        )

    def _format_notice_period_answer(self, sql_result: dict[str, Any]) -> str | None:
        rows = sql_result.get("rows", [])

        notice_lines = []
        for row in rows:
            contract = row.get("contract_id")
            vendor = row.get("vendor_name")
            notice = row.get("notice_period_days")
            end_date = row.get("end_date")

            if contract and vendor and notice:
                if end_date:
                    notice_lines.append(
                        f"- {contract} ({vendor}) ends on {end_date} -> {notice} days notice"
                    )
                else:
                    notice_lines.append(
                        f"- {contract} ({vendor}) -> {notice} days notice"
                    )

        if not notice_lines:
            return None

        return "Notice periods from structured contract data:\n" + "\n".join(notice_lines)

    def answer(self, question: str) -> dict[str, Any]:
        q = question.lower()

        sql_result = run_sql_tool(question)

        # SPECIAL CASE: notice period questions should prefer structured contract data.
        # This prevents retrieval from mixing similar but incorrect contract documents.
        if "notice period" in q or ("notice" in q and "contract" in q):
            notice_answer = self._format_notice_period_answer(sql_result)

            if notice_answer:
                return {
                    "answer": notice_answer,
                    "tools_used": ["SQL Tool"],
                    "sql_rows": sql_result.get("rows", []),
                    "doc_snippets": [],
                    "sources": {
                        "sql_sources": sql_result.get("sources", []),
                        "document_sources": [],
                    },
                }

        doc_results = []
        if self._needs_documents(question) or not sql_result.get("rows"):
            doc_results = self.doc_store.search(question, top_k=5)

        doc_results = self._filter_docs_by_structured_context(
            sql_result=sql_result,
            doc_results=doc_results,
        )

        # CASE 1: Pure SQL answer. Do not use the LLM.
        if sql_result.get("rows") and not doc_results:
            return {
                "answer": sql_result["answer"],
                "tools_used": ["SQL Tool"],
                "sql_rows": sql_result.get("rows", []),
                "doc_snippets": [],
                "sources": {
                    "sql_sources": sql_result.get("sources", []),
                    "document_sources": [],
                },
            }

        # CASE 2: SQL already answers payment-term mismatch questions.
        if sql_result.get("rows") and "payment terms" in q:
            return {
                "answer": sql_result["answer"],
                "tools_used": ["SQL Tool"],
                "sql_rows": sql_result.get("rows", []),
                "doc_snippets": [],
                "sources": {
                    "sql_sources": sql_result.get("sources", []),
                    "document_sources": [],
                },
            }

        # CASE 3: Hybrid question.
        if sql_result.get("rows") and doc_results:
            return {
                "answer": self._format_hybrid_answer(sql_result),
                "tools_used": ["SQL Tool", "Document Retrieval Tool"],
                "sql_rows": sql_result.get("rows", []),
                "doc_snippets": doc_results[:5],
                "sources": {
                    "sql_sources": sql_result.get("sources", []),
                    "document_sources": list({doc["source"] for doc in doc_results}),
                },
            }

        # CASE 4: Document-only question.
        if doc_results:
            final_answer = self._synthesize_answer(
                question=question,
                sql_result={"rows": []},
                doc_results=doc_results,
            )

            return {
                "answer": final_answer,
                "tools_used": ["Document Retrieval Tool", "Ollama Synthesis Layer"],
                "sql_rows": [],
                "doc_snippets": doc_results[:5],
                "sources": {
                    "sql_sources": [],
                    "document_sources": list({doc["source"] for doc in doc_results}),
                },
            }

        return {
            "answer": (
                "I could not confidently answer this question with the available tools. "
                "Try asking about spend, vendors, contracts, invoices, payment terms, renewal clauses, or procurement policy."
            ),
            "tools_used": [],
            "sql_rows": [],
            "doc_snippets": [],
            "sources": {
                "sql_sources": [],
                "document_sources": [],
            },
        }