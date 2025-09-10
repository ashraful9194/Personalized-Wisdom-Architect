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
INDEX_NAME = "how-to-win-friends-and-influence-people"
CLOUD = "aws"
REGION = "us-east-1" # Common AWS region

# --- Initialize Clients ---
# Use the new Pinecone client initialization
pc = Pinecone(api_key=PINECONE_API_KEY) # <-- CHANGE
genai.configure(api_key=GEMINI_API_KEY)

def check_and_create_index():
    """Check if the Pinecone index exists and create it if it doesn't."""
    # Always recreate the index: delete if it exists, then create fresh
    existing = pc.list_indexes().names()
    if INDEX_NAME in existing:
        print(f"🗑️ Deleting existing index '{INDEX_NAME}'...")
        pc.delete_index(INDEX_NAME)
        # Wait until deletion is reflected
        while INDEX_NAME in pc.list_indexes().names():
            time.sleep(2)
        print(f"✅ Deleted '{INDEX_NAME}'.")

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

def create_chunks_by_page_count(full_text: str, pages_per_chunk: int = 10) -> list[str]:
    """
    Groups the text of a book into larger chunks based on a set number of pages.
    This is ideal for sequential reading, like daily emails.
    """
    print(f"🧠 Grouping text into chunks of {pages_per_chunk} pages...")

    # 1. Split the entire text by the unique page marker.
    # The first element will be empty due to the split, so we skip it `[1:]`.
    pages = full_text.split("\n\n---PAGE ")[1:]
    if not pages:
        print("❌ No pages found. Check the PDF extraction and page markers.")
        return []

    # 2. Group the extracted pages into batches of `pages_per_chunk`.
    chunks = []
    for i in range(0, len(pages), pages_per_chunk):
        # Get a batch of 15 pages
        page_batch = pages[i:i + pages_per_chunk]

        # 3. Join the text of this batch back together into a single chunk.
        # We'll re-add the page markers for clarity in the final text.
        chunk_content = ""
        for page_text in page_batch:
             # The page_text looks like "1---\n\nActual text...", so we add the marker back.
            chunk_content += f"\n\n---PAGE {page_text}"

        chunks.append(chunk_content.strip())

    print(f"✅ Created {len(chunks)} chunks, each containing up to {pages_per_chunk} pages.")
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
        pdf_path = "book2.pdf"
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"'{pdf_path}' not found. Please place your book in the same folder.")
            
        full_text = extract_pdf_text(pdf_path)
        chunks = create_chunks_by_page_count(full_text, pages_per_chunk=10)

        print(f"📊 Preparing to upload {len(chunks)} chunks to Pinecone...")
        # Persist total chunks to progress.json for downstream use
        try:
            progress_path = "progress.json"
            current_progress = {}
            if os.path.exists(progress_path):
                with open(progress_path, "r") as pf:
                    try:
                        current_progress = json.load(pf) or {}
                    except Exception:
                        current_progress = {}
            current_chunk_value = int(current_progress.get("current_chunk", 0))
            with open(progress_path, "w") as pf:
                json.dump({
                    "current_chunk": current_chunk_value,
                    "total_chunks": len(chunks)
                }, pf)
            print(f"📝 Saved total_chunks={len(chunks)} to progress.json")
        except Exception as e:
            print(f"⚠️ Could not update progress.json with total_chunks: {e}")
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