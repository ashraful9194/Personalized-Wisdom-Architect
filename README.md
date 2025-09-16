# 🧠 My Personalized Wisdom Architect

![Status: Operational](https://img.shields.io/badge/status-MVP_Operational-brightgreen) ![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg) ![Automation](https://img.shields.io/github/actions/workflow/status/ashraful9194/PDF-Reader-Agent/daily_digest.yml?label=Daily%20Digest&style=flat-square) ![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

### Why I Built This

Like many people, I have a large collection of self-help and non-fiction PDF books on my hard drive that I've always wanted to read. I found it difficult to make consistent progress, and the sheer volume was overwhelming. So, I decided to build a solution for myself.

This project is my personal AI agent that acts as an intelligent reading companion. It takes my library of books and transforms the passive act of reading into an active, daily system for learning and growth. Every morning, it reads with me, helps me understand complex ideas, and ensures the knowledge actually sticks.

-----

## ✨ My Favorite Features

  * **Smart Daily Readings:** Instead of just sending random pages, the agent analyzes a book and splits it into semantically coherent chunks. This means every email I receive contains a complete, self-contained idea, making it much easier to learn.

  * **Connecting the Dots:** This is the agent's "magic." As I read a new book, it uses a vector database to find related concepts from *all the other books I've ever read*. It then explains the connection, helping me build a latticework of knowledge.

  * **Actionable Takeaways:** Every digest includes a concrete action I can take and a reflective question. This pushes me to not just consume the information, but to actively apply it to my own life.

  * **Personal Vocabulary Builder:** The agent identifies advanced words from the text and includes them in the daily email, helping me expand my vocabulary effortlessly as I read.

  * **Fully Autonomous:** The entire system runs automatically on a schedule using GitHub Actions. I don't have to do anything except check my email in the morning.

-----

## 🔧 How It's Built (The Tech Stack)

To bring this idea to life, I used a modern, serverless tech stack that is both powerful and extremely cost-effective.

  * **AI & Embeddings:** Google Gemini (`gemini-1.fum Flash`, `text-embedding-004`)
  * **Vector Database (Memory):** Pinecone
  * **Backend & Logic:** Python
  * **Automation & CI/CD:** GitHub Actions
  * **Email Delivery:** `smtplib` (via Gmail)
  * **PDF Processing:** `PyPDF2`
  * **Text Splitting:** `langchain_text_splitters`

-----

## 🛣️ Project Status & Future Roadmap

**Current Status:** The core MVP (Minimum Viable Product) of the Personalized Wisdom Architect is fully operational. The agent can successfully ingest a PDF book, store its knowledge, and deliver automated daily digests with AI-generated insights and synthesis.

This project is under active development, and I have a clear vision for its future. My goal is to evolve this agent into an even more powerful and interactive learning companion.

**What's Next:**

* **✨ Interactive UI:** Develop a simple web interface using **Gradio** or **Streamlit** to manage the book library and view progress.
* **📚 Multi-Book Library:** Add the ability to manage and switch between multiple concurrent books.
* **📈 Progress Tracking:** Implement a system to track reading streaks and visualize progress through the library.
* **👁️ Bionic Reading Toggle:** Integrate a feature to turn the Bionic Reading formatting on or off based on user preference.
* **🎧 Audio Summaries:** Explore generating short, daily audio summaries of the key insights using a text-to-speech API.

----

## ⚙️ How to Run Your Own Version

If you'd like to set up your own version of this agent, here’s how.

### 1\. Prerequisites

  * A GitHub account
  * Python 3.9+ installed
  * Accounts for Google (for Gemini API and Gmail) and Pinecone

### 2\. Clone the Repository

```bash
git clone https://github.com/ashraful9194/PDF-Reader-Agent.git
cd PDF-Reader-Agent
```

### 3\. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4\. Set Up Secrets & Credentials

You'll need to get three secret keys:

  * **`GEMINI_API_KEY`:** From Google AI Studio.
  * **`PINECONE_API_KEY`:** From your Pinecone project dashboard.
  * **`GMAIL_APP_PASSWORD`:** A 16-digit App Password from your Google Account security settings.

Create a `.env` file in your project root for **local testing**:

```
GEMINI_API_KEY="your-gemini-key-here"
PINECONE_API_KEY="your-pinecone-key-here"
GMAIL_APP_PASSWORD="your16digitapppasswordhere"
```

For deployment, add these same keys to your repository's **GitHub Secrets** (`Settings > Secrets and variables > Actions`).

### 5\. Configure the Scripts

  * In `daily_digest.py`, change the `SENDER_EMAIL` and `RECEIVER_EMAIL` variables to your own Gmail address.
  * In `ingest.py`, ensure the Pinecone `REGION` variable matches your project's region.

-----

## 🚀 Usage

### 1\. "Teaching" the Agent a New Book

1.  Place your PDF book in the project directory (e.g., `book.pdf`).
2.  In `ingest.py`, update the `pdf_path` variable to point to your book's filename.
3.  Run the script locally: `python ingest.py`.

### 2\. Receiving Daily Digests

1.  Once a book is ingested, the scheduled GitHub Action will run automatically every morning.
2.  Just check your email for your daily digest\!

-----

## 🤝 How to Contribute

While this is a personal project, I'm open to ideas and contributions\! Feel free to open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License.
