import os
import gradio as gr
import pypdf
from smolagents import CodeAgent, tool
import yaml
import re
import litellm
import json
from tools.final_answer import FinalAnswerTool

# --- 1. State Management ---
BOOK_PARTS = {}

# --- 2. Tool and Helper Functions ---
@tool
def read_pdf_text(file_path: str) -> str:
    """
    Reads the text content from a PDF file, up to a certain limit.

    Args:
        file_path (str): The full path to the PDF file.
    """
    print(f"🤖 Reading PDF from: {file_path}")
    try:
        max_return_chars = int(os.getenv("PDF_MAX_RETURN_CHARS", "20000"))
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            text = ""
            for idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n\n=== Page {idx} ===\n" + page_text + "\n"
                if len(text) >= max_return_chars:
                    break
        print("✅ PDF read successfully.")
        if len(text) > max_return_chars:
            return text[:max_return_chars] + "\n\n[TRUNCATED]"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return f"Error: Could not read the PDF file. Make sure the path is correct and the file is not corrupted. Details: {e}"

def read_pdf_page_exact(file_path: str, page_number: int) -> str:
    """Helper to return the exact extracted text of a single page (1-indexed)."""
    try:
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            total_pages = len(reader.pages)
            if page_number < 1 or page_number > total_pages:
                return f"Error: Page {page_number} is out of range. PDF has {total_pages} pages."
            page = reader.pages[page_number - 1]
            page_text = page.extract_text() or ""
            if not page_text.strip():
                return f"No extractable text found on page {page_number}."
            return page_text
    except Exception as e:
        return f"Error extracting page {page_number}: {e}"

@tool
def read_pdf_page_text(file_path: str, page_number: int) -> str:
    """
    Returns the exact extracted text for a single page of a PDF.

    Args:
        file_path (str): The full path to the PDF file.
        page_number (int): The 1-indexed page number to extract.
    """
    return read_pdf_page_exact(file_path, page_number)

def read_entire_pdf(file_path: str) -> dict:
    """Reads the full text of a PDF and maps page numbers to their text."""
    print(f"🤖 Reading entire PDF from: {file_path}")
    page_texts = {}
    try:
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                page_texts[idx] = page_text
        print(f"✅ PDF read successfully. Total pages: {len(page_texts)}")
        return page_texts
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return {"error": f"Error: Could not read the PDF file. Details: {e}"}

def refine_text_whitespace(text: str) -> str:
    """Normalizes whitespace in a string while preserving paragraph breaks."""
    if not text:
        return ""
    lines = text.split('\n')
    cleaned_lines = [' '.join(line.split()) for line in lines]
    return '\n'.join(cleaned_lines)

# --- FINAL, RELIABLE PARTITIONING FUNCTION ---
def partition_book(pdf_path: str) -> str:
    """
    Programmatically divides the book into chunks of 10 pages each.
    This method is fast and reliable.
    """
    global BOOK_PARTS
    if pdf_path in BOOK_PARTS:
        return f"This book has already been analyzed and divided into {len(BOOK_PARTS[pdf_path])} parts."

    print("🤖 Programmatically partitioning the book into 10-page chunks...")
    try:
        all_pages = read_entire_pdf(pdf_path)
        if "error" in all_pages:
            return all_pages["error"]
        
        total_pages = len(all_pages)
        if total_pages == 0:
            return "Error: Could not read any pages from the PDF."

        parts = []
        chunk_size = 10
        for i in range(0, total_pages, chunk_size):
            start_page = i + 1
            end_page = min(i + chunk_size, total_pages)
            
            part_text = ""
            for page_num in range(start_page, end_page + 1):
                if page_num in all_pages:
                    part_text += all_pages[page_num] + "\n"
            
            parts.append(part_text)
        
        BOOK_PARTS[pdf_path] = parts
        return (f"✅ Success! The book has been divided into {len(parts)} parts, "
                f"each about 10 pages long. You can now ask for 'part 1', 'part 2', etc.")

    except Exception as e:
        return f"An error occurred while partitioning the book: {e}"

def process_and_ask(pdf_file, question):
    """Main function to handle user requests."""
    if not pdf_file and any(cmd in question.lower() for cmd in ["analyze", "partition", "part", "section", "page"]):
        return "Please upload a PDF file to perform this action."
    if not question:
        return "Please enter a question."

    pdf_path = pdf_file.name if pdf_file else None

    if pdf_path and ("analyze" in question.lower() or "partition" in question.lower()):
        return partition_book(pdf_path)

    part_match = re.search(r"\b(part|section)\s+(\d+)\b", question.lower())
    if pdf_path and part_match:
        if pdf_path not in BOOK_PARTS:
            return "You must analyze the book first. Please type 'analyze book' and submit."
        
        part_number = int(part_match.group(2))
        parts = BOOK_PARTS[pdf_path]

        if not 1 <= part_number <= len(parts):
            return f"Invalid part number. This book has {len(parts)} parts. Please choose a number between 1 and {len(parts)}."

        part_index = part_number - 1
        part_text = parts[part_index]
        cleaned_part_text = refine_text_whitespace(part_text)
        
        hook_prompt = (
            f"You are a brilliant content creator. Create a highly engaging 'hook' for the text provided below. "
            f"Your output must be a Python code block that calls the `final_answer` tool with the hook as a string.\n\n"
            f"Template to follow:\n"
            f"Thought: I will read the provided text and write a compelling hook, then call final_answer.\n"
            f"Code:\n"
            f"```py\n"
            f"hook = \"\"\"What secrets lie within these pages? A critical insight awaits that could change everything...\"\"\"\n"
            f"final_answer(hook)\n"
            f"```<end_code>\n\n"
            f"--- TEXT FROM PART {part_number} ---\n{cleaned_part_text}"
        )
        
        summary_hook = ""
        try:
            print(f"🤖 Generating motivational hook for part {part_number}...")
            summary_hook = agent.run(hook_prompt, reset=True)
        except Exception as e:
            summary_hook = f"Could not generate hook due to an error: {e}"

        return (
            f"### Hook for Part {part_number}\n\n{summary_hook}\n\n"
            f"---\n\n### Full Content of Part {part_number}\n\n"
            f"```text\n{cleaned_part_text}\n```"
        )
    
    page_match = re.search(r"\bpage\s+(\d+)\b", (question or "").lower())
    if pdf_path and page_match:
        page_number = int(page_match.group(1))
        page_content = read_pdf_page_exact(pdf_path, page_number)
        cleaned_page_text = refine_text_whitespace(page_content)
        return f"### Full Content of Page {page_number}\n\n```text\n{cleaned_page_text}\n```"
    
    prompt_with_context = (
        f"Answer the user's question: '{question}'. "
        f"If the question seems related to the uploaded PDF (available at '{pdf_path}'), "
        f"your first step must be to call the `read_pdf_text` tool to get its content. "
        f"Then, provide the answer using the `final_answer` tool."
    )
    try:
        response = agent.run(prompt_with_context, reset=True)
        return str(response)
    except Exception as e:
        return f"An error occurred while running the agent: {e}"

# --- Agent and UI Setup ---
final_answer = FinalAnswerTool()

print("🚀 Configuring model for local Ollama...")
from smolagents import LiteLLMModel

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b") 
model_id_for_litellm = f"ollama/{OLLAMA_MODEL}"

model = LiteLLMModel(
    model_id=model_id_for_litellm,
    api_base=OLLAMA_BASE_URL,
    api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
    max_tokens=4096,
    temperature=0.2,
    timeout=300
)
print(f"✅ Using local Ollama model: {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
 
with open("prompts.yaml", 'r') as stream:
    prompt_templates = yaml.safe_load(stream)
 
agent = CodeAgent(
    model=model,
    tools=[final_answer, read_pdf_text, read_pdf_page_text],
    max_steps=8,
    verbosity_level=0,
    prompt_templates=prompt_templates
)

with gr.Blocks(theme=gr.themes.Soft(), title="PDF Book Analyzer") as demo:
    gr.Markdown("# 📖 PDF Book Analyzer")
    gr.Markdown(
        "**Step 1:** Upload a PDF.\n"
        "**Step 2:** Type `analyze book` to divide it into 10-page parts.\n"
        "**Step 3:** Ask for a specific part (e.g., `part 5`)."
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            pdf_uploader = gr.File(label="Upload PDF", file_types=[".pdf"])
            question_box = gr.Textbox(label="Your Command or Question", placeholder="e.g., analyze book or what is deep work?")
            submit_button = gr.Button("Ask", variant="primary")
        with gr.Column(scale=2):
            answer_box = gr.Markdown(label="Agent's Answer")

    submit_button.click(fn=process_and_ask, inputs=[pdf_uploader, question_box], outputs=answer_box)

if __name__ == "__main__":
    demo.launch(share=True)