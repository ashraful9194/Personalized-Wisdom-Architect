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

## ⚙️ Getting Started

*(This section would be updated to include instructions on configuring email settings.)*

1.  Clone the repository.
2.  Set up the Python virtual environment and install dependencies.
3.  Configure your email credentials in a `.env` file.
4.  Run the scheduler and the web app.

---

## 🤝 How to Contribute

Contributions are welcome! If you have ideas for new features or improvements, please open an issue or submit a pull request.
