from pathlib import Path
from typing import List, Dict

import os

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader

from spendiq.config import DOCS_DIR


class DocumentStore:
    def __init__(self):
        self.documents: List[Dict] = []
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = None

    def load_documents(self):
        self.documents = []

        # Load contracts
        contracts_path = DOCS_DIR / "contracts"
        policies_path = DOCS_DIR / "policies"

        for base_path in [contracts_path, policies_path]:
            for root, _, files in os.walk(base_path):
                for file in files:
                    full_path = Path(root) / file

                    if file.endswith(".md"):
                        text = full_path.read_text(encoding="utf-8")
                    elif file.endswith(".pdf"):
                        text = self._read_pdf(full_path)
                    else:
                        continue

                    chunks = self._chunk_text(text)

                    for i, chunk in enumerate(chunks):
                        self.documents.append({
                            "text": chunk,
                            "source": str(full_path),
                            "chunk_id": i
                        })

        print(f"Loaded {len(self.documents)} document chunks")

    def _read_pdf(self, path: Path) -> str:
        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    def _chunk_text(self, text: str, chunk_size: int = 200) -> List[str]:
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks

    def build_index(self):
        texts = [doc["text"] for doc in self.documents]
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(self, query: str, top_k: int = 5):
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]

        ranked = sorted(
            zip(self.documents, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {
                "text": doc["text"],
                "source": doc["source"],
                "score": score
            }
            for doc, score in ranked[:top_k]
        ]