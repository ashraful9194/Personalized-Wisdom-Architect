import os
import json
import smtplib
import sys
import unicodedata
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import yaml
import google.generativeai as genai
from pinecone import Pinecone

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

SENDER_EMAIL = "ashraful9194@gmail.com"  # <-- šMPORTANT: Change to your email
RECEIVER_EMAIL = "ashraful9194@gmail.com" # <-- IMPORTANT: Change to your email

INDEX_NAME = "how-to-win-friends-and-influence-people"
PROGRESS_FILE = "progress.json"

# --- Initialize Clients ---
pc = Pinecone(api_key=PINECONE_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
generative_model = genai.GenerativeModel('gemini-1.5-flash')

def get_total_chunks_from_pinecone(index) -> int:
    """Return total number of vectors (chunks) stored in the Pinecone index.
    Falls back to 0 if unavailable.
    """
    try:
        stats = index.describe_index_stats()
        # Prefer namespaces sum if available, otherwise total_vector_count
        if hasattr(stats, "namespaces") and isinstance(stats.namespaces, dict) and stats.namespaces:
            return sum((ns.get("vector_count", 0) for ns in stats.namespaces.values()))
        if hasattr(stats, "total_vector_count"):
            return int(stats.total_vector_count)
        # Some client versions return dict
        if isinstance(stats, dict):
            if "namespaces" in stats and isinstance(stats["namespaces"], dict) and stats["namespaces"]:
                return sum((ns.get("vector_count", 0) for ns in stats["namespaces"].values()))
            if "total_vector_count" in stats:
                return int(stats["total_vector_count"])
    except Exception:
        pass
    return 0

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

def send_html_email(subject, html_content):
    """Sends a beautiful HTML email using smtplib."""
    try:
        # Clean credentials
        safe_sender_email = clean_text_for_email(SENDER_EMAIL)
        safe_receiver_email = clean_text_for_email(RECEIVER_EMAIL)
        safe_gmail_password = clean_text_for_email(GMAIL_APP_PASSWORD)
        safe_subject = clean_text_for_email(subject) or "Your Daily Wisdom Digest"
        
        print(f"📧 Preparing beautiful HTML email...")
        
        # Create multipart message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = safe_subject
        msg['From'] = safe_sender_email
        msg['To'] = safe_receiver_email
        
        # Create HTML part
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(safe_sender_email, safe_gmail_password)
            server.send_message(msg)
            
        print("✅ Beautiful HTML email sent successfully!")
        
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        print(f"Subject length: {len(subject) if subject else 0}")
        print(f"HTML content length: {len(html_content) if html_content else 0}")
        raise RuntimeError(f"Failed to send email: {e}")

def main():
    """Main function to generate and send the daily digest."""
    print("🚀 Starting daily digest generation...")
    try:
        # 1. Get Progress
        progress = get_progress()
        start_chunk = progress['current_chunk']
        print(f"📌 Reading progress: Start chunk is {start_chunk}")

        # 2. Fetch Data from Pinecone: gather up to 1 consecutive valid chunks
        index = pc.Index(INDEX_NAME)
        desired_chunks = 1
        gathered_texts = []
        gathered_vectors = []

        attempts = 0
        max_attempts = 100  # safety limit across skips
        current_cursor = start_chunk
        while attempts < max_attempts and len(gathered_texts) < desired_chunks:
            chunk_id = f"chunk_{current_cursor}"
            fetch_response = index.fetch(ids=[chunk_id])
            current_chunk_data = fetch_response.vectors.get(chunk_id)
            if current_chunk_data is None:
                print(f"ℹ️ {chunk_id} not found, skipping...")
            else:
                text = (current_chunk_data.metadata or {}).get('text', '')
                vector = getattr(current_chunk_data, 'values', None)
                if text and len(text.strip()) >= 20 and vector:
                    gathered_texts.append(text)
                    gathered_vectors.append(vector)
                    print(f"📚 Added {chunk_id} to today's batch ({len(gathered_texts)}/{desired_chunks}).")
                else:
                    print(f"ℹ️ {chunk_id} has insufficient content, skipping...")

            current_cursor += 1
            attempts += 1

        if not gathered_texts:
            raise ValueError("No suitable chunks with content found after multiple attempts")

        # Combine fetched texts; remember how many consumed
        consumed_chunks = len(gathered_texts)
        current_chunk_text = "\n\n---\n\n".join(gathered_texts)
        # Use the first valid vector for similarity search fallback
        current_chunk_vector = gathered_vectors[0] if gathered_vectors else None

        # Clean the chunk text early to prevent propagation of problematic characters
        current_chunk_text = clean_text_for_email(current_chunk_text)

        # 3. Skip related-concept synthesis (legacy feature removed)

        # 4. Generate Content with Gemini
        print("✍️ Generating insights with Gemini...")
        # Guard against empty content
        if not current_chunk_text or len(current_chunk_text.strip()) < 20:
            raise ValueError("Current chunk text is empty or too short for generation")

        # Load daily digest prompt templates from prompts.yaml
        with open("prompts.yaml", "r") as yf:
            prompts_config = yaml.safe_load(yf) or {}
        daily_digest_prompts = prompts_config.get("daily_digest", {})

        # Build enhanced prompt (JSON output with summary + vocabulary) and call model
        enhanced_tpl = daily_digest_prompts.get("enhanced_json", "")
        # Avoid Python str.format conflicts with JSON braces by using simple token replacement
        enhanced_prompt = enhanced_tpl.replace("{full_text}", current_chunk_text)
        response = generative_model.generate_content(enhanced_prompt)
        raw_text = response.text or "{}"

        # Attempt to parse JSON; fall back to minimal structure if needed
        try:
            parsed = json.loads(raw_text)
        except Exception:
            # Some models may prepend text; try to isolate JSON using a simple heuristic
            try:
                start_idx = raw_text.find("{")
                end_idx = raw_text.rfind("}")
                parsed = json.loads(raw_text[start_idx:end_idx+1]) if start_idx != -1 and end_idx != -1 else {}
            except Exception:
                parsed = {}

        summary_text = str(parsed.get("summary", "")).strip()
        vocabulary_items = parsed.get("vocabulary", []) if isinstance(parsed.get("vocabulary"), list) else []

        # 5. Prepare subject range for header and email subject
        if consumed_chunks == 1:
            subject_range = f"Chapter {start_chunk}"
        else:
            subject_range = f"Chapters {start_chunk}-{start_chunk + consumed_chunks - 1}"

        # 6. Create Beautiful HTML Email including progress, summary, vocabulary, and full text
        # Determine total chunks automatically from Pinecone (fallback to env if set)
        auto_total = get_total_chunks_from_pinecone(index)
        env_total = 0
        try:
            env_val = os.getenv("BOOK_TOTAL_CHUNKS", "").strip()
            env_total = int(env_val) if env_val else 0
        except Exception:
            env_total = 0
        total_chunks = env_total or auto_total

        end_chunk = start_chunk + consumed_chunks - 1
        if total_chunks > 0 and end_chunk <= total_chunks:
            percent = max(0, min(100, round((end_chunk / total_chunks) * 100)))
            progress_html = f"""
            <div style='margin:18px 0;'>
              <div style='font-weight:600; margin-bottom:8px; color:#1f2937;'>Reading Progress · {percent}%</div>
              <div style='height:16px; background:#eef2ff; border-radius:999px; overflow:hidden; box-shadow: inset 0 1px 2px rgba(0,0,0,0.06);'>
                <div style='width:{percent}%; height:100%; background:linear-gradient(90deg,#667eea,#764ba2);'></div>
              </div>
              <div style='font-size:12px; color:#6b7280; margin-top:6px;'>{end_chunk} / {total_chunks} chapters</div>
            </div>
            """
        else:
            progress_html = f"""
            <div style='margin:18px 0;'>
              <div style='display:inline-block; background:#eef2ff; color:#4338ca; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:600;'>
                Chapters completed: {end_chunk}
              </div>
            </div>
            """
        def render_vocab_html(items):
            if not items:
                return "<p>No vocabulary items identified today.</p>"
            rows = []
            for it in items:
                term = str(it.get("term", "")).strip()
                meaning = str(it.get("meaning_simple", "")).strip()
                difficulty = str(it.get("difficulty", "")).strip()
                if not term:
                    continue
                rows.append(f"<tr><td style='padding:8px 12px; border-bottom:1px solid #eee; font-weight:600;'>{term}</td><td style='padding:8px 12px; border-bottom:1px solid #eee;'>{meaning}</td><td style='padding:8px 12px; border-bottom:1px solid #eee; color:#555;'>{difficulty}</td></tr>")
            if not rows:
                return "<p>No vocabulary items identified today.</p>"
            return """
            <table style='width:100%; border-collapse:collapse; margin-top:8px;'>
              <thead>
                <tr>
                  <th align='left' style='padding:8px 12px; border-bottom:2px solid #ddd;'>Term</th>
                  <th align='left' style='padding:8px 12px; border-bottom:2px solid #ddd;'>Simple meaning</th>
                  <th align='left' style='padding:8px 12px; border-bottom:2px solid #ddd;'>Difficulty</th>
                </tr>
              </thead>
              <tbody>
            """ + "".join(rows) + """
              </tbody>
            </table>
            """

        full_text_html = current_chunk_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
        summary_html = (summary_text or "No summary generated today.").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")
        vocab_html = render_vocab_html(vocabulary_items)

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8"/>
          <meta name="viewport" content="width=device-width, initial-scale=1"/>
          <title>Daily Wisdom Digest</title>
        </head>
        <body style="margin:0; padding:0; background:#f6f7fb; color:#333; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji','Segoe UI Emoji','Segoe UI Symbol';">
          <div style="max-width:720px; margin:0 auto; background:#fff; box-shadow:0 6px 24px rgba(0,0,0,0.08);">
            <div style="padding:24px 28px; background:linear-gradient(135deg,#667eea,#764ba2); color:#fff;">
              <h1 style="margin:0; font-size:22px; font-weight:600;">Daily Wisdom Digest</h1>
              <div style="opacity:0.9; font-size:14px; margin-top:6px;">{subject_range}</div>
            </div>
            <div style="padding:20px 24px;">
              {progress_html}
              <h2 style="margin:10px 0 8px; font-size:18px; color:#2c3e50;">Summary</h2>
              <p style="margin:0; line-height:1.6;">{summary_html}</p>
              <h2 style="margin:20px 0 8px; font-size:18px; color:#2c3e50;">Vocabulary</h2>
              {vocab_html}
              <h2 style="margin:24px 0 8px; font-size:18px; color:#2c3e50;">Full Text</h2>
              <div style="padding:12px 14px; background:#fafbff; border:1px solid #eef1ff; border-radius:8px; line-height:1.6; white-space:normal;">{full_text_html}</div>
            </div>
            <div style="padding:18px 24px; color:#6b7280; font-size:12px; background:#f9fafb; text-align:center;">Generated by ReadEaser AI • Keep reading, keep growing 🌱</div>
          </div>
        </body>
        </html>
        """

        # 7. Send the Email
        if consumed_chunks == 1:
            subject_range = f"Chapter {start_chunk}"
        else:
            subject_range = f"Chapters {start_chunk}-{start_chunk + consumed_chunks - 1}"
        email_subject = f"Daily Wisdom Digest - {subject_range}"
        send_html_email(email_subject, html_content)

        # 8. Update Progress (advance by number of consumed chunks)
        progress['current_chunk'] = start_chunk + consumed_chunks
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