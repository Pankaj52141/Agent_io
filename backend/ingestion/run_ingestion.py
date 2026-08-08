"""
Data Ingestion Pipeline — Orchestrates parsing, chunking, embedding, and indexing.
Run with: python -m backend.ingestion.run_ingestion
"""
import os
import json
import uuid
import time
import numpy as np
import faiss
from pathlib import Path
from openai import OpenAI

from backend.config import (
    DATA_DIR, CHUNKS_DIR, EMBEDDINGS_DIR, OPENAI_API_KEY, EMBEDDING_MODEL,
    EMBEDDING_DIM, CHUNK_SIZE, CHUNK_OVERLAP,
)
from backend.ingestion.pdf_parser import parse_pdf
from backend.ingestion.excel_parser import parse_excel
from backend.ingestion.chunker import chunk_text
from backend.understanding.generator import generate_understanding_files
from backend.security.injection_guard import sanitize_document_content


def main():
    print("=" * 60)
    print("  Financial Data Ingestion Pipeline")
    print("=" * 60)

    # ── Step 1: Parse all source files ──
    pdfs = sorted(DATA_DIR.glob("*.pdf"))
    xls_files = sorted(DATA_DIR.glob("*.xls"))

    print(f"\nFound {len(pdfs)} PDFs and {len(xls_files)} XLS files.")

    all_raw_chunks = []

    print("\n[1/5] Parsing PDFs...")
    for pdf in pdfs:
        print(f"  -> {pdf.name}")
        try:
            chunks = parse_pdf(str(pdf))
            all_raw_chunks.extend(chunks)
            print(f"    [OK] {len(chunks)} pages extracted")
        except Exception as e:
            print(f"    [FAIL] Error: {e}")

    print(f"\n[2/5] Parsing Excel files...")
    for xls in xls_files:
        print(f"  -> {xls.name}")
        try:
            chunks = parse_excel(str(xls))
            all_raw_chunks.extend(chunks)
            print(f"    [OK] {len(chunks)} sheets extracted")
        except Exception as e:
            print(f"    [FAIL] Error: {e}")

    print(f"\nTotal raw pages/sheets: {len(all_raw_chunks)}")

    # ── Step 2: Chunk and sanitize ──
    print(f"\n[3/5] Chunking and sanitizing content...")
    processed_chunks = []
    for raw in all_raw_chunks:
        text = raw.get("content", "")
        if not text.strip():
            continue

        # Sanitize document content for prompt injection
        source_file = raw.get("source_file", "unknown")
        text = sanitize_document_content(text, source_file)

        # Chunk the text
        text_chunks = chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

        for c in text_chunks:
            chunk_data = {
                "id": str(uuid.uuid4()),  # Unique ID for each chunk
                "content": c,
                "source_file": raw.get("source_file", "unknown"),
                "page_or_sheet": str(raw.get("page_or_sheet", raw.get("page", ""))),
                "section": raw.get("section", ""),
                "data_category": raw.get("data_category", "general"),
                "fiscal_year": raw.get("fiscal_year", ""),
                "fiscal_quarter": raw.get("fiscal_quarter", ""),
                "metadata": raw.get("metadata", {}),
            }
            processed_chunks.append(chunk_data)

    print(f"  [OK] Generated {len(processed_chunks)} final chunks")

    # Save chunks
    chunks_path = CHUNKS_DIR / "all_chunks.json"
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(processed_chunks, f, indent=2, default=str)
    print(f"  [OK] Saved to {chunks_path}")

    # ── Step 3: Generate embeddings ──
    if not OPENAI_API_KEY:
        print("\n[WARN] OPENAI_API_KEY not set. Skipping embeddings.")
        return

    client = OpenAI(api_key=OPENAI_API_KEY)

    print(f"\n[4/5] Generating embeddings...")
    embeddings = []
    chunk_ids = []
    batch_size = 50  # Smaller batches to avoid rate limits

    total_batches = (len(processed_chunks) + batch_size - 1) // batch_size
    for i in range(0, len(processed_chunks), batch_size):
        batch = processed_chunks[i : i + batch_size]
        texts = [c["content"][:8000] for c in batch]  # Truncate to fit model limits
        ids = [c["id"] for c in batch]
        batch_num = i // batch_size + 1

        try:
            response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
            batch_embeddings = [data.embedding for data in response.data]
            embeddings.extend(batch_embeddings)
            chunk_ids.extend(ids)
            print(f"  Batch {batch_num}/{total_batches} [OK] ({len(batch_embeddings)} embeddings)")
        except Exception as e:
            print(f"  Batch {batch_num}/{total_batches} [FAIL] Error: {e}")
            # Wait and retry once
            time.sleep(5)
            try:
                response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL)
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                chunk_ids.extend(ids)
                print(f"  Batch {batch_num}/{total_batches} [OK] (retry succeeded)")
            except Exception as e2:
                print(f"  Batch {batch_num}/{total_batches} [FAIL] Retry failed: {e2}")

        # Small delay to avoid rate limits
        time.sleep(0.5)

    if embeddings:
        print(f"\n  Building FAISS index with {len(embeddings)} vectors...")
        dimension = len(embeddings[0])
        index = faiss.IndexFlatL2(dimension)
        embed_np = np.array(embeddings, dtype=np.float32)
        index.add(embed_np)

        # Save index
        index_path = str(EMBEDDINGS_DIR / "faiss_index.bin")
        faiss.write_index(index, index_path)

        # Save chunk ID mapping
        ids_path = EMBEDDINGS_DIR / "chunk_ids.json"
        with open(ids_path, "w", encoding="utf-8") as f:
            json.dump(chunk_ids, f)

        print(f"  [OK] FAISS index saved ({index.ntotal} vectors, dim={dimension})")

    # ── Step 4: Generate understanding files ──
    print(f"\n[5/5] Generating understanding files...")
    try:
        generate_understanding_files(processed_chunks)
        print("  [OK] Understanding files generated")
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("  Ingestion Complete!")
    print(f"  Chunks: {len(processed_chunks)}")
    print(f"  Embeddings: {len(embeddings)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
