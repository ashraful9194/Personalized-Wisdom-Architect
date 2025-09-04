import os
import json
import smtplib
import sys
import unicodedata
import re
from email.message import EmailMessage
from email import policy
from email.header import Header
from email.utils import formataddr
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

SENDER_EMAIL = "ashraful9194@gmail.com"  # <-- IMPORTANT: Change to your email
RECEIVER_EMAIL = "ashraful9194@gmail.com" # <-- IMPORTANT: Change to your email

INDEX_NAME = "wisdom-architect"
PROGRESS_FILE = "progress.json"

# --- Initialize Clients ---
pc = Pinecone(api_key=PINECONE_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
generative_model = genai.GenerativeModel('gemini-1.5-flash')

def clean_text_for_email(text):
    """
    Clean text to remove problematic Unicode characters that cause email encoding issues.
    """
    if not text:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Replace non-breaking spaces and other problematic Unicode characters
    replacements = {
        '\xa0': ' ',  # Non-breaking space -> regular space
        '\u2013': '-',  # En dash -> hyphen
        '\u2014': '--',  # Em dash -> double hyphen
        '\u2018': "'",  # Left single quotation mark
        '\u2019': "'",  # Right single quotation mark
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u2026': '...',  # Horizontal ellipsis
        '\u00a0': ' ',  # Another non-breaking space variant
    }
    
    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)
    
    # Normalize Unicode characters to their closest ASCII equivalents
    text = unicodedata.normalize('NFKD', text)
    
    # Remove any remaining non-ASCII characters that might cause issues
    # But keep common accented characters by encoding/decoding
    try:
        text = text.encode('ascii', 'ignore').decode('ascii')
    except UnicodeError:
        # If that fails, be more aggressive
        text = ''.join(char for char in text if ord(char) < 128)
    
    # Clean up any double spaces that might have been created
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def get_progress():
    """Reads the current chunk number from the progress file."""
    with open(PROGRESS_FILE, 'r') as f:
        return json.load(f)

def save_progress(progress_data):
    """Saves the updated chunk number to the progress file."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress_data, f)

def send_email(subject, body):
    """Sends the daily digest email using smtplib with robust Unicode handling."""
    try:
        # Clean the subject and body of problematic Unicode characters
        safe_subject = clean_text_for_email(subject) or "Your Daily Wisdom Digest"
        safe_body = clean_text_for_email(body) or "No content available for today."
        
        print(f"📧 Preparing email with subject: {safe_subject[:50]}...")
        
        # Create message with plain policy (more compatible)
        msg = EmailMessage(policy=policy.default)
        msg["Subject"] = safe_subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        
        # Set content as plain text with explicit charset
        msg.set_content(safe_body, charset='utf-8')
        
        # Send email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
            
            # Send the message - let smtplib handle the encoding
            text = msg.as_string()
            server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], text.encode('utf-8'))
            
        print("✅ Email sent successfully!")
        
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        print(f"Subject length: {len(subject) if subject else 0}")
        print(f"Body length: {len(body) if body else 0}")
        # Print first 100 chars of body for debugging
        if body:
            print(f"Body preview: {repr(body[:100])}")
        raise RuntimeError(f"Failed to send email: {e}")

def main():
    """Main function to generate and send the daily digest."""
    print("🚀 Starting daily digest generation...")
    try:
        # 1. Get Progress
        progress = get_progress()
        chunk_id_to_fetch = f"chunk_{progress['current_chunk']}"
        print(f"📌 Reading progress: Current chunk is {progress['current_chunk']}")

        # 2. Fetch Data from Pinecone (with auto-skip for empty chunks)
        index = pc.Index(INDEX_NAME)

        attempts = 0
        max_attempts = 25  # safety limit
        current_chunk_text = ""
        current_chunk_vector = None
        while attempts < max_attempts:
            fetch_response = index.fetch(ids=[chunk_id_to_fetch])
            current_chunk_data = fetch_response.vectors.get(chunk_id_to_fetch)
            if current_chunk_data is None:
                print(f"ℹ️ {chunk_id_to_fetch} not found, advancing progress...")
            else:
                current_chunk_text = (current_chunk_data.metadata or {}).get('text', '')
                current_chunk_vector = getattr(current_chunk_data, 'values', None)

            if current_chunk_text and len(current_chunk_text.strip()) >= 20 and current_chunk_vector:
                print("📚 Fetched today's chunk from Pinecone.")
                break

            # Advance to next chunk and try again
            progress['current_chunk'] += 1
            save_progress(progress)
            chunk_id_to_fetch = f"chunk_{progress['current_chunk']}"
            attempts += 1
            print(f"↪️ Skipping empty/invalid chunk. Trying {chunk_id_to_fetch} (attempt {attempts})...")

        if not current_chunk_text or not current_chunk_vector:
            raise ValueError("No suitable chunk with content found after multiple attempts")

        # Clean the chunk text early to prevent propagation of problematic characters
        current_chunk_text = clean_text_for_email(current_chunk_text)

        # 3. Run Synthesis Engine
        synthesis_result = index.query(
            vector=current_chunk_vector,
            top_k=2, # Find the top 2 most similar chunks (one is the chunk itself)
            include_metadata=True
        )
        # The second result is the most similar, different chunk
        if not synthesis_result.matches or len(synthesis_result.matches) < 2:
            print("ℹ️ Not enough matches found for related concept; proceeding without it.")
            similar_chunk_text = ""
        else:
            similar_chunk_text = synthesis_result.matches[1].metadata.get('text', '')
            similar_chunk_text = clean_text_for_email(similar_chunk_text)
        print("🧠 Found a related concept for synthesis.")

        # 4. Generate Content with Gemini
        print("✍️ Generating insights with Gemini...")
        # Guard against empty content
        if not current_chunk_text or len(current_chunk_text.strip()) < 20:
            raise ValueError("Current chunk text is empty or too short for generation")
        has_related = bool(similar_chunk_text and similar_chunk_text.strip())

        if has_related:
            prompt = f"""
You are an AI reading assistant. You are given all required content below. Do not ask for inputs.
Write a Daily Wisdom Digest in plain text only. Use only standard ASCII characters, no special Unicode characters.

Main Text for Today:
```text
{current_chunk_text}
```

Related Concept from the Book:
```text
{similar_chunk_text}
```

Produce these sections (plain text, no markdown formatting beyond headings):
- Quote of the Day: one powerful sentence from the Main Text
- Actionable Insight: one concrete action the reader can take today
- Reflective Prompt: one open-ended question
- Connecting the Dots: 3-5 sentences explaining the connection between Main Text and Related Concept

Important: Use only standard punctuation marks (', ", -, ...) and avoid special Unicode characters.
"""
        else:
            prompt = f"""
You are an AI reading assistant. You are given the main text below. Do not ask for inputs.
Write a Daily Wisdom Digest in plain text only. Use only standard ASCII characters, no special Unicode characters.

Main Text for Today:
```text
{current_chunk_text}
```

Produce these sections (plain text, no markdown formatting beyond headings):
- Quote of the Day: one powerful sentence from the Main Text
- Actionable Insight: one concrete action the reader can take today
- Reflective Prompt: one open-ended question
- Key Takeaway: 3-5 sentences summarizing the core idea from the Main Text

Important: Use only standard punctuation marks (', ", -, ...) and avoid special Unicode characters.
"""
        response = generative_model.generate_content(prompt)
        email_body = response.text
        
        # Clean the generated content as well
        email_body = clean_text_for_email(email_body)

        # 5. Send the Email
        email_subject = "Your Daily Wisdom Digest"
        send_email(email_subject, email_body)

        # 6. Update Progress
        progress['current_chunk'] += 1
        save_progress(progress)
        print(f"📈 Progress updated. Next chunk will be {progress['current_chunk']}.")

        print("🎉 Daily digest process completed successfully!")

    except Exception as e:
        print(f"❌ A fatal error occurred: {e}")
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        # Exit non-zero so GitHub Actions job fails
        sys.exit(1)

if __name__ == "__main__":
    main()