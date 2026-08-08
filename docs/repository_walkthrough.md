# Agentio Repository Walkthrough for Video

This document explains the project structure, each main folder, and each important file so you can present the repository clearly in a video or presentation.

---

## 1. What this project does

Agentio is a financial data AI assistant for Apple’s SEC filings and financial statements. It:

- ingests PDF and Excel financial documents
- splits them into chunks
- creates embeddings and a vector search index
- enforces role-based access control (RBAC)
- protects against prompt injection attacks
- answers user questions through a chat interface
- learns from user feedback

In simple terms, the project is like a secure AI assistant that answers financial questions while making sure users only see the data they are allowed to access.

---

## 2. Main folder structure

- [backend](../backend) — the complete backend logic
- [frontend](../frontend) — the web chat UI
- [data](../data) — raw company financial documents
- [processed](../processed) — generated chunk, embedding, and understanding files
- [docs](../docs) — diagrams and project documentation
- [test_e2e.py](../test_e2e.py) — end-to-end API test script

---

## 3. Folder-by-folder explanation

### Folder: backend

This is the core of the project. It contains the server, agent logic, ingestion pipeline, RBAC rules, security logic, and understanding generation.

### Folder: backend/agent

This folder contains the “brain” of the system.

- [backend/agent/orchestrator.py](../backend/agent/orchestrator.py)
  - This is the main orchestrator class.
  - It loads the processed chunks and embeddings.
  - It checks user input for prompt injection.
  - It retrieves relevant chunks.
  - It builds a context and sends it to OpenAI.
  - It validates the answer to prevent data leakage.
  - It also integrates feedback from users.

### Folder: backend/feedback

This folder handles user feedback.

- [backend/feedback/manager.py](../backend/feedback/manager.py)
  - Stores feedback in a JSON file.
  - Saves positive/negative ratings and corrections.
  - Helps the system learn from bad answers.
  - Provides a few-shot example mechanism for future similar questions.

### Folder: backend/ingestion

This folder is responsible for turning raw financial files into searchable knowledge.

- [backend/ingestion/pdf_parser.py](../backend/ingestion/pdf_parser.py)
  - Reads PDF files.
  - Extracts text and tables using PyMuPDF and pdfplumber.
  - Detects the likely financial category of each page.
  - Creates structured chunks for later retrieval.

- [backend/ingestion/excel_parser.py](../backend/ingestion/excel_parser.py)
  - Reads Excel files.
  - Extracts sheet content.
  - Detects the type of financial data in the sheet.
  - Converts sheet data into chunks.

- [backend/ingestion/chunker.py](../backend/ingestion/chunker.py)
  - Splits large text into smaller chunks.
  - Keeps chunk size controlled using token-based logic.
  - Adds overlap between chunks so context is preserved.

- [backend/ingestion/run_ingestion.py](../backend/ingestion/run_ingestion.py)
  - This is the main ingestion pipeline.
  - It runs all parsing steps.
  - It sanitizes content.
  - It chunks the data.
  - It generates embeddings.
  - It saves everything into the processed folder.

### Folder: backend/rbac

This folder implements security and access control.

- [backend/rbac/models.py](../backend/rbac/models.py)
  - Defines the data structures for users, tokens, login requests, queries, and data chunks.
  - Used by FastAPI for request validation and response modeling.

- [backend/rbac/auth.py](../backend/rbac/auth.py)
  - Handles JWT-based authentication.
  - Verifies passwords.
  - Creates access tokens.
  - Decodes tokens to identify the current user.

- [backend/rbac/enforcer.py](../backend/rbac/enforcer.py)
  - Implements role-based access rules.
  - Determines which categories a role can see.
  - Filters out restricted chunks before the model sees them.
  - Also checks the answer for leakage after generation.

### Folder: backend/security

This folder contains safety mechanisms.

- [backend/security/injection_guard.py](../backend/security/injection_guard.py)
  - Detects prompt injection attempts.
  - Looks for suspicious patterns and role confusion prompts.
  - Sanitizes document content to remove instructions embedded inside files.
  - Validates model output for leakage of internal instructions or sensitive data.

### Folder: backend/understanding

This folder creates precomputed summaries and metadata to make the assistant faster.

- [backend/understanding/generator.py](../backend/understanding/generator.py)
  - Creates file summaries.
  - Extracts key financial metrics.
  - Builds a category index.
  - Generates schema notes for Excel sheets.
  - Produces a glossary of important financial terms.

### Folder: frontend

This contains the web interface.

- [frontend/index.html](../frontend/index.html)
  - The main page structure for login and chat UI.

- [frontend/styles.css](../frontend/styles.css)
  - Styles the app with a dark theme and glass-style design.

- [frontend/app.js](../frontend/app.js)
  - Handles login, chat, API calls, rendering messages, and feedback UI.
  - Sends user messages to the backend.
  - Displays the assistant’s answer and sources.

### Folder: data

This folder contains the raw financial input documents.

- PDF annual reports
- Excel quarterly financial statements

These are the source files used by the ingestion pipeline.

### Folder: processed

This folder contains generated output files created after ingestion.

- [processed/chunks/all_chunks.json](../processed/chunks/all_chunks.json)
  - All parsed and chunked document content.

- [processed/embeddings/chunk_ids.json](../processed/embeddings/chunk_ids.json)
  - Maps embeddings to chunk IDs.

- [processed/understanding/file_summaries.json](../processed/understanding/file_summaries.json)
  - Summaries of each file.

- [processed/understanding/key_metrics.json](../processed/understanding/key_metrics.json)
  - Extracted important financial metrics.

- [processed/feedback/feedback_store.json](../processed/feedback/feedback_store.json)
  - Stores user feedback.

---

## 4. Important top-level files

### [README.md](../README.md)

This is the project overview and setup guide.
It explains:
- what the project is
- how to install dependencies
- how to run ingestion
- how to start the backend
- how to log in as demo users

### [backend/main.py](../backend/main.py)

This is the FastAPI server entry point.
It provides the API routes for:
- login
- fetching user info
- answering queries
- submitting feedback
- serving the frontend

### [backend/config.py](../backend/config.py)

This file acts as the central configuration hub.
It defines:
- project paths
- OpenAI model settings
- JWT settings
- chunk size and overlap
- data categories
- role restrictions
- demo users

### [test_e2e.py](../test_e2e.py)

This file tests the main functionality end to end.
It checks:
- authentication
- normal queries
- RBAC behavior
- prompt injection defense
- feedback flow

---

## 5. How the code works end to end

Here is the flow of the application:

1. The user opens the web app.
2. The user logs in with a role such as CEO, CTO, or CFO.
3. The frontend sends the query to the backend API.
4. The backend validates the JWT token.
5. The agent checks the input for prompt injection.
6. The retriever finds relevant chunks from the processed knowledge base.
7. The RBAC enforcer removes restricted categories for the user’s role.
8. The LLM generates an answer using only the safe context.
9. The response is validated again for leakage.
10. The answer is returned to the frontend and shown to the user.

---

## 6. Video narration script

You can use this as a voiceover guide:

### Intro
“Welcome to Agentio, a secure AI assistant for financial data. In this project, we combine document ingestion, retrieval, RBAC security, and a chat interface to answer questions about Apple’s financial documents.”

### Project overview
“This repository is divided into three major parts: the backend, the frontend, and the processed data store. The backend is responsible for parsing documents, enforcing role-based access, and generating answers. The frontend allows users to interact with the assistant. The processed folder stores the generated knowledge base.”

### Backend explanation
“The backend folder is the core of the project. Inside it, the agent orchestrator acts like the system brain. It receives a query, checks for prompt injection, retrieves relevant chunks, and sends the context to the language model.”

### Security explanation
“One of the most important parts of this project is security. The RBAC modules restrict what each role can access, and the injection guard prevents malicious prompts from bypassing the system.”

### Data ingestion explanation
“The ingestion pipeline reads PDFs and Excel files, converts them into chunks, and creates embeddings so the system can search them efficiently. This part is what turns raw documents into searchable knowledge.”

### Frontend explanation
“The frontend is a simple web app that lets users log in and chat with the assistant. It sends requests to the API and displays the answer, sources, and feedback controls.”

### Closing
“In short, Agentio combines AI, document processing, security, and a web interface into one system that answers finance questions safely and intelligently.”

---

## 7. Short presentation summary

If you need a very short version for a video intro, say this:

“Agentio is a secure financial AI assistant. The backend ingests financial documents, chunks them into searchable knowledge, enforces role-based access control, and uses an LLM to answer user questions. The frontend provides a chat experience, while the processed folder stores embeddings, summaries, and feedback data.”
