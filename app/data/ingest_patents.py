import os
import chromadb
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field
from pypdf import PdfReader
import re

chroma_client = chromadb.PersistentClient(path="./chroma_db")
patent_collection = chroma_client.get_or_create_collection(name="patent_corpus")

# Initialize Instructor pointing to your local Ollama instance
client = instructor.from_openai(
    OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    ),
    mode=instructor.Mode.JSON,
)

class PatentMetadata(BaseModel):
    patent_title: str = Field(description="Full title of the patent")
    inventors: str = Field(description="Names of the primary inventor(s), comma seperated string")


def extract_metadata_with_llm(page_1_text: str, model_name: str = "llama3.2") -> PatentMetadata:
    """
    Uses Ollama to parse messy/interleaved USPTO cover page text into structured metadata.
    """
    system_prompt = """
    You are an expert patent metadata extractor. Extract the primary Patent ID, Patent Title, 
    and Inventor(s) from the provided USPTO cover sheet text.
    
    CRITICAL RULES:
    1. Ignore PDF viewer artifacts (e.g., 'Automatic Zoom', '100%', 'Page Fit').
    2. Reconstruct the full title even if words are split across multi-column text streams.
    
    """
    
    try:
        metadata = client.chat.completions.create(
            model=model_name,
            response_model=PatentMetadata,
            max_retries=2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Cover Sheet Text:\n{page_1_text[:2500]}"},
            ],
        )
        return metadata
    except Exception as e:
        print(f"⚠️ LLM Metadata Extraction failed: {e}. Falling back to default values.")
        return PatentMetadata(
            patent_title="Unknown Patent Title",
            inventors="Unknown Inventor"
        )


def extract_and_chunk_pdf(pdf_path: str, chunk_size: int = 800, overlap: int = 150):
    reader = PdfReader(pdf_path)
    filename = os.path.basename(pdf_path)
    chunks_with_metadata = []

    # 1. Extract cover text from Page 1
    first_page_text = reader.pages[0].extract_text() if len(reader.pages) > 0 else ""
    
    # 2. Extract structured metadata using local LLM
    print(f" Extracting metadata with Ollama for: {filename}...")
    meta = extract_metadata_with_llm(first_page_text)
    id = re.sub(r'\D', '', filename)
    print(f"   • Patent ID   : {id}")
    print(f"   • Patent Title: {meta.patent_title}")
    print(f"   • Inventor(s) : {meta.inventors}")
        
    # 3. Chunk text across pages and attach rich metadata
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text or not text.strip():
            continue

        start = 0
        chunk_idx = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks_with_metadata.append({
                    "text": chunk_text,
                    "metadata": {
                        "patent_id": id,
                        "patent_title": meta.patent_title,
                        "inventors": meta.inventors,
                        "source_file": filename,
                        "page_number": page_num + 1,
                        "chunk_id": f"{filename}_p{page_num + 1}_c{chunk_idx}"
                    }
                })

            start += chunk_size - overlap
            chunk_idx += 1

    return chunks_with_metadata

def ingest_patent_directory(pdf_folder_path: str):
    """
    Scans directory for PDF files, extracts chunks, and batch-loads into ChromaDB.
    """
    if not os.path.exists(pdf_folder_path):
        print(f"Directory '{pdf_folder_path}' not found.")
        return

    documents = []
    metadatas = []
    ids = []

    for file in os.listdir(pdf_folder_path):
        if file.endswith(".pdf"):
            full_path = os.path.join(pdf_folder_path, file)
            print(f"Processing: {file}...")

            extracted_chunks = extract_and_chunk_pdf(full_path)

            for chunk in extracted_chunks:
                documents.append(chunk["text"])
                metadatas.append(chunk["metadata"])
                ids.append(chunk["metadata"]["chunk_id"])

    if documents:
        # ChromaDB automatically generates embeddings using default MiniLM model
        patent_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"\nSuccessfully ingested {len(documents)} chunks into ChromaDB!")
    else:
        print("No PDF text extracted.")


if __name__ == "__main__":
    PDF_DIR = "./app/data/pdf_patents"
    ingest_patent_directory(PDF_DIR)