# Prepwise AI — Interview Question Generator

A polished, responsive Streamlit application for interview preparation. Create role- and skill-focused question sets, review answer guides and coaching tips, complete a guided mock interview, save useful questions, and download a PDF practice pack.

## Features

- **Question Studio:** Choose a job role, experience level, interview format, skills, question count, and difficulty.
- **AI generation:** Uses the OpenAI Chat Completions API when an API key is configured. The model can be selected with `OPENAI_MODEL` (default: `gpt-4o-mini`).
- **Demo mode:** Without an API key, a built-in question bank provides usable technical, HR, scenario, and coding practice.
- **Answer guides:** Sample answer outlines, useful keywords, and actionable interview tips for every question.
- **Mock interview:** Work through one prompt at a time, draft your response, reveal the guide, and track completion.
- **Dashboard and library:** Review recent practice activity and save, search, and remove favorite questions.
- **PDF export:** Download a clean, printable practice pack.
- **Responsive styling:** Custom blue, violet, and cyan glass-inspired design, dark appearance option, subtle motion, and mobile-friendly layouts.
- **Local persistence:** Session history and saved questions are stored in `data/interview_data.json`.

## Run locally on Windows with VS Code

1. Install [Python 3.10 or later](https://www.python.org/downloads/) and [VS Code](https://code.visualstudio.com/). During Python setup, enable **Add Python to PATH**.
2. Open this project folder in VS Code.
3. Open **Terminal → New Terminal** and create a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, either use Command Prompt with `.venv\Scripts\activate.bat` or run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the current PowerShell terminal and activate again.

4. Install the dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Start the app:

   ```powershell
   python -m streamlit run app.py
   ```

6. Streamlit opens the app in your browser, usually at `http://localhost:8501`. Stop it with **Ctrl+C** in the terminal.

## Enable AI-generated questions (optional)

The application works without an API key. To enable personalized AI generation, set your key in the terminal before launching Streamlit:

**PowerShell**

```powershell
$env:OPENAI_API_KEY="your-api-key"
python -m streamlit run app.py
```

**Command Prompt**

```bat
set OPENAI_API_KEY=your-api-key
python -m streamlit run app.py
```

Alternatively, create `.streamlit/secrets.toml` (this file is git-ignored) containing:

```toml
OPENAI_API_KEY = "your-api-key"
```

Optional environment settings:

- `OPENAI_MODEL`: model name accepted by your OpenAI-compatible API; default is `gpt-4o-mini`.
- `OPENAI_BASE_URL`: optional base URL for an OpenAI-compatible API. Omit it for the standard OpenAI endpoint.

**Keep your API key private.** Do not commit `.streamlit/secrets.toml` or a key in source code. If AI generation fails, the app falls back to the built-in question bank and shows an explanatory notice.

## Project structure

```text
ai-interview-question-generator/
├── app.py                     # Streamlit app and application logic
├── assets/
│   └── style.css              # Responsive theme, components, and animation styles
├── data/
│   └── interview_data.json    # Created automatically for local practice history
├── .streamlit/
│   └── secrets.toml           # Optional; create locally, never commit
├── .env.example               # Optional environment-variable reference
├── .gitignore
├── requirements.txt
└── README.md
```

## Notes

- The app's stored practice sessions are local to the machine and project folder where Streamlit is running. Back up `data/interview_data.json` if you want to preserve history before moving or deleting the project.
- Internet access is needed for the optional AI API and to load the web font. The sample-question mode does not require an API connection.
- The PDF export uses ReportLab, installed through `requirements.txt`.
- If using an OpenAI-compatible service, confirm that the selected model supports JSON object response format.
