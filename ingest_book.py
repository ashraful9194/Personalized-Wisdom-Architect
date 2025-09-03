import os
import time
import json
import PyPDF2
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INDEX_NAME = "wisdom-architect"
CLOUD = "aws"
REGION = "us-east-1" # Common AWS region

# --- Initialize Clients ---
# Use the new Pinecone client initialization
pc = Pinecone(api_key=PINECONE_API_KEY) # <-- CHANGE
genai.configure(api_key=GEMINI_API_KEY)

def check_and_create_index():
    """Check if the Pinecone index exists and create it if it doesn't."""
    if INDEX_NAME not in pc.list_indexes().names():
        print(f"Creating index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=768,  # Dimension for text-embedding-004
            metric="cosine",
            spec=ServerlessSpec(cloud=CLOUD, region=REGION)
        )
        print("Waiting for index to become ready...")
        while not pc.describe_index(INDEX_NAME).status['ready']:
            time.sleep(5)
        print(f"✅ Index '{INDEX_NAME}' is ready!")
    else:
        print(f"✅ Index '{INDEX_NAME}' already exists.")
    return pc.Index(INDEX_NAME)

def extract_pdf_text(pdf_path: str) -> str:
    """Extract all text from a PDF file, adding page markers."""
    print(f"📖 Extracting text and adding page markers from: {pdf_path}")
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for i, page in enumerate(pdf_reader.pages):
                # Add a clear page marker before each page's content
                text += f"\n\n---PAGE {i + 1}---\n\n"
                text += page.extract_text() or ""
                print(f"Processed page {i + 1}/{len(pdf_reader.pages)}")
        print(f"✅ Successfully extracted {len(text)} characters with page markers.")
        return text
    except Exception as e:
        print(f"❌ Error extracting PDF text: {e}")
        raise

def create_thematic_chunks(full_text: str) -> list:
    """Create chunks using recursive splitting (no LLM; cost-free).

    Strategy:
    - Prefer natural boundaries first (page markers, blank lines, sentences, spaces)
    - Target chunk size ~1200 chars with 150-char overlap for better retrieval
    """
    print("🧠 Creating chunks using RecursiveCharacterTextSplitter...")

    # Split first on explicit page markers to keep coherence across pages
    pages = [p.strip() for p in full_text.split("\n\n---PAGE ") if p.strip()]
    if not pages:
        pages = [full_text]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[str] = []
    for page_block in pages:
        # Remove any residual page marker header like "X---" if present
        cleaned = page_block
        if "---\n\n" in cleaned:
            cleaned = cleaned.split("---\n\n", 1)[-1]
        chunks.extend(splitter.split_text(cleaned))

    print(f"✅ Created {len(chunks)} chunks (recursive, no LLM).")
    return chunks

def get_text_embedding(text: str) -> list:
    """Get vector embedding for text using the correct Gemini model."""
    try:
        # Use the correct model and function for embedding # <-- CHANGE
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        return result['embedding']
    except Exception as e:
        print(f"❌ Error getting embedding: {e}")
        return None # Return None to handle the error gracefully

def main():
    """Main execution block to orchestrate the book ingestion process."""
    if not PINECONE_API_KEY or not GEMINI_API_KEY:
        raise ValueError("Please set your PINECONE_API_KEY and GEMINI_API_KEY environment variables.")

    print("🚀 Starting book ingestion process...")
    try:
        index = check_and_create_index()
        pdf_path = "book.pdf"
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"'{pdf_path}' not found. Please place your book in the same folder.")
            
        full_text = extract_pdf_text(pdf_path)
        chunks = create_thematic_chunks(full_text)

        print(f"📊 Preparing to upload {len(chunks)} chunks to Pinecone...")
        batch_size = 100 # Process in batches for efficiency
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            print(f"--- Processing batch {i//batch_size + 1} ---")
            
            vectors_to_upsert = []
            for j, chunk in enumerate(batch_chunks):
                vector = get_text_embedding(chunk)
                if vector: # Only process if embedding was successful
                    vectors_to_upsert.append({
                        "id": f"chunk_{i + j}",
                        "values": vector,
                        "metadata": {"text": chunk, "chunk_number": i + j}
                    })
                time.sleep(0.5) # Small delay to respect API rate limits
            
            if vectors_to_upsert:
                index.upsert(vectors=vectors_to_upsert)
                print(f"✅ Upserted batch of {len(vectors_to_upsert)} vectors.")

        print("🎉 Book ingestion completed successfully!")

    except Exception as e:
        print(f"❌ A fatal error occurred: {e}")

if __name__ == "__main__":
    main()