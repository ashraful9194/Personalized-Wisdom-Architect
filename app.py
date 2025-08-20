# import os
# import gradio as gr
# import pypdf
# from smolagents import CodeAgent, HfApiModel, tool
# import yaml
# import re
# from collections import Counter
# from tools.final_answer import FinalAnswerTool
 
# # --- 1. Define the PDF Reading Tool ---
# # This tool takes a file path, reads the PDF, and returns its text content.
# @tool
# def read_pdf_text(file_path: str) -> str:
#     """
#     Reads the text content from a PDF file.
#     Args:
#         file_path (str): The full path to the PDF file.
#     """
#     print(f"🤖 Reading PDF from: {file_path}")
#     try:
#         max_return_chars = int(os.getenv("PDF_MAX_RETURN_CHARS", "15000"))
#         with open(file_path, 'rb') as f:
#             reader = pypdf.PdfReader(f)
#             text = ""
#             print(f"Hey I am here: {len(reader.pages)}")
#             for idx, page in enumerate(reader.pages, start=1):
#                 page_text = page.extract_text()
#                 if page_text:
#                     text += f"\n\n=== Page {idx} ===\n" + page_text + "\n"
#                 if len(text) >= max_return_chars:
#                     break
#         print("✅ PDF read successfully.")
#         if len(text) > max_return_chars:
#             return text[:max_return_chars] + "\n\n[TRUNCATED]"
#         return text
#     except Exception as e:
#         print(f"Error reading PDF: {e}")
#         return f"Error: Could not read the PDF file. Make sure the path is correct and the file is not corrupted. Details: {e}"
 
# # --- 2. Set up the Agent ---
 
# def read_pdf_page_exact(file_path: str, page_number: int) -> str:
#     """
#     Return the exact extracted text of a single page (1-indexed). No truncation.
#     """
#     try:
#         with open(file_path, 'rb') as f:
#             reader = pypdf.PdfReader(f)
#             total_pages = len(reader.pages)
#             if page_number < 1 or page_number > total_pages:
#                 return f"Error: Page {page_number} is out of range. PDF has {total_pages} pages."
#             page = reader.pages[page_number - 1]
#             page_text = page.extract_text() or ""
#             if not page_text.strip():
#                 return f"No extractable text found on page {page_number}."
#             return page_text
#     except Exception as e:
#         return f"Error extracting page {page_number}: {e}"
 
# def refine_text_whitespace(text: str) -> str:
#     """
#     Normalizes whitespace in a string while preserving paragraph breaks.
#     It cleans up extra spaces within each line, then rejoins the lines.
#     """
#     if not text:
#         return ""
 
#     # 1. Split the entire text block into individual lines
#     lines = text.split('\n')
 
#     # 2. For each line, split it into words and join back with a single space.
#     #    This cleans up spaces within the line.
#     cleaned_lines = [' '.join(line.split()) for line in lines]
 
#     # 3. Join the cleaned lines back together with newline characters.
#     #    This reconstructs the paragraph structure.
#     return '\n'.join(cleaned_lines)
 
# @tool
# def read_pdf_page_text(file_path: str, page_number: int) -> str:
#     """
#     Returns the exact extracted text for a single page of a PDF.
 
#     Args:
#         file_path (str): The full path to the PDF file.
#         page_number (int): 1-indexed page number to extract.
 
#     Returns:
#         str: The raw text extracted from the specified page.
#     """
#     return read_pdf_page_exact(file_path, page_number)
 
# # Local stop words for offline text analysis fallback
# STOP_WORDS = set([
#     'the','and','is','in','to','of','a','that','it','for','on','as','with','was','by','at','which','this','from','an','be','or','has','but','not','are','have','you','he','she','they','we','i','me','my','your','our','us','can','will','would','should','could','may','might','must','shall','do','does','did','done','so','if','then','than','when','where','why','how','what','who','whom','whose','about','into','over','under','after','before','between','through','during','without','against','among','up','down','out','off','further','furthermore','however','moreover','nevertheless','therefore','thus','consequently','yet','although','though','even','still','only','just','quite','very','much','little','few','many','some','any','no','nor','too','also','either','neither','both','each','every','own','same','other','another','such','more','most','less','least','s','t','don','now'
# ])
 
 
# def compute_complex_words(pdf_text: str, top_n: int = 100) -> list[str]:
#     # Keep alphabetic words, allow internal hyphens/apostrophes, lowercase
#     tokens = re.findall(r"\b[a-zA-Z][a-zA-Z\-']+\b", pdf_text.lower())
#     # Filter tokens: remove stopwords, url-like/domain-like tokens, and short words
#     def is_valid_token(tok: str) -> bool:
#         if len(tok) < 6:
#             return False
#         if tok in STOP_WORDS:
#             return False
#         if any(sub in tok for sub in [
#             'http', 'www', 'com', 'org', 'net', 'edu', 'gov', 'io', 'co'
#         ]):
#             return False
#         if any(ch.isdigit() for ch in tok):
#             return False
#         return True
 
#     filtered = [t for t in tokens if is_valid_token(t)]
#     counts = Counter(filtered)
#     # Sort by length desc, then frequency desc, then alphabetically
#     sorted_words = sorted(counts.keys(), key=lambda w: (-len(w), -counts[w], w))
#     return sorted_words[:top_n]
 
# # Initialize the tool that gives the final answer
# final_answer = FinalAnswerTool()
 
# # Configure the language model
# # If USE_OLLAMA=1, use a local OpenAI-compatible endpoint (e.g., Ollama) to avoid HF credits
# USE_OLLAMA = os.getenv("USE_OLLAMA", "0") == "1"
# if USE_OLLAMA:
#     try:
#         from smolagents import LiteLLMModel  # Requires `litellm` package
 
#         OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
#         OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
#         # Note: Ollama does not require an API key; a placeholder is fine
#         model_id_for_litellm = OLLAMA_MODEL if OLLAMA_MODEL.startswith("ollama/") else f"ollama/{OLLAMA_MODEL}"
#         model = LiteLLMModel(
#             model_id=model_id_for_litellm,
#             api_base=OLLAMA_BASE_URL,
#             api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
#             max_tokens=2048,
#             temperature=0.2,
#         )
#         print(f"Using local Ollama model: {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
#     except Exception as e:
#         print(f"LiteLLMModel unavailable, trying OpenAI-compatible client: {e}")
#         try:
#             # OpenAI-compatible client (no HF) using smolagents' OpenAI server model
#             from smolagents import OpenAIServerModel
 
#             OLLAMA_BASE_URL_V1 = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/") + "/v1"
#             OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
#             model = OpenAIServerModel(
#                 model_id=OLLAMA_MODEL,
#                 api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
#                 api_base=OLLAMA_BASE_URL_V1,
#                 max_tokens=2048,
#                 temperature=0.2,
#             )
#             print(f"Using OpenAI-compatible endpoint at {OLLAMA_BASE_URL_V1} with model {OLLAMA_MODEL}")
#         except Exception as e2:
#             print(f"Falling back to HfApiModel (OpenAI-compatible client unavailable): {e2}")
#             model = HfApiModel(
#                 max_tokens=2048,
#                 temperature=0.2,
#                 model_id='Qwen/Qwen2.5-Coder-32B-Instruct',
#                 custom_role_conversions=None,
#             )
# else:
#     # Default: Hugging Face Inference API
#     model = HfApiModel(
#         max_tokens=2048,  # Allow longer answers/quotes
#         temperature=0.2,
#         model_id='Qwen/Qwen2.5-Coder-32B-Instruct',
#         custom_role_conversions=None,
#     )
 
# # Load prompt templates from the YAML file
# with open("prompts.yaml", 'r') as stream:
#     prompt_templates = yaml.safe_load(stream)
 
# # Create the agent and provide it with the tools it can use
# agent = CodeAgent(
#     model=model,
#     # Add our new read_pdf_text tool to the list
#     tools=[final_answer, read_pdf_text, read_pdf_page_text],
#     max_steps=6,  # A few more steps to extract quotes
#     verbosity_level=0,
#     prompt_templates=prompt_templates
# )
 
# # --- 3. Create the Gradio Web Interface ---
 
# def process_and_ask(pdf_file, question):
#     """
#     This function is called when the user clicks "Ask" in the UI.
#     It orchestrates the agent to read the PDF and answer the question.
#     """
#     if not pdf_file:
#         return "Please upload a PDF file first."
#     if not question:
#         return "Please enter a question."
 
#     # The agent needs the path to the file. Gradio provides a temporary path.
#     pdf_path = pdf_file.name
 
#     # Check if the user is asking for a specific page.
#     page_match = re.search(r"\bpage\s+(\d{1,4})\b", (question or "").lower())
#     if page_match:
#         page_number = int(page_match.group(1))
 
#         # 1. Directly get the full, exact text of the requested page.
#         print(f"🤖 User requested page {page_number}. Reading it directly.")
#         raw_text = read_pdf_page_exact(pdf_path, page_number)
 
#         # 1a. Clean the extracted text to fix whitespace issues.
#         exact_text = refine_text_whitespace(raw_text)
 
#         # Handle cases where the page can't be read or is empty.
#         if "Error:" in raw_text or "No extractable text" in raw_text:
#             return f"### Could not process page {page_number}\n\n" + raw_text
 
#         # 2. Create a new prompt to generate a CREATIVE and ENGAGING summary.
#         #    This prompt encourages the LLM to be more like a storyteller.
#         summarization_prompt = (
#             f"You are a brilliant content creator whose job is to get people excited about reading. "
#             f"Your task is to create a highly engaging and motivational 'hook' for the text provided below, "
#             f"which comes from page {page_number} of a document.\n\n"
#             f"**Your Goal:** Make the reader instantly curious and eager to read the full page. "
#             f"Do not just summarize; create a compelling preview.\n\n"
#             f"**Instructions:**\n"
#             f"1.  **Start with a Bang:** Begin with an intriguing question or a bold statement that grabs attention.\n"
#             f"2.  **Highlight the 'Why':** Tease the most interesting discovery, critical piece of data, or surprising conclusion on the page. Hint at the answer without giving it all away.\n"
#             f"3.  **Use Energetic Language:** Employ vivid and persuasive words. Frame the content as a must-read.\n"
#             f"4.  **Keep it Short & Punchy:** The entire hook should be a few sentences long.\n\n"
#             f"**Example Style:**\n"
#             f"- 'Ever wonder how a single decision led to a 50% market shift? This page breaks down the critical moment it all changed, revealing a key mistake most leaders miss.'\n"
#             f"- 'What if the secret to network security wasn't a stronger firewall, but something far simpler? Dive into this section to uncover a counterintuitive strategy that challenges everything we thought we knew.'\n\n"
#             f"--- TEXT FROM PAGE {page_number} ---\n"
#             f"{exact_text}"
#         )
 
#         summary = ""
#         try:
#             # 3. Run the agent with the summarization prompt.
#             print("🤖 Generating summary for the page content...")
#             summary = agent.run(summarization_prompt, reset=True)
#             print("✅ Summary generated.")
#         except Exception as e:
#             summary = f"Could not generate summary due to an error: {e}"
 
#         # 4. Combine the generated summary and the full page content for the final output.
#         return (
#             f"### Summary of Page {page_number}\n\n"
#             f"{summary}\n\n"
#             f"---\n\n"
#             f"### Full Content of Page {page_number}\n\n"
#             f"```text\n"
#             f"{exact_text}\n"
#             f"```"
#         )
 
#     # --- ORIGINAL LOGIC FOR GENERAL QUESTIONS (NO CHANGES NEEDED HERE) ---
#     # Create a clear prompt for the agent for general questions
#     prompt = (
#         f"Your task is to answer a question based on the content of a PDF document.\n"
#         f"Use ONLY the `read_pdf_text` tool to get the text from: '{pdf_path}'.\n"
#         f"CRITICAL RULES:\n"
#         f"- Never print or echo the full PDF text.\n"
#         f"- Do NOT call any functions other than `read_pdf_text`, `read_pdf_page_text`, and `final_answer`.\n"
#         f"- Return a detailed explanation and include 1-3 short verbatim quotes (exact words from the PDF).\n"
#         f"- When quoting, include the page marker shown in the text like '=== Page N ==='. Keep each quote under 300 characters.\n"
#         f"- If the answer contains apostrophes or spans multiple lines, use triple double quotes: answer = \"\"\"...\"\"\"\".\n"
#         f"- Keep the 'Thought:' very short.\n"
#         f"- ALWAYS include a Code block exactly like below and end it with ```<end_code>.\n"
#         f"- After computing the result, immediately call `final_answer` and stop.\n\n"
#         f"Question: {question}\n\n"
#         f"Template to follow:\n"
#         f"Thought: I will read the PDF text, find the incident details, then provide a detailed explanation with 1-3 brief quotes and page number(s).\n"
#         f"Code:\n"
#         f"```py\n"
#         f"text = read_pdf_text(file_path='{pdf_path}')\n"
#         f"# Build a detailed explanation, then add 1-3 short verbatim quotes with '=== Page N ===' markers.\n"
#         f"answer = \"\"\"...\"\"\"  # replace with detailed explanation + short quotes incl. page markers\n"
#         f"final_answer(answer)\n"
#         f"```<end_code>\n"
#     )
 
#     # Run the agent for general questions
#     try:
#         response = agent.run(prompt, reset=True)
#         return str(response)
#     except Exception as e:
#         if "complex" in (question or "").lower() and "word" in question.lower():
#             pdf_text = read_pdf_text(pdf_path)
#             if pdf_text.startswith("Error:"):
#                 return pdf_text
#             words = compute_complex_words(pdf_text, top_n=100)
#             return ", ".join(words)
#         return f"Model error: {e}"
 
# # Define the layout and components of the Gradio interface
# with gr.Blocks(theme=gr.themes.Soft(), title="PDF Question Answering Agent") as demo:
#     gr.Markdown("# 🤖 PDF Question Answering Agent")
#     gr.Markdown("Upload a PDF, ask a question about its content, and let the agent find the answer for you.")
 
#     with gr.Row():
#         with gr.Column(scale=1):
#             pdf_uploader = gr.File(label="Upload PDF", file_types=[".pdf"])
#             question_box = gr.Textbox(label="Your Question", placeholder="e.g., What is the main conclusion of the document?")
#             submit_button = gr.Button("Ask", variant="primary")
#         with gr.Column(scale=2):
#             answer_box = gr.Markdown(label="Agent's Answer")
 
#     # Connect the button click to the processing function
#     submit_button.click(         
#         fn=process_and_ask,
#         inputs=[pdf_uploader, question_box],
#         outputs=answer_box
#     )
 
# # --- 4. Launch the application ---
# if __name__ == "__main__":
#     demo.launch()
# import os
# import gradio as gr
# import pypdf
# from smolagents import CodeAgent, tool
# import yaml
# import re
# from tools.final_answer import FinalAnswerTool

# # --- 1. State Management ---
# # Global dictionary to store the partitioned parts of processed books
# BOOK_PARTS = {}

# # --- 2. Tool and Helper Functions ---

# @tool
# def read_pdf_text(file_path: str) -> str:
#     """
#     Reads the text content from a PDF file, up to a certain limit.

#     Args:
#         file_path (str): The full path to the PDF file.
#     """
#     print(f"🤖 Reading PDF from: {file_path}")
#     try:
#         max_return_chars = int(os.getenv("PDF_MAX_RETURN_CHARS", "15000"))
#         with open(file_path, 'rb') as f:
#             reader = pypdf.PdfReader(f)
#             text = ""
#             for idx, page in enumerate(reader.pages, start=1):
#                 page_text = page.extract_text()
#                 if page_text:
#                     text += f"\n\n=== Page {idx} ===\n" + page_text + "\n"
#                 if len(text) >= max_return_chars:
#                     break
#         print("✅ PDF read successfully.")
#         if len(text) > max_return_chars:
#             return text[:max_return_chars] + "\n\n[TRUNCATED]"
#         return text
#     except Exception as e:
#         print(f"Error reading PDF: {e}")
#         return f"Error: Could not read the PDF file. Details: {e}"

# def read_pdf_page_exact(file_path: str, page_number: int) -> str:
#     """Helper to return the exact extracted text of a single page (1-indexed)."""
#     try:
#         with open(file_path, 'rb') as f:
#             reader = pypdf.PdfReader(f)
#             total_pages = len(reader.pages)
#             if page_number < 1 or page_number > total_pages:
#                 return f"Error: Page {page_number} is out of range. PDF has {total_pages} pages."
#             page = reader.pages[page_number - 1]
#             page_text = page.extract_text() or ""
#             if not page_text.strip():
#                 return f"No extractable text found on page {page_number}."
#             return page_text
#     except Exception as e:
#         return f"Error extracting page {page_number}: {e}"

# @tool
# def read_pdf_page_text(file_path: str, page_number: int) -> str:
#     """
#     Returns the exact extracted text for a single page of a PDF.

#     Args:
#         file_path (str): The full path to the PDF file.
#         page_number (int): The 1-indexed page number to extract.
#     """
#     return read_pdf_page_exact(file_path, page_number)

# def read_entire_pdf(file_path: str) -> dict:
#     """Reads the full text of a PDF and maps page numbers to their text."""
#     print(f"🤖 Reading entire PDF from: {file_path}")
#     page_texts = {}
#     try:
#         with open(file_path, 'rb') as f:
#             reader = pypdf.PdfReader(f)
#             for idx, page in enumerate(reader.pages, start=1):
#                 page_text = page.extract_text() or ""
#                 page_texts[idx] = page_text
#         print(f"✅ PDF read successfully. Total pages: {len(page_texts)}")
#         return page_texts
#     except Exception as e:
#         print(f"Error reading PDF: {e}")
#         return {"error": f"Error: Could not read the PDF file. Details: {e}"}

# def refine_text_whitespace(text: str) -> str:
#     """Normalizes whitespace in a string while preserving paragraph breaks."""
#     if not text:
#         return ""
#     lines = text.split('\n')
#     cleaned_lines = [' '.join(line.split()) for line in lines]
#     return '\n'.join(cleaned_lines)

# def partition_book_with_llm(pdf_path: str, agent_instance: CodeAgent) -> str:
#     """Analyzes a book to create a thematic table of contents and partitions the text."""
#     global BOOK_PARTS
#     if pdf_path in BOOK_PARTS:
#         return f"This book has already been analyzed and divided into {len(BOOK_PARTS[pdf_path])} parts."

#     all_pages = read_entire_pdf(pdf_path)
#     if "error" in all_pages:
#         return all_pages["error"]

#     full_text_for_analysis = ""
#     for page_num, text in all_pages.items():
#         full_text_for_analysis += f"\n\n=== Page {page_num} ===\n" + text
#         if len(full_text_for_analysis) > 20000:
#             full_text_for_analysis += "\n\n[... CONTENT TRUNCATED FOR ANALYSIS ...]"
#             break
            
#     # --- SIMPLIFIED PROMPT ---
#     # We now ask the model ONLY for the YAML content, making its job much easier.
#     toc_prompt = (
#         f"You are a professional editor. Your task is to analyze the provided text from a book and create a thematic "
#         f"table of contents. Identify the main logical sections where the topic or narrative shifts significantly. "
#         f"Your output must be ONLY a valid YAML list, where each item has a 'title' and a 'start_page'.\n\n"
#         f"CRITICAL RULES:\n"
#         f"- Do NOT add any extra text, explanation, or markdown formatting like ```yaml. Just output the raw YAML.\n"
#         f"- The 'start_page' must be an integer from the '=== Page N ===' markers.\n"
#         f"- Aim for 5 to 15 logical parts.\n\n"
#         f"Example of a perfect response:\n"
#         f"- title: \"Introduction to Core Concepts\"\n"
#         f"  start_page: 1\n"
#         f"- title: \"The First Major Conflict\"\n"
#         f"  start_page: 25\n"
#         f"- title: \"Resolution and New Beginnings\"\n"
#         f"  start_page: 78\n\n"
#         f"--- BOOK TEXT FOR ANALYSIS ---\n"
#         f"{full_text_for_analysis}"
#     )

#     print("🤖 Asking LLM to generate a table of contents...")
#     try:
#         # --- SIMPLIFIED LOGIC ---
#         # We call the model directly and parse its raw response as YAML.
#         # This bypasses the agent's code-parsing logic for this specific task.
#         raw_response = agent_instance.model.run(toc_prompt)
        
#         # Clean up potential markdown code blocks if the model adds them anyway
#         cleaned_response = re.sub(r"```yaml\n|```", "", raw_response).strip()
        
#         toc = yaml.safe_load(cleaned_response)
        
#         if not isinstance(toc, list) or not all('start_page' in item for item in toc):
#             return f"Error: The model returned malformed YAML.\nContent: {cleaned_response}"

#     except Exception as e:
#         return f"An error occurred while generating or parsing the book structure: {e}"

#     # The rest of the function remains the same...
#     print(f"✅ ToC generated. Partitioning the book into {len(toc)} parts...")
#     parts = []
#     toc.sort(key=lambda x: x['start_page'])
    
#     for i, part_info in enumerate(toc):
#         start_page = part_info['start_page']
#         end_page = toc[i+1]['start_page'] - 1 if i + 1 < len(toc) else len(all_pages)
#         part_text = ""
#         for page_num in range(start_page, end_page + 1):
#             if page_num in all_pages:
#                 part_text += all_pages[page_num] + "\n"
#         parts.append(part_text)

#     BOOK_PARTS[pdf_path] = parts
#     return f"✅ Success! The book has been analyzed and divided into {len(parts)} parts. You can now ask for 'part 1', 'part 2', etc."

# # --- 3. Gradio Interface Logic ---

# def process_and_ask(pdf_file, question):
#     """Main function to handle user requests."""
#     if not pdf_file:
#         return "Please upload a PDF file first."
#     if not question:
#         return "Please enter a question."

#     pdf_path = pdf_file.name

#     if "analyze" in question.lower() or "partition" in question.lower():
#         return partition_book_with_llm(pdf_path, agent)

#     part_match = re.search(r"\b(part|section)\s+(\d+)\b", question.lower())
#     if part_match:
#         if pdf_path not in BOOK_PARTS:
#             return "You must analyze the book first. Please type 'analyze book' and submit."
        
#         part_number = int(part_match.group(2))
#         parts = BOOK_PARTS[pdf_path]

#         if not 1 <= part_number <= len(parts):
#             return f"Invalid part number. This book has {len(parts)} parts. Please choose a number between 1 and {len(parts)}."

#         part_index = part_number - 1
#         part_text = parts[part_index]
#         cleaned_part_text = refine_text_whitespace(part_text)
        
#         hook_prompt = (
#             f"You are a brilliant content creator. Create a highly engaging 'hook' for the text provided below. "
#             f"Your output must be a Python code block that calls the `final_answer` tool with the hook as a string.\n\n"
#             f"CRITICAL RULES:\n"
#             f"- Start with an intriguing question or a bold statement.\n"
#             f"- Use energetic and persuasive language.\n"
#             f"- Your final action MUST be to call `final_answer`.\n\n"
#             f"Template to follow:\n"
#             f"Thought: I will write a compelling hook and call final_answer.\n"
#             f"Code:\n"
#             f"```py\n"
#             f"hook = \"\"\"Ever wonder how a single decision can change everything? This section reveals the critical moment...\"\"\"\n"
#             f"final_answer(hook)\n"
#             f"```<end_code>\n\n"
#             f"--- TEXT FROM PART {part_number} ---\n{cleaned_part_text}"
#         )
        
#         summary_hook = ""
#         try:
#             print(f"🤖 Generating motivational hook for part {part_number}...")
#             summary_hook = agent.run(hook_prompt, reset=True)
#         except Exception as e:
#             summary_hook = f"Could not generate hook due to an error: {e}"

#         return (
#             f"### Hook for Part {part_number}\n\n{summary_hook}\n\n"
#             f"---\n\n### Full Content of Part {part_number}\n\n"
#             f"```text\n{cleaned_part_text}\n```"
#         )
    
#     page_match = re.search(r"\bpage\s+(\d+)\b", (question or "").lower())
#     if page_match:
#         page_number = int(page_match.group(1))
#         page_content = read_pdf_page_exact(pdf_path, page_number)
#         cleaned_page_text = refine_text_whitespace(page_content)
#         return f"### Full Content of Page {page_number}\n\n```text\n{cleaned_page_text}\n```"
    
#     # RESTORED: General question handler
#     # For any other question, let the agent figure it out using its tools.
#     prompt_with_context = (
#         f"Your task is to answer the user's question. "
#         f"The user has uploaded a file available at the path '{pdf_path}'. "
#         f"You can use the `read_pdf_text` or `read_pdf_page_text` tools to inspect it.\n\n"
#         f"User's Question: {question}"
#     )
#     try:
#         response = agent.run(prompt_with_context, reset=True)
#         return str(response)
#     except Exception as e:
#         return f"An error occurred while running the agent: {e}"

# # --- MOVED: Agent and UI Setup ---

# # Initialize the tool that gives the final answer
# final_answer = FinalAnswerTool()

# # Directly configure the agent to use your local Ollama model
# print("🚀 Configuring model for local Ollama...")
# from smolagents import LiteLLMModel
# OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
# model_id_for_litellm = OLLAMA_MODEL if OLLAMA_MODEL.startswith("ollama/") else f"ollama/{OLLAMA_MODEL}"
# model = LiteLLMModel(
#     model_id=model_id_for_litellm,
#     api_base=OLLAMA_BASE_URL,
#     api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
#     max_tokens=2048,
#     temperature=0.2,
# )
# print(f"✅ Using local Ollama model: {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
 
# # Load prompt templates from the YAML file
# with open("prompts.yaml", 'r') as stream:
#     prompt_templates = yaml.safe_load(stream)
 
# # Create the agent and provide it with all the defined tools
# agent = CodeAgent(
#     model=model,
#     tools=[final_answer, read_pdf_text, read_pdf_page_text],
#     max_steps=8,
#     verbosity_level=0,
#     prompt_templates=prompt_templates
# )

# # Define the Gradio interface
# with gr.Blocks(theme=gr.themes.Soft(), title="PDF Book Analyzer") as demo:
#     gr.Markdown("# 🤖 PDF Book Analyzer")
#     gr.Markdown(
#         "**Step 1:** Upload a PDF.\n"
#         "**Step 2:** Type `analyze book` in the question box and click Ask.\n"
#         "**Step 3:** Once analyzed, ask for a specific part (e.g., `part 5`)."
#     )
    
#     with gr.Row():
#         with gr.Column(scale=1):
#             pdf_uploader = gr.File(label="Upload PDF", file_types=[".pdf"])
#             question_box = gr.Textbox(label="Your Command or Question", placeholder="e.g., analyze book")
#             submit_button = gr.Button("Ask", variant="primary")
#         with gr.Column(scale=2):
#             answer_box = gr.Markdown(label="Agent's Answer")

#     submit_button.click(fn=process_and_ask, inputs=[pdf_uploader, question_box], outputs=answer_box)

# # --- Launch the application ---
# if __name__ == "__main__":
#     demo.launch()

import os
import gradio as gr
import pypdf
from smolagents import CodeAgent, tool
import yaml
import re
import litellm # <-- ADDED THIS IMPORT
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
        max_return_chars = int(os.getenv("PDF_MAX_RETURN_CHARS", "15000"))
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
import json # Make sure to add this at the top of your app.py

def partition_book_with_llm(pdf_path: str, agent_instance: CodeAgent) -> str:
    """Analyzes a book to create a thematic table of contents (using JSON) and partitions the text."""
    global BOOK_PARTS
    if pdf_path in BOOK_PARTS:
        return f"This book has already been analyzed and divided into {len(BOOK_PARTS[pdf_path])} parts."

    all_pages = read_entire_pdf(pdf_path)
    if "error" in all_pages:
        return all_pages["error"]

    full_text_for_analysis = ""
    for page_num, text in all_pages.items():
        full_text_for_analysis += f"\n\n=== Page {page_num} ===\n" + text
        if len(full_text_for_analysis) > 20000:
            full_text_for_analysis += "\n\n[... CONTENT TRUNCATED FOR ANALYSIS ...]"
            break
            
    # --- NEW JSON PROMPT ---
    # This prompt asks for a JSON string, which is easier for models to generate and for Python to parse.
    toc_prompt = (
        f"Analyze the text from a book which contains '=== Page N ===' markers. "
        f"Your task is to identify the main thematic sections and create a table of contents. "
        f"Your output MUST be a valid JSON string representing a list of objects. Nothing else. "
        f"Each object must have two keys: a 'title' (string) and a 'start_page' (integer). "
        f"Do not output markdown, code blocks, or any explanatory text. Generate the raw JSON string directly.\n\n"
        f"EXAMPLE OF A PERFECT RESPONSE:\n"
        f'[{{"title": "Introduction to Core Concepts", "start_page": 1}}, {{"title": "The First Major Conflict", "start_page": 25}}]\n\n'
        f"---BEGIN TEXT---\n{full_text_for_analysis}\n---END TEXT---"
    )

    print("🤖 Asking LLM to generate a JSON table of contents...")
    try:
        response = litellm.completion(
            model=model_id_for_litellm,
            messages=[{"role": "user", "content": toc_prompt}],
            api_base=OLLAMA_BASE_URL,
            api_key="ollama"
        )
        raw_response = response.choices[0].message.content
        
        # Clean the response to find the JSON list
        json_match = re.search(r'\[.*\]', raw_response, re.DOTALL)
        if not json_match:
            return f"Error: The model did not return a valid JSON list.\nContent: {raw_response}"
        
        cleaned_json_string = json_match.group(0)
        toc = json.loads(cleaned_json_string)
        
        if not isinstance(toc, list) or not all('start_page' in item for item in toc):
            return f"Error: The model returned malformed JSON.\nContent: {cleaned_json_string}"

    except json.JSONDecodeError:
        return f"Error: Failed to decode JSON from the model's response.\nContent: {raw_response}"
    except Exception as e:
        return f"An error occurred while generating or parsing the book structure: {e}"

    print(f"✅ ToC generated. Partitioning the book into {len(toc)} parts...")
    parts = []
    toc.sort(key=lambda x: x['start_page'])
    
    for i, part_info in enumerate(toc):
        start_page = part_info['start_page']
        end_page = toc[i+1]['start_page'] - 1 if i + 1 < len(toc) else len(all_pages)
        part_text = ""
        for page_num in range(start_page, end_page + 1):
            if page_num in all_pages:
                part_text += all_pages[page_num] + "\n"
        parts.append(part_text)

    BOOK_PARTS[pdf_path] = parts
    return f"✅ Success! The book has been analyzed and divided into {len(parts)} parts. You can now ask for 'part 1', 'part 2', etc."

def process_and_ask(pdf_file, question):
    """Main function to handle user requests."""
    if not pdf_file:
        return "Please upload a PDF file first."
    if not question:
        return "Please enter a question."

    pdf_path = pdf_file.name

    if "analyze" in question.lower() or "partition" in question.lower():
        return partition_book_with_llm(pdf_path, agent)

    part_match = re.search(r"\b(part|section)\s+(\d+)\b", question.lower())
    if part_match:
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
            f"CRITICAL RULES:\n"
            f"- Start with an intriguing question or a bold statement.\n"
            f"- Use energetic and persuasive language.\n"
            f"- Your final action MUST be to call `final_answer`.\n\n"
            f"Template to follow:\n"
            f"Thought: I will write a compelling hook and call final_answer.\n"
            f"Code:\n"
            f"```py\n"
            f"hook = \"\"\"Ever wonder how a single decision can change everything? This section reveals the critical moment...\"\"\"\n"
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
    
    page_match = re.search(r"\bpage\s+(\d{1,4})\b", (question or "").lower())
    if page_match:
        page_number = int(page_match.group(1))
        page_content = read_pdf_page_exact(pdf_path, page_number)
        cleaned_page_text = refine_text_whitespace(page_content)
        return f"### Full Content of Page {page_number}\n\n```text\n{cleaned_page_text}\n```"
    
    prompt_with_context = (
        f"Your task is to answer the user's question. "
        f"The user has uploaded a file available at the path '{pdf_path}'. "
        f"You can use the `read_pdf_text` or `read_pdf_page_text` tools to inspect it.\n\n"
        f"User's Question: {question}"
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
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
model_id_for_litellm = OLLAMA_MODEL if OLLAMA_MODEL.startswith("ollama/") else f"ollama/{OLLAMA_MODEL}"
model = LiteLLMModel(
    model_id=model_id_for_litellm,
    api_base=OLLAMA_BASE_URL,
    api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
    max_tokens=2048,
    temperature=0.2,
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
    gr.Markdown("# 🤖 PDF Book Analyzer")
    gr.Markdown(
        "**Step 1:** Upload a PDF.\n"
        "**Step 2:** Type `analyze book` in the question box and click Ask.\n"
        "**Step 3:** Once analyzed, ask for a specific part (e.g., `part 5`)."
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            pdf_uploader = gr.File(label="Upload PDF", file_types=[".pdf"])
            question_box = gr.Textbox(label="Your Command or Question", placeholder="e.g., analyze book")
            submit_button = gr.Button("Ask", variant="primary")
        with gr.Column(scale=2):
            answer_box = gr.Markdown(label="Agent's Answer")

    submit_button.click(fn=process_and_ask, inputs=[pdf_uploader, question_box], outputs=answer_box)

if __name__ == "__main__":
    demo.launch()