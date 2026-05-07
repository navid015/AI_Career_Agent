

from __future__ import annotations

import os
import re
import tempfile

import gradio as gr
from dotenv import load_dotenv

from agents import CareerAgent
from pdf_generator import generate_cover_letter_pdf
from resume_parser import parse_resume

# Load .env if present (no-op in production where env vars are set directly)
load_dotenv()

DEFAULT_MODEL = "claude-sonnet-4-6"
MODEL_CHOICES = [
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-haiku-4-5-20251001",
]

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()) or "candidate"
    return name[:50]


def process(jd_text, resume_file, model, progress=gr.Progress()):
    if not API_KEY:
        raise gr.Error(
            "Server is not configured: ANTHROPIC_API_KEY is missing from the "
            "environment. The application owner needs to set it."
        )
    if not jd_text or not jd_text.strip():
        raise gr.Error("Please paste a job description.")
    if not resume_file:
        raise gr.Error("Please upload your resume (PDF, DOCX, or TXT).")

    progress(0.05, desc="Parsing resume...")
    resume_path = resume_file if isinstance(resume_file, str) else resume_file.name
    resume_text = parse_resume(resume_path)
    if len(resume_text.strip()) < 50:
        raise gr.Error(
            "Could not extract meaningful text from your resume. If it is a "
            "scanned PDF, please try a DOCX or TXT version."
        )

    agent = CareerAgent(api_key=API_KEY, model=model or DEFAULT_MODEL)
    result = agent.run(jd_text=jd_text, resume_text=resume_text, progress=progress)

    progress(0.95, desc="Building PDF...")
    pdf_path = os.path.join(
        tempfile.gettempdir(),
        f"cover_letter_{_safe_filename(result['candidate_name'])}.pdf",
    )
    generate_cover_letter_pdf(
        letter_body=result["cover_letter"],
        candidate_name=result["candidate_name"],
        company=result["company"],
        role=result["role"],
        output_path=pdf_path,
        candidate_email=result["resume_analysis"].get("email") or None,
    )

    progress(1.0, desc="Done")
    summary = (
        f"### Generated for **{result['candidate_name']}**\n"
        f"**Role:** {result['role']} &nbsp;·&nbsp; **Company:** {result['company']}"
    )
    return summary, result["cover_letter"], pdf_path, result["suggestions"]


# ---------------------------------------------------------------------------
# Custom styling
# ---------------------------------------------------------------------------

CSS = """
/* Center the app and constrain its width */
.gradio-container {
    max-width: 1550px !important;
    width: 95vw !important;
    margin: 0 auto !important;
    padding: 1.25rem 2rem 2rem 2rem !important;
}

/* Hide default Gradio footer */
footer {display: none !important;}

/* ---------- Hero header ---------- */
.app-header {
    text-align: center;
    padding: 1.25rem 0 1.5rem 0;
}
.app-header h1 {
    font-size: 2.75rem;
    font-weight: 800;
    margin: 0 0 0.5rem 0;
    background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
}
.app-header p {
    color: #94a3b8;
    font-size: 1.05rem;
    margin: 0 auto 1rem auto;
    max-width: 680px;
    line-height: 1.55;
}
.pipeline-badge {
    display: inline-block;
    background: rgba(99, 102, 241, 0.12);
    color: #a5b4fc;
    padding: 0.5rem 1.1rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 500;
    border: 1px solid rgba(99, 102, 241, 0.3);
}

/* ---------- Card containers ---------- */
.card {
    background: var(--background-fill-secondary) !important;
    border: 1px solid var(--border-color-primary) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    min-height: 100%;
}

/* ---------- Section labels ---------- */
.section-label {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #a5b4fc;
    margin: 0 0 1rem 0;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--border-color-primary);
}

/* ---------- Primary button ---------- */
.generate-btn button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 1rem !important;
    margin-top: 0.75rem !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3) !important;
}
.generate-btn button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45) !important;
}

/* ---------- Empty state styling ---------- */
.empty-state {
    text-align: center;
    color: #64748b;
    padding: 2rem 0;
    font-style: italic;
}

/* ---------- Privacy footer ---------- */
.privacy-note {
    text-align: center;
    color: #64748b;
    font-size: 0.82rem;
    margin-top: 2rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--border-color-primary);
}

/* Make rows space columns out properly */
.gradio-container .gap {
    gap: 1.25rem !important;
}
"""


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="AI Career Agent") as demo:
        # Hero header
        gr.HTML(
            """
            <div class="app-header">
                <h1>AI Career Agent</h1>
                <p>Paste a job description, upload your resume, and get a tailored
                cover letter plus a targeted resume optimization report — powered
                by a multi-agent pipeline.</p>
                <span class="pipeline-badge">
                    JD Analyzer → Resume Analyzer → Cover Letter Writer → Resume Optimizer
                </span>
            </div>
            """
        )

        with gr.Row(equal_height=False):
            # ------------------ Input column ------------------
            with gr.Column(scale=1, elem_classes=["card"]):
                gr.HTML('<div class="section-label">📋 Your Inputs</div>')

                jd_input = gr.Textbox(
                    label="Job Description",
                    lines=12,
                    placeholder="Paste the full job description here...",
                )

                resume_input = gr.File(
                    label="Resume (PDF, DOCX, or TXT)",
                    file_types=[".pdf", ".docx", ".txt"],
                    type="filepath",
                )

                with gr.Accordion("⚙️ Advanced settings", open=False):
                    model_input = gr.Dropdown(
                        label="Model",
                        choices=MODEL_CHOICES,
                        value=DEFAULT_MODEL,
                        info="Sonnet — balanced. Opus — highest quality. Haiku — fastest & cheapest.",
                    )

                run_btn = gr.Button(
                    "✨ Generate Cover Letter & Suggestions",
                    variant="primary",
                    size="lg",
                    elem_classes=["generate-btn"],
                )

            # ------------------ Output column ------------------
            with gr.Column(scale=1, elem_classes=["card"]):
                gr.HTML('<div class="section-label">✨ Results</div>')

                summary_output = gr.Markdown(
                    value="<div class='empty-state'>Your generated content will appear here.</div>"
                )

                with gr.Tabs():
                    with gr.Tab("📄 Cover Letter"):
                        cover_letter_output = gr.Textbox(
                            label="Cover Letter (editable)",
                            lines=14,
                            placeholder="Your personalized cover letter will appear here...",
                        )
                        pdf_output = gr.File(label="📥 Download as PDF")

                    with gr.Tab("🎯 Resume Suggestions"):
                        suggestions_output = gr.Markdown(
                            value="<div class='empty-state'>Targeted resume suggestions will appear here.</div>"
                        )

        # Footer
        gr.HTML(
            '<div class="privacy-note">'
            'Your resume and job description are sent to the Anthropic API for '
            'processing and are not stored by this application.'
            '</div>'
        )

        run_btn.click(
            process,
            inputs=[jd_input, resume_input, model_input],
            outputs=[summary_output, cover_letter_output, pdf_output, suggestions_output],
        )

    return demo


if __name__ == "__main__":
    if not API_KEY:
        print("⚠️  ANTHROPIC_API_KEY is not set.")
        print("    Create a .env file in this directory with:")
        print("    ANTHROPIC_API_KEY=sk-ant-...")
        print()
    demo = build_ui()
    demo.launch(
        theme=gr.themes.Soft(primary_hue="indigo", neutral_hue="slate"),
        css=CSS,
    )