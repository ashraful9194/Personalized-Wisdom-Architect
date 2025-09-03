# 📖 ReadEaser: Your AI-Powered Reading Companion

![Status: In Development](https://img.shields.io/badge/status-in_development-blue)
![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

Feeling overwhelmed by your digital reading list? ReadEaser is an intelligent agent designed to help you conquer those unread books and documents effortlessly. Instead of letting PDFs gather dust on your hard drive, ReadEaser analyzes them, breaks them into digestible daily parts, and delivers them straight to your inbox.

This project transforms reading from a chore into a delightful daily habit, using AI to make every session engaging, motivating, and efficient.

---

## ✨ Key Features

* **🚀 Daily Digestible Chunks:** ReadEaser automatically partitions large books into smaller, manageable parts. Every day, it sends you the next part of the book, helping you make steady progress without feeling overwhelmed.

* **💡 Motivational Hooks & Summaries:** Each daily email starts with a short, AI-generated "motivational hook" to pique your interest, along with a concise summary of the part's key points. You'll know exactly what you're about to read and why it's important.

* **👁️ Bionic Reading Integration:** Read faster and with greater focus! The main text in each email is formatted using the bionic reading method, which bolds the initial letters of words to guide your eyes and improve comprehension speed.

* **🧠 Complex Word Simplifier:** Don't let difficult vocabulary slow you down. The agent identifies complex words within the daily part and provides simple, easy-to-understand definitions, expanding your knowledge as you read.

---

## 🔧 How It Works

The workflow is designed to be simple and automated:

1.  **Upload & Analyze:** Start by uploading a PDF book to the application. The agent analyzes the document and programmatically divides it into daily reading chunks.
2.  **Schedule:** The system schedules a daily job to process the next unread chunk of your book.
3.  **Receive & Read:** Every day, you receive a beautifully formatted email containing your motivational hook, summary, bionic reading text, and simplified word definitions. Just open, read, and repeat!

![Demo GIF of the Daily Email](https://i.imgur.com/your-email-demo.gif)

---

## 🛠️ Tech Stack & Future Roadmap

This project leverages a powerful stack to bring your reading to life:

* **AI:** `smolagents`, `Ollama` (`llama3:8b`), `litellm`
* **Backend:** Python, `schedule` (for daily jobs), `smtplib` (for email)
* **UI:** Gradio
* **PDF Processing:** PyPDF

> This is just the beginning! Future plans include progress tracking, integration with services like Pocket and Kindle, and even generating audio summaries for you to listen to on the go.

---

## Book Ingestion Script

The project now includes a robust book ingestion script (`ingest_book.py`) that processes PDF books and stores them in a Pinecone vector database for semantic search and retrieval.

### Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables:**
   Create a `.env` file in the project root with the following variables:
   ```
   PINECONE_API_KEY=your_pinecone_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Pinecone Setup:**
   - Sign up for Pinecone at https://www.pinecone.io/
   - Create a new project in the AWS ap-south-1 region
   - Get your API key from the Pinecone console

4. **Google Gemini Setup:**
   - Get your API key from Google AI Studio: https://makersuite.google.com/app/apikey

### Usage

1. **Place your PDF book** in the project directory as `book.pdf` (or modify the path in the script)

2. **Run the ingestion script:**
   ```bash
   python ingest_book.py
   ```

The script will:
- Create a Pinecone index named "wisdom-architect" if it doesn't exist
- Extract all text from the PDF using PyPDF2
- Use Gemini AI to create thematic chunks of the content
- Generate vector embeddings for each chunk using Gemini's embedding model
- Store the chunks in Pinecone with metadata including book title and chunk number

### Features

- **Automatic Index Creation:** Creates Pinecone index with proper specifications for text-embedding-004 model
- **Thematic Chunking:** Uses AI to intelligently split book content into meaningful chunks
- **Robust Error Handling:** Includes fallback chunking and comprehensive error handling
- **Progress Tracking:** Clear console output showing processing progress
- **Metadata Storage:** Stores rich metadata with each vector for better retrieval

### Output

The script provides detailed console output including:
- Index creation status
- PDF processing progress
- Chunk creation statistics
- Upload progress for each chunk
- Final summary of processed content

---

## ⚙️ Getting Started

*(This section would be updated to include instructions on configuring email settings.)*

1.  Clone the repository.
2.  Set up the Python virtual environment and install dependencies.
3.  Configure your email credentials in a `.env` file.
4.  Run the scheduler and the web app.

---

## 🤝 How to Contribute

Contributions are welcome! If you have ideas for new features or improvements, please open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
