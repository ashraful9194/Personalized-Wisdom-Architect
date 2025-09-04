import os
import json
import smtplib
import sys
import unicodedata
import re
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

def create_html_email_template(quote, insight, prompt, connection_or_takeaway, chunk_number):
    """
    Creates a beautiful HTML email template for the daily digest.
    """
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Wisdom Digest</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Georgia', serif; background-color: #f8f9fa; color: #333;">
    <!-- Main Container -->
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 300; letter-spacing: 1px;">
                📚 Daily Wisdom Digest
            </h1>
            <p style="color: #e8eaf6; margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">
                Chapter {chunk_number} • Your Reading Journey Continues
            </p>
        </div>

        <!-- Quote Section -->
        <div style="padding: 40px 30px 30px 30px; border-left: 5px solid #667eea; margin: 0; background-color: #f8f9ff;">
            <div style="display: flex; align-items: flex-start; margin-bottom: 15px;">
                <span style="font-size: 36px; color: #667eea; line-height: 1; margin-right: 15px;">💡</span>
                <h2 style="color: #667eea; margin: 0; font-size: 20px; font-weight: 600;">Quote of the Day</h2>
            </div>
            <blockquote style="margin: 0; padding: 0; font-style: italic; font-size: 18px; line-height: 1.6; color: #444;">
                "{quote}"
            </blockquote>
        </div>

        <!-- Actionable Insight -->
        <div style="padding: 30px; background-color: #ffffff;">
            <div style="display: flex; align-items: flex-start; margin-bottom: 15px;">
                <span style="font-size: 32px; color: #4caf50; line-height: 1; margin-right: 15px;">🎯</span>
                <h2 style="color: #4caf50; margin: 0; font-size: 20px; font-weight: 600;">Actionable Insight</h2>
            </div>
            <p style="margin: 0; font-size: 16px; line-height: 1.7; color: #555;">
                {insight}
            </p>
        </div>

        <!-- Reflective Prompt -->
        <div style="padding: 30px; background-color: #fff8e1; border-top: 3px solid #ffc107;">
            <div style="display: flex; align-items: flex-start; margin-bottom: 15px;">
                <span style="font-size: 32px; color: #ff9800; line-height: 1; margin-right: 15px;">🤔</span>
                <h2 style="color: #ff9800; margin: 0; font-size: 20px; font-weight: 600;">Reflective Prompt</h2>
            </div>
            <p style="margin: 0; font-size: 16px; line-height: 1.7; color: #555; font-style: italic;">
                {prompt}
            </p>
        </div>

        <!-- Connection/Key Takeaway -->
        <div style="padding: 30px; background-color: #e8f5e8; border-top: 3px solid #2e7d32;">
            <div style="display: flex; align-items: flex-start; margin-bottom: 15px;">
                <span style="font-size: 32px; color: #2e7d32; line-height: 1; margin-right: 15px;">🔗</span>
                <h2 style="color: #2e7d32; margin: 0; font-size: 20px; font-weight: 600;">Key Connection</h2>
            </div>
            <p style="margin: 0; font-size: 16px; line-height: 1.7; color: #555;">
                {connection_or_takeaway}
            </p>
        </div>

        <!-- Footer -->
        <div style="background-color: #37474f; padding: 30px; text-align: center;">
            <p style="color: #b0bec5; margin: 0 0 10px 0; font-size: 14px;">
                Keep reading, keep growing! 🌱
            </p>
            <p style="color: #78909c; margin: 0; font-size: 12px;">
                Generated with ❤️ by ReadEaser AI • Continue your journey tomorrow
            </p>
            <div style="margin-top: 20px;">
                <div style="display: inline-block; background-color: #667eea; color: white; padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: 500;">
                    📈 Progress: Chapter {chunk_number}
                </div>
            </div>
        </div>
        
    </div>

    <!-- Mobile Responsiveness -->
    <style>
        @media only screen and (max-width: 600px) {{
            .container {{ width: 100% !important; }}
            .padding {{ padding: 20px !important; }}
            h1 {{ font-size: 24px !important; }}
            h2 {{ font-size: 18px !important; }}
        }}
    </style>
</body>
</html>
"""
    return html_template

def parse_ai_response(response_text):
    """
    Parse the AI response to extract individual sections.
    """
    # Clean the response first
    response_text = clean_text_for_email(response_text)
    
    # Initialize sections with defaults
    sections = {
        'quote': 'Wisdom comes from within.',
        'insight': 'Take time today to reflect on what you have learned.',
        'prompt': 'How can you apply today\'s learning to improve your life?',
        'connection': 'Every piece of knowledge builds upon the last, creating a foundation for growth.'
    }
    
    try:
        # Split by common section headers (case insensitive)
        patterns = {
            'quote': r'(?:quote of the day|quote)[:\-\s]+(.*?)(?=\n.*?(?:actionable|insight|reflective|key|connecting)|\Z)',
            'insight': r'(?:actionable insight|insight)[:\-\s]+(.*?)(?=\n.*?(?:reflective|quote|key|connecting)|\Z)',
            'prompt': r'(?:reflective prompt|prompt)[:\-\s]+(.*?)(?=\n.*?(?:connecting|key|quote|actionable)|\Z)',
            'connection': r'(?:connecting the dots|key takeaway|connection)[:\-\s]+(.*?)(?=\n.*?(?:quote|actionable|reflective)|\Z)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                sections[key] = match.group(1).strip()
        
    except Exception as e:
        print(f"⚠️ Error parsing AI response: {e}")
        # Keep default sections if parsing fails
    
    return sections

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

Produce these sections (plain text, no markdown formatting):

Quote of the Day: [Extract one powerful, memorable sentence from the Main Text - keep it under 150 characters]

Actionable Insight: [One concrete, specific action the reader can take today based on the main text - be practical and specific]

Reflective Prompt: [One thought-provoking, open-ended question that encourages deep thinking about the concepts]

Connecting the Dots: [Explain in 3-5 sentences how the Main Text and Related Concept connect and reinforce each other's messages]

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

Produce these sections (plain text, no markdown formatting):

Quote of the Day: [Extract one powerful, memorable sentence from the Main Text - keep it under 150 characters]

Actionable Insight: [One concrete, specific action the reader can take today based on the main text - be practical and specific]

Reflective Prompt: [One thought-provoking, open-ended question that encourages deep thinking about the concepts]

Key Takeaway: [Summarize the core idea from the Main Text in 3-5 sentences, focusing on practical wisdom]

Important: Use only standard punctuation marks (', ", -, ...) and avoid special Unicode characters.
"""
        response = generative_model.generate_content(prompt)
        ai_response = response.text
        
        # Clean the generated content
        ai_response = clean_text_for_email(ai_response)

        # 5. Parse AI Response into sections
        sections = parse_ai_response(ai_response)
        
        # 6. Create Beautiful HTML Email
        html_content = create_html_email_template(
            quote=sections['quote'],
            insight=sections['insight'],
            prompt=sections['prompt'],
            connection_or_takeaway=sections['connection'],
            chunk_number=progress['current_chunk']
        )

        # 7. Send the Email
        email_subject = f"Daily Wisdom Digest - Chapter {progress['current_chunk']}"
        send_html_email(email_subject, html_content)

        # 8. Update Progress
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