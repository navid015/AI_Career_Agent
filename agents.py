"""
Multi-agent system for cover letter generation and resume optimization.

Architecture: Orchestrator + 4 specialized agents
  1. JDAnalyzerAgent     - extracts structured info from a job description
  2. ResumeAnalyzerAgent  - extracts structured info from a resume
  3. CoverLetterAgent     - writes a tailored letter using both analyses
  4. ResumeOptimizerAgent - suggests targeted edits to the resume

Each agent has a focused system prompt and a single responsibility. The
orchestrator (`CareerAgent.run`) sequences calls and passes context forward.
"""

from __future__ import annotations

import json
import re
from typing import Any

from anthropic import Anthropic


def _extract_json(text: str) -> dict[str, Any]:
    """Robustly pull a JSON object out of an LLM response."""
    text = text.strip()
    # Strip markdown fences if present
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: grab the outermost { ... }
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {}


class CareerAgent:
    """Orchestrator that coordinates four specialized sub-agents."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        if not api_key:
            raise ValueError("An Anthropic API key is required.")
        self.client = Anthropic(api_key=api_key)
        self.model = model

    # ---------- low-level helper ----------

    def _call(self, system: str, user: str, max_tokens: int = 2048) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Concatenate all text blocks (defensive against multi-block responses)
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()

    # ---------- Agent 1: JD Analyzer ----------

    def analyze_jd(self, jd: str) -> dict[str, Any]:
        system = (
            "You are a job description analyzer. Read the JD and extract structured "
            "information. Output ONLY a valid JSON object, no preamble, no markdown. "
            "Schema:\n"
            "{\n"
            '  "company": string,\n'
            '  "role": string,\n'
            '  "seniority": string,\n'
            '  "key_requirements": [string],\n'
            '  "tech_stack": [string],\n'
            '  "soft_skills": [string],\n'
            '  "must_haves": [string],\n'
            '  "nice_to_haves": [string],\n'
            '  "tone": string\n'
            "}\n"
            "If a field is unclear, use a sensible default like \"Unknown\" or []."
        )
        out = self._call(system, f"Job description:\n\n{jd}", max_tokens=1500)
        return _extract_json(out)

    # ---------- Agent 2: Resume Analyzer ----------

    def analyze_resume(self, resume_text: str) -> dict[str, Any]:
        system = (
            "You are a resume parser. Extract structured info as a JSON object only. "
            "No preamble, no markdown.\n"
            "Schema:\n"
            "{\n"
            '  "name": string,\n'
            '  "email": string,\n'
            '  "current_role": string,\n'
            '  "years_experience": string,\n'
            '  "skills": [string],\n'
            '  "key_projects": [{"name": string, "description": string, "impact": string}],\n'
            '  "achievements": [string],\n'
            '  "education": string\n'
            "}\n"
            "Use \"\" or [] when something is missing. Do not fabricate."
        )
        out = self._call(system, f"Resume:\n\n{resume_text}", max_tokens=1800)
        return _extract_json(out)

    # ---------- Agent 3: Cover Letter Writer ----------

    def write_cover_letter(
        self,
        jd_text: str,
        resume_text: str,
        jd_analysis: dict[str, Any],
        resume_analysis: dict[str, Any],
    ) -> str:
        system = (
            "You are an expert cover letter writer. Write a tailored, specific, "
            "human-sounding cover letter that:\n"
            "- Opens with genuine interest tied to the company/role (not generic)\n"
            "- Connects 2-3 of the candidate's concrete experiences to the JD's top requirements\n"
            "- Uses real metrics or project names from the resume where available\n"
            "- Sounds conversational and confident, not robotic or AI-flavored\n"
            "- Is 3-4 paragraphs, roughly 300-350 words\n"
            "- Closes with a clear, confident next-step line\n\n"
            "Output ONLY the body of the letter. Do NOT include a date, addresses, "
            "\"Dear Hiring Manager,\" line, or sign-off — those are added by the PDF "
            "generator. Start directly with the first body paragraph."
        )
        user = (
            f"JOB DESCRIPTION:\n{jd_text}\n\n"
            f"JD ANALYSIS:\n{json.dumps(jd_analysis, indent=2)}\n\n"
            f"RESUME:\n{resume_text}\n\n"
            f"RESUME ANALYSIS:\n{json.dumps(resume_analysis, indent=2)}\n\n"
            "Write the letter body now."
        )
        return self._call(system, user, max_tokens=2048)

    # ---------- Agent 4: Resume Optimizer ----------

    def suggest_resume_changes(
        self,
        resume_text: str,
        jd_analysis: dict[str, Any],
        resume_analysis: dict[str, Any],
    ) -> str:
        system = (
            "You are a resume optimization expert. Compare the resume to the JD and "
            "give actionable, honest suggestions. Never invent experience the candidate "
            "doesn't have.\n\n"
            "Output in this exact markdown format:\n\n"
            "## Match Score\n"
            "**X/10** — one-line summary\n\n"
            "## Critical Gaps\n"
            "Bulleted list of missing keywords or skills the JD requires that aren't in "
            "the resume. If the candidate likely has the skill but didn't mention it, "
            "say so explicitly.\n\n"
            "## Suggested Edits\n"
            "For each suggestion, use this block:\n\n"
            "**Section:** which section of the resume\n"
            "**Current:** brief excerpt of what's there now\n"
            "**Suggested:** the rewrite\n"
            "**Why:** the reason it improves the match\n\n"
            "Provide 3-6 high-impact edits. Skip trivial ones.\n\n"
            "## Keywords to Incorporate\n"
            "Bulleted list of JD keywords missing from the resume that should be worked "
            "in (only if true to the candidate's experience).\n\n"
            "## Strengths to Emphasize\n"
            "What's already strong and should be moved up, repeated in the summary, or "
            "highlighted with metrics."
        )
        user = (
            f"JOB ANALYSIS:\n{json.dumps(jd_analysis, indent=2)}\n\n"
            f"RESUME ANALYSIS:\n{json.dumps(resume_analysis, indent=2)}\n\n"
            f"FULL RESUME:\n{resume_text}\n\n"
            "Provide your optimization report."
        )
        return self._call(system, user, max_tokens=2500)

    # ---------- Orchestrator ----------

    def run(self, jd_text: str, resume_text: str, progress=None) -> dict[str, Any]:
        """Run the full pipeline. `progress` is an optional callable(fraction, desc)."""

        def _p(frac: float, desc: str) -> None:
            if progress is not None:
                progress(frac, desc=desc)

        _p(0.20, "Analyzing job description...")
        jd_analysis = self.analyze_jd(jd_text)

        _p(0.40, "Analyzing resume...")
        resume_analysis = self.analyze_resume(resume_text)

        _p(0.65, "Drafting cover letter...")
        letter = self.write_cover_letter(jd_text, resume_text, jd_analysis, resume_analysis)

        _p(0.90, "Generating resume suggestions...")
        suggestions = self.suggest_resume_changes(resume_text, jd_analysis, resume_analysis)

        return {
            "jd_analysis": jd_analysis,
            "resume_analysis": resume_analysis,
            "cover_letter": letter,
            "suggestions": suggestions,
            "candidate_name": resume_analysis.get("name") or "Candidate",
            "company": jd_analysis.get("company") or "the Company",
            "role": jd_analysis.get("role") or "the Role",
        }
