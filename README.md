---
title: AI Career Agent
emoji: 📝
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 5.0.1
app_file: app.py
pinned: false
license: mit
short_description: Multi-agent cover letter writer and resume optimizer
---

# AI Career Agent

A multi-agent application that turns a job description and your resume into:

- a **tailored cover letter** (text + downloadable PDF)
- a **resume optimization report** with concrete suggested edits, missing keywords, and strengths to emphasize

Built with the Anthropic API and Gradio. Designed to deploy on Hugging Face Spaces.

## Architecture

The system uses an **orchestrator + specialized agents** pattern:

```
                   ┌──────────────────────┐
   JD + Resume ──▶ │   CareerAgent (orch) │
                   └──────────┬───────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  JD Analyzer        Resume Analyzer       Cover Letter Writer
  (structured        (structured           (uses both analyses)
   extraction)        extraction)
                                                    │
                                                    ▼
                                           Resume Optimizer
                                           (gap analysis +
                                            edit suggestions)
```

Each agent has a focused system prompt and a single responsibility. The orchestrator (`CareerAgent.run` in `agents.py`) sequences the calls and threads context between them.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Gradio UI and the entry point Hugging Face runs |
| `agents.py` | Orchestrator and the four specialized agents |
| `resume_parser.py` | Extracts plain text from PDF, DOCX, or TXT resumes |
| `pdf_generator.py` | Renders the cover letter to a PDF with ReportLab |
| `requirements.txt` | Pinned Python deps |

## Deploy to Hugging Face Spaces

1. **Create a new Space** at https://huggingface.co/new-space
   - SDK: **Gradio**
   - Hardware: **CPU basic** is enough (all heavy lifting happens in the Anthropic API)

2. **Upload these files** (or push via `git`):
   ```
   app.py
   agents.py
   resume_parser.py
   pdf_generator.py
   requirements.txt
   README.md
   ```

3. **Add the API key as a secret**
   - Space → **Settings** → **Variables and secrets** → **New secret**
   - Name: `ANTHROPIC_API_KEY`
   - Value: your key from https://console.anthropic.com

4. The Space will build automatically. First boot takes ~1–2 min.

### Pushing via git

```bash
git clone https://huggingface.co/spaces/<your-username>/<your-space>
cd <your-space>
# copy the project files into this directory, then:
git add .
git commit -m "Initial commit: AI Career Agent"
git push
```

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your real key
python app.py
```

Then open the printed URL (usually `http://127.0.0.1:7860`).

## Configuration

- **Model selection** is exposed in the UI under *Advanced settings*. Default is `claude-sonnet-4-6` (good balance of cost/quality). Switch to `claude-opus-4-6` for the highest-quality letters, or `claude-haiku-4-5-20251001` for the cheapest.
- **API key**: loaded from the `ANTHROPIC_API_KEY` environment variable only. Locally, put it in a `.env` file (see `.env.example`); on Hugging Face Spaces, set it as a Space secret. End users never see or supply a key.

## Privacy

Your resume and job description are sent to the Anthropic API for processing. They are not stored by this Space, and no logs of inputs are kept on disk. The generated PDF is written to a temp directory and served as a download.

## License

MIT