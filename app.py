from __future__ import annotations

import html
import json
import os
import random
import re
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from openai import OpenAI
except ImportError:  # The no-key demo remains usable without the optional SDK.
    OpenAI = None  # type: ignore[assignment,misc]

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DATA_FILE = DATA_DIR / "interview_data.json"

st.set_page_config(
    page_title="Prepwise AI | Interview practice",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROLES = [
    "Python Developer", "Java Developer", "Web Developer", "Frontend Developer",
    "Backend Developer", "Full-Stack Developer", "AI/ML Engineer", "Data Analyst",
    "Data Scientist", "Software Engineer", "DevOps Engineer", "Product Manager",
    "UX/UI Designer", "QA Engineer", "Cybersecurity Analyst", "Other",
]
SKILL_OPTIONS = [
    "Python", "Java", "JavaScript", "TypeScript", "HTML", "CSS", "React", "Node.js",
    "SQL", "PostgreSQL", "Machine Learning", "Data Analysis", "APIs", "Git", "Docker",
    "Cloud", "System Design", "Communication", "Leadership", "Problem Solving",
]
EXPERIENCE = ["Beginner", "Intermediate", "Advanced"]
INTERVIEW_TYPES = ["Mixed", "Technical", "HR", "Coding"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]


def _fresh_data() -> dict[str, Any]:
    return {"sessions": [], "saved_questions": [], "mock_interviews_completed": 0}


def load_data() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        return _fresh_data()
    try:
        value = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return _fresh_data()
        defaults = _fresh_data()
        defaults.update(value)
        return defaults
    except (OSError, json.JSONDecodeError):
        return _fresh_data()


def save_data(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="prepwise_", suffix=".json", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temp_path, DATA_FILE)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    try:
        return str(st.secrets.get("OPENAI_API_KEY", "")).strip()
    except Exception:
        return ""


def clean_question(item: dict[str, Any], index: int, default_difficulty: str) -> dict[str, Any]:
    question = str(item.get("question", "")).strip()
    if not question:
        raise ValueError(f"Question {index + 1} was empty")
    keywords = item.get("keywords", [])
    tips = item.get("tips", [])
    if isinstance(keywords, str):
        keywords = [part.strip() for part in keywords.split(",") if part.strip()]
    if isinstance(tips, str):
        tips = [tips]
    return {
        "id": f"q-{datetime.now().timestamp():.0f}-{index}-{random.randint(100, 999)}",
        "question": question,
        "category": str(item.get("category", "General")),
        "difficulty": str(item.get("difficulty", default_difficulty)),
        "answer": str(item.get("answer", "A strong response is specific, structured, and grounded in a real example. Explain your reasoning, the choices you made, and the result.")),
        "keywords": [str(x) for x in keywords][:8] if isinstance(keywords, list) else [],
        "tips": [str(x) for x in tips][:5] if isinstance(tips, list) else [],
    }


def _sample_question_bank(role: str, skills: list[str], level: str, interview_type: str, difficulty: str, count: int) -> list[dict[str, Any]]:
    skill = skills[0] if skills else role.split()[0]
    skill2 = skills[1] if len(skills) > 1 else "your main technology"
    level_context = {"Beginner": "in a project or course", "Intermediate": "in a production project", "Advanced": "at scale in a production environment"}.get(level, "in a project")
    templates: list[tuple[str, str, str, list[str], list[str]]] = [
        ("Technical", f"How does {skill} work, and what problem does it solve in a {role} role?", f"Start with the purpose of {skill}, outline its core mechanism, then connect it to a concrete {role} use case. Mention one trade-off or limitation.", [skill, "core concepts", "use case", "trade-off"], ["Define the concept before diving into details.", "Use a small example and explain when you would choose another approach."]),
        ("Technical", f"Tell me about a time you used {skill} {level_context}. What did you build and what would you improve?", f"Use a concise STAR structure: explain the project context, your responsibility, how you applied {skill}, and the measurable outcome. Close with one improvement you would make next time.", [skill, "ownership", "impact", "reflection"], ["Keep the focus on your own contribution.", "Include a result or a clear signal of success."]),
        ("Technical", f"A {role} application built with {skill} has become slow. How would you investigate and improve it?", "First reproduce and measure the slowdown, then use profiling and logs to locate the bottleneck. Form a hypothesis, make one targeted change, and compare before-and-after metrics. Consider correctness and regression tests.", ["profiling", "baseline", "bottleneck", "measurement", "regression test"], ["Avoid guessing before collecting evidence.", "Explain how you would verify the improvement."]),
        ("Scenario", f"You discover a serious bug in a feature using {skill2} shortly before release. What would you do?", "Assess user impact and release risk, reproduce the issue, and communicate early with the team. Agree on a safe fix or rollback, add a regression test, and document follow-up work. Prioritize user safety over protecting a deadline.", ["impact assessment", "communication", "mitigation", "regression test"], ["Show calm prioritization and transparent communication.", "Mention when you would escalate or roll back."]),
        ("Technical", f"How would you test a feature that combines {skill} and {skill2}?", "Describe a layered strategy: unit tests for logic, integration tests for boundaries between components, and a small number of end-to-end tests for critical user paths. Include edge cases, test data, and how failures are diagnosed.", ["unit tests", "integration tests", "edge cases", "end-to-end"], ["Choose tests based on risk rather than maximizing test count.", "Explain what should be mocked and what should remain real."]),
        ("Technical", f"What trade-offs would you consider when choosing {skill} over an alternative for a {role} project?", f"Compare suitability, team familiarity, performance, maintainability, ecosystem maturity, and operational cost. Tie the decision to the project's constraints instead of claiming one tool is always best. State what evidence could change your choice.", [skill, "constraints", "maintainability", "trade-offs"], ["Name the context behind your recommendation.", "Show that you can revisit a decision when evidence changes."]),
        ("HR", "Tell me about a time you received critical feedback. How did you respond?", "Choose a specific example, explain what the feedback was, and show how you clarified it and acted on it. Finish with the change you made and what improved. Demonstrate openness without becoming defensive.", ["self-awareness", "action", "growth", "outcome"], ["Use a real, work-relevant example.", "Focus on what you changed rather than judging the person who gave feedback."]),
        ("HR", f"Why are you interested in this {role} position, and what would you bring to the team?", f"Connect your interest in the role to the team's work, then support your fit with two relevant strengths or examples, such as experience with {skill}. Finish with the impact you hope to make and a thoughtful question for the interviewer.", [role, skill, "motivation", "evidence"], ["Avoid generic claims; anchor your answer in the job description.", "Keep the answer focused and conversational."]),
        ("HR", "Describe a disagreement with a teammate and how you reached a resolution.", "Set the context briefly, explain the differing views fairly, and describe how you listened, used evidence, and aligned on a decision. Share the outcome and what you learned about collaboration.", ["listening", "evidence", "collaboration", "resolution"], ["Show respect for the other person's perspective.", "Choose an example with a constructive outcome."]),
        ("HR", "What is one professional strength you rely on, and when has it made a difference?", "Name a job-relevant strength and prove it with a concise example. Explain the action you took and the result, then connect it to how you would contribute in this role.", ["strength", "example", "impact", "role fit"], ["Be specific rather than listing several strengths.", "Support the claim with an observable result."]),
        ("Coding", f"Write a function that finds the first non-repeating character in a string. Explain its time and space complexity.", "Count character frequencies in one pass, then scan the string in order and return the first character whose count is one. This is O(n) time and O(k) space, where k is the number of distinct characters. Clarify behavior for an empty string or no unique character.", ["frequency map", "two passes", "O(n)", "edge cases"], ["Clarify input assumptions and expected return value first.", "Walk through a short example and test an empty input."]),
        ("Coding", f"Given a list of integers and a target, return the indices of two values that add up to the target.", "Scan once while storing each value's index in a hash map. For each value, check whether target minus value is already present; if so, return the two indices. This gives O(n) expected time and O(n) space. Clarify duplicate and no-solution behavior.", ["hash map", "complement", "O(n)", "duplicates"], ["Ask whether one solution is guaranteed.", "Do not reuse the same element twice."]),
        ("Coding", f"How would you remove duplicate values from a collection while preserving the original order?", "Track values in a set and append a value to a result list only the first time it appears. This is O(n) expected time and O(n) additional space. Discuss whether values are hashable and how equality is defined.", ["set", "stable order", "O(n)", "hashability"], ["State the ordering requirement explicitly.", "Consider empty input and repeated values."]),
        ("Scenario", f"An API endpoint used by your {role} team intermittently returns errors. How would you debug it?", "Establish the error rate and affected requests, correlate logs and traces by request ID, inspect recent changes and dependency health, and reproduce safely. Mitigate user impact first, then fix the root cause and add monitoring or tests to prevent recurrence.", ["observability", "request IDs", "mitigation", "root cause"], ["Separate immediate mitigation from the permanent fix.", "Mention how you will confirm recovery."]),
        ("Technical", f"How do you keep a {role} codebase maintainable as features and contributors grow?", "Keep modules cohesive, make interfaces clear, automate formatting and tests, document important decisions, and review changes constructively. Refactor incrementally when complexity starts slowing delivery, while protecting behavior with tests.", ["modularity", "tests", "code review", "incremental refactoring"], ["Give an example of a maintainability practice you have used.", "Balance clean design with delivery needs."]),
        ("HR", "Tell me about a time you had to learn something quickly to complete a task.", f"Describe the goal and time constraint, how you broke the topic into learnable pieces, and how you applied the learning—perhaps with {skill}. Finish with the result and how you validated your understanding.", ["learning plan", "initiative", "application", "validation"], ["Show how you decided what to learn first.", "Mention a concrete outcome."]),
        ("Scenario", f"A stakeholder asks for a change that conflicts with the current technical plan. How would you handle it as a {role}?", "Clarify the underlying user need and constraints, explain the technical implications in plain language, and present options with costs and risks. Collaborate on a decision, record it, and revisit it if new evidence emerges.", ["clarifying questions", "options", "trade-offs", "alignment"], ["Do not frame the discussion as technical versus nontechnical.", "Show how you make the trade-off understandable."]),
        ("Technical", f"What security or privacy risks should you consider when working with {skill}?", "Identify the data and trust boundaries first, then consider least privilege, input validation, secret management, dependency updates, and logging that avoids exposing sensitive information. Explain how you would test and monitor the controls.", ["least privilege", "validation", "secrets", "data privacy"], ["Tie risks to the actual data and system boundaries.", "Mention prevention and detection."]),
        ("HR", "Describe a project that did not go as planned. What did you learn?", "Be candid about the challenge, own your part without blaming others, and explain how you responded. Focus on the lesson, the adjustment you made, and how it improved later work.", ["accountability", "adaptability", "lesson", "improvement"], ["Pick a real setback with a useful learning outcome.", "Keep the explanation constructive."]),
        ("Coding", "How would you merge two sorted lists into one sorted list efficiently?", "Use two pointers, one for each list. Repeatedly append the smaller current value and advance that pointer, then append the remaining tail. The time complexity is O(n + m); output storage is O(n + m), or O(1) extra space if the required output representation permits in-place merging.", ["two pointers", "sorted inputs", "O(n + m)", "remaining tail"], ["Explain why the result remains sorted at each step.", "Test when either input is empty."]),
        ("Technical", f"How would you explain a complex {skill} concept to a teammate who is new to it?", "Start from the teammate's goal and existing knowledge, use a small concrete example, and introduce terminology only when needed. Check understanding, invite questions, and point to a minimal example they can run or inspect.", ["audience", "analogy", "example", "feedback"], ["Adapt your explanation to the listener.", "Check understanding instead of assuming it."]),
        ("Scenario", f"You have several urgent tasks and limited time. How do you decide what to work on first?", "Compare user impact, urgency, dependencies, and risk. Confirm priorities with stakeholders when needed, break the highest-value work into a clear next step, and communicate what will be delayed and why.", ["impact", "prioritization", "dependencies", "communication"], ["Make the criteria explicit.", "Reassess if new information changes the risk."]),
        ("Technical", f"What would you monitor after shipping a feature built with {skill}?", "Choose signals that show both system health and user outcomes: errors, latency, resource use, and a relevant success metric. Set useful thresholds, avoid noisy alerts, and define who responds and how to roll back if needed.", ["latency", "errors", "user outcome", "alerting"], ["Connect metrics to the feature's purpose.", "Explain what action an alert should trigger."]),
        ("HR", "What kind of team environment helps you do your best work?", "Describe a few specific conditions—such as clear goals, candid communication, and room to take ownership—and explain how you contribute to creating them. Show flexibility across working styles.", ["communication", "ownership", "teamwork", "adaptability"], ["Keep the answer positive and job-relevant.", "Explain what you personally do to support the environment."]),
    ]
    if interview_type == "Technical":
        templates = [t for t in templates if t[0] in {"Technical", "Scenario"}]
    elif interview_type == "HR":
        templates = [t for t in templates if t[0] == "HR"]
    elif interview_type == "Coding":
        templates = [t for t in templates if t[0] in {"Coding", "Technical"}]
    random.shuffle(templates)
    results = []
    used: set[str] = set()
    for i in range(count):
        category, prompt, answer, keywords, tips = templates[i % len(templates)]
        if prompt in used:
            prompt = f"{prompt} What would you change for a {difficulty.lower()}-level solution?"
            answer += " For a more complex variation, discuss constraints, edge cases, and the trade-offs in your chosen approach."
        used.add(prompt)
        results.append(clean_question({"question": prompt, "category": category, "difficulty": difficulty, "answer": answer, "keywords": keywords, "tips": tips}, i, difficulty))
    return results


def generate_with_ai(role: str, level: str, interview_type: str, skills: list[str], difficulty: str, count: int, api_key: str) -> list[dict[str, Any]]:
    if OpenAI is None:
        raise RuntimeError("The OpenAI Python package is not installed")
    client_options: dict[str, Any] = {"api_key": api_key, "timeout": 40.0, "max_retries": 1}
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    if base_url:
        client_options["base_url"] = base_url
    client = OpenAI(**client_options)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    instructions = f"""Create exactly {count} original, realistic interview questions for a {role} candidate.
Experience: {level}. Interview format: {interview_type}. Difficulty: {difficulty}.
Relevant skills: {', '.join(skills) if skills else 'general role skills'}.
Balance domain-specific fundamentals with practical, scenario-based questions. Match categories to the format. Avoid duplicates and trivia. Each sample answer should be concise, accurate, teach a clear answer structure, and suit the selected level. Keywords should be short phrases. Tips should be actionable.
Return ONLY valid JSON with this exact shape: {{"questions":[{{"question":"...","category":"Technical|HR|Coding|Scenario","difficulty":"Easy|Medium|Hard","answer":"...","keywords":["..."],"tips":["..."]}}]}}"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert interview coach. Follow the requested JSON format exactly."},
            {"role": "user", "content": instructions},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )
    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    raw_questions = parsed.get("questions", [])
    if not isinstance(raw_questions, list) or not raw_questions:
        raise ValueError("The AI response did not include a questions list")
    questions = [clean_question(item, i, difficulty) for i, item in enumerate(raw_questions[:count]) if isinstance(item, dict)]
    if len(questions) < count:
        raise ValueError(f"The AI returned {len(questions)} of {count} requested questions")
    return questions


def make_pdf(session: dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=0.7 * inch, leftMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", parent=styles["Title"], textColor=colors.HexColor("#6257e8"), alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="Question", parent=styles["Heading3"], textColor=colors.HexColor("#242b45"), spaceBefore=9, spaceAfter=5))
    styles.add(ParagraphStyle(name="SmallMeta", parent=styles["BodyText"], textColor=colors.HexColor("#667085"), fontSize=9, spaceAfter=5))
    story = [Paragraph("Prepwise AI", styles["BrandTitle"]), Paragraph(f"Interview practice pack · {html.escape(session.get('role', 'Interview'))}", styles["Heading2"]), Paragraph(f"{html.escape(session.get('experience', ''))} · {html.escape(session.get('interview_type', ''))} · {html.escape(session.get('difficulty', ''))}", styles["SmallMeta"]), Spacer(1, 10)]
    for index, q in enumerate(session.get("questions", []), start=1):
        group = [Paragraph(f"{index}. {html.escape(q['question'])}", styles["Question"]), Paragraph(f"{html.escape(q.get('category', 'General'))} · {html.escape(q.get('difficulty', 'Medium'))}", styles["SmallMeta"]), Paragraph(f"<b>Sample answer</b><br/>{html.escape(q.get('answer', '')).replace(chr(10), '<br/>')}", styles["BodyText"]), Spacer(1, 3)]
        if q.get("keywords"):
            group.append(Paragraph(f"<b>Keywords:</b> {html.escape(', '.join(q['keywords']))}", styles["BodyText"]))
        if q.get("tips"):
            group.append(Paragraph(f"<b>Tips:</b> {html.escape(' · '.join(q['tips']))}", styles["BodyText"]))
        story.append(KeepTogether(group))
    doc.build(story)
    return output.getvalue()


def inject_style() -> None:
    css_path = APP_DIR / "assets" / "style.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    dark = st.session_state.get("dark_mode", False)
    variables = """
    :root { --surface:#ffffff; --surface-2:#f7f8fc; --text:#20243a; --muted:#737b92; --border:rgba(105,113,145,.16); --shadow:0 16px 45px rgba(38,48,92,.08); --page:#f6f7fb; }
    """
    if dark:
        variables = """
        :root { --surface:#171a2c; --surface-2:#20243a; --text:#f0f2ff; --muted:#a5acc5; --border:rgba(180,187,230,.15); --shadow:0 16px 45px rgba(0,0,0,.22); --page:#101222; }
        """
    st.markdown(f"<style>{variables}\n{css}</style>", unsafe_allow_html=True)


def tag(label: str, color: str = "violet") -> str:
    return f'<span class="tag tag-{html.escape(color)}">{html.escape(label)}</span>'


def render_question_card(q: dict[str, Any], index: int, key_prefix: str = "q") -> None:
    color = {"Technical": "blue", "Coding": "cyan", "HR": "pink", "Scenario": "orange"}.get(q.get("category", ""), "violet")
    st.markdown(f"<div class='question-top'><div class='question-number'>{index:02d}</div><div class='question-tags'>{tag(q.get('category', 'General'), color)}{tag(q.get('difficulty', 'Medium'), 'neutral')}</div></div><div class='question-title'>{html.escape(q['question'])}</div>", unsafe_allow_html=True)
    with st.expander("Explore answer guide", expanded=False):
        st.markdown(f"<div class='answer-label'>SAMPLE ANSWER</div><div class='answer-copy'>{html.escape(q.get('answer', ''))}</div>", unsafe_allow_html=True)
        if q.get("keywords"):
            st.markdown("<div class='answer-label' style='margin-top:15px'>KEYWORDS TO INCLUDE</div>", unsafe_allow_html=True)
            st.markdown(" ".join(tag(k, "cyan") for k in q["keywords"]), unsafe_allow_html=True)
        if q.get("tips"):
            st.markdown("<div class='answer-label' style='margin-top:15px'>COACH'S TIPS</div>", unsafe_allow_html=True)
            for tip in q["tips"]:
                st.markdown(f"<div class='tip-line'><span>↗</span>{html.escape(tip)}</div>", unsafe_allow_html=True)
    st.code(q["question"], language=None, line_numbers=False, wrap_lines=True)


def header(title: str, subtitle: str, eyebrow: str = "PREPWISE AI") -> None:
    st.markdown(f"<div class='page-heading'><div class='eyebrow'>{html.escape(eyebrow)}</div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>", unsafe_allow_html=True)


if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "current_questions" not in st.session_state:
    st.session_state.current_questions = []
if "current_session" not in st.session_state:
    st.session_state.current_session = None
if "mock_index" not in st.session_state:
    st.session_state.mock_index = 0
if "mock_answers" not in st.session_state:
    st.session_state.mock_answers = {}
if "mock_revealed" not in st.session_state:
    st.session_state.mock_revealed = False
if "mock_active" not in st.session_state:
    st.session_state.mock_active = False
if "notice" not in st.session_state:
    st.session_state.notice = None
if st.session_state.get("nav_redirect"):
    st.session_state.navigation = st.session_state.pop("nav_redirect")

inject_style()
data = load_data()

with st.sidebar:
    st.markdown("<div class='brand-lockup'><div class='brand-mark'>✦</div><div><div class='brand-name'>prepwise<span>.ai</span></div><div class='brand-caption'>YOUR INTERVIEW EDGE</div></div></div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-label'>WORKSPACE</div>", unsafe_allow_html=True)
    page = st.radio("Navigate", ["Overview", "Question Studio", "Mock Interview", "Saved Library"], label_visibility="collapsed", key="navigation")
    st.markdown("<div class='sidebar-spacer'></div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-label'>PREFERENCES</div>", unsafe_allow_html=True)
    st.toggle("Dark appearance", key="dark_mode")
    st.caption("Your sessions stay in a local JSON file on this device.")
    st.markdown("<div class='sidebar-foot'><span class='status-dot'></span> Ready when you are</div>", unsafe_allow_html=True)

# Re-apply stylesheet on theme toggle during this run.
inject_style()
if st.session_state.notice:
    level, message = st.session_state.notice
    getattr(st, level)(message)
    st.session_state.notice = None

if page == "Overview":
    st.markdown("""
    <section class="hero-shell">
      <div class="hero-copy">
        <div class="hero-kicker"><span class="live-dot"></span> YOUR PERSONAL AI INTERVIEW COACH</div>
        <h1>Prepare smarter.<br/><span>Interview better.</span></h1>
        <p>Turn your skills and ambitions into a focused practice plan. Build confidence one thoughtful question at a time.</p>
        <div class="hero-actions"><span class="hero-note">Personalized practice. Real progress.</span></div>
      </div>
      <div class="hero-art" aria-hidden="true">
        <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div>
        <div class="hero-core"><div class="core-spark">✦</div><div class="core-label">AI<br/>COACH</div></div>
        <div class="float-card float-card-a"><span class="mini-icon">✧</span><span>Role-ready questions</span></div>
        <div class="float-card float-card-b"><span class="mini-icon cyan-icon">✓</span><span>Build your confidence</span></div>
        <div class="hero-particle p1"></div><div class="hero-particle p2"></div><div class="hero-particle p3"></div>
      </div>
      <div class="hero-glow"></div>
    </section>
    """, unsafe_allow_html=True)
    a, b = st.columns([1, 1])
    with a:
        if st.button("✦  Start preparing", type="primary", use_container_width=False, key="start_preparing"):
            st.session_state.nav_redirect = "Question Studio"
            st.rerun()
    with b:
        st.markdown("<div class='hero-social-proof'>✧ &nbsp; Make every practice session count</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-head'><div><div class='eyebrow'>YOUR PRACTICE SPACE</div><h2>Everything you need to feel ready</h2></div><span class='section-aside'>A little practice goes a long way</span></div>", unsafe_allow_html=True)
    feature_cols = st.columns(3)
    feature_cards = [
        ("◈", "Technical interviews", "Explore fundamentals, architecture, and practical scenarios tailored to your role.", "blue"),
        ("◎", "People & HR", "Practice thoughtful stories about teamwork, impact, and the way you work.", "violet"),
        ("⌘", "Coding practice", "Warm up with approachable problems and clear solution strategies.", "cyan"),
    ]
    for col, (icon, title, copy, color) in zip(feature_cols, feature_cards):
        with col:
            st.markdown(f"<div class='feature-card'><div class='feature-icon icon-{color}'>{icon}</div><h3>{title}</h3><p>{copy}</p><div class='feature-link'>Explore practice <span>↗</span></div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-head compact-head'><div><div class='eyebrow'>YOUR MOMENTUM</div><h2>Progress, at a glance</h2></div></div>", unsafe_allow_html=True)
    sessions = data.get("sessions", [])
    q_total = sum(len(item.get("questions", [])) for item in sessions)
    stats = [(str(q_total), "Questions generated", "↗"), (str(data.get("mock_interviews_completed", 0)), "Mock interviews", "◉"), (str(len(sessions)), "Practice sessions", "✦"), (str(len(data.get("saved_questions", []))), "Saved questions", "☆")]
    cols = st.columns(4)
    for col, (value, label, icon) in zip(cols, stats):
        with col:
            st.markdown(f"<div class='stat-card'><div class='stat-top'><span>{label}</span><span class='stat-icon'>{icon}</span></div><div class='stat-value'>{value}</div><div class='stat-foot'>Your preparation, your pace</div></div>", unsafe_allow_html=True)
    recent_skills = next((item.get("skills", []) for item in reversed(sessions) if item.get("skills")), [])
    recommended_skills = [skill for skill in ["Problem Solving", "Communication", "System Design", "SQL", "Git", "Cloud", "Machine Learning"] if skill not in recent_skills][:3]
    if not recommended_skills:
        recommended_skills = ["Communication", "System Design", "Problem Solving"]
    st.markdown("<div class='section-head compact-head'><div><div class='eyebrow'>A GOOD NEXT STEP</div><h2>Skills worth exploring</h2></div></div>", unsafe_allow_html=True)
    st.markdown("<div class='skill-recommendations'>" + "".join(f"<div class='skill-suggestion'><span>✧</span><strong>{html.escape(skill)}</strong><small>Build breadth alongside your role-specific practice</small></div>" for skill in recommended_skills) + "</div>", unsafe_allow_html=True)
    if sessions:
        st.markdown("<div class='section-head compact-head'><div><div class='eyebrow'>RECENT ACTIVITY</div><h2>Pick up where you left off</h2></div></div>", unsafe_allow_html=True)
        for item in reversed(sessions[-3:]):
            st.markdown(f"<div class='recent-row'><div class='recent-icon'>✦</div><div class='recent-main'><strong>{html.escape(item.get('role', 'Interview practice'))}</strong><span>{html.escape(item.get('experience', ''))} · {html.escape(item.get('interview_type', ''))}</span></div><div class='recent-count'>{len(item.get('questions', []))} questions</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='empty-inline'><div class='empty-icon'>✦</div><div><strong>Your first practice session is waiting.</strong><br/><span>Build a tailored set of questions in the Question Studio.</span></div></div>", unsafe_allow_html=True)

elif page == "Question Studio":
    header("Question Studio", "Tell us what you're preparing for. We'll build a practice set around you.")
    left, right = st.columns([0.94, 1.06], gap="large")
    with left:
        st.markdown("<div class='form-panel'><div class='panel-heading'><div class='panel-icon'>✦</div><div><h3>Set your interview context</h3><p>Adjust the details to make each question count.</p></div></div>", unsafe_allow_html=True)
        role = st.selectbox("Job role", ROLES, index=0, key="gen_role")
        if role == "Other":
            role = st.text_input("Enter your job role", placeholder="e.g. Platform Engineer", key="custom_role") or "Software Engineer"
        level = st.selectbox("Experience level", EXPERIENCE, index=0, key="gen_level")
        interview_type = st.selectbox("Interview format", INTERVIEW_TYPES, index=0, key="gen_type")
        skills = st.multiselect("Skills to focus on", SKILL_OPTIONS, default=["Python", "Problem Solving"], key="gen_skills", help="Choose the skills most relevant to the role.")
        c1, c2 = st.columns(2)
        with c1:
            count = st.selectbox("Question count", [5, 10, 15, 20], index=0, key="gen_count")
        with c2:
            difficulty = st.selectbox("Difficulty", DIFFICULTIES, index=1, key="gen_difficulty")
        generate_clicked = st.button("✦  Generate my questions", type="primary", use_container_width=True, key="generate_questions")
        st.markdown("<div class='privacy-note'>⌑ &nbsp; Your practice history is saved locally in this project.</div></div>", unsafe_allow_html=True)
        if generate_clicked:
            api_key = get_api_key()
            with st.spinner("Building a focused practice set…"):
                if api_key:
                    try:
                        generated = generate_with_ai(role, level, interview_type, skills, difficulty, count, api_key)
                        source_note = "AI-generated questions tailored to your choices."
                    except Exception as exc:
                        generated = _sample_question_bank(role, skills, level, interview_type, difficulty, count)
                        source_note = f"Using the built-in question bank because AI generation was unavailable ({str(exc)[:180]})."
                else:
                    generated = _sample_question_bank(role, skills, level, interview_type, difficulty, count)
                    source_note = "Sample mode is active. Add an OpenAI API key to enable personalized AI generation."
                session = {"id": f"s-{datetime.now().timestamp():.0f}", "created_at": datetime.now().isoformat(timespec="seconds"), "role": role, "experience": level, "interview_type": interview_type, "skills": skills, "difficulty": difficulty, "questions": generated, "source": "AI" if api_key and source_note.startswith("AI-generated") else "Sample"}
                st.session_state.current_questions = generated
                st.session_state.current_session = session
                data["sessions"].append(session)
                save_data(data)
                st.session_state.notice = ("success" if session["source"] == "AI" else "info", f"{len(generated)} questions are ready. {source_note}")
                st.rerun()
    with right:
        questions = st.session_state.current_questions
        if questions:
            session = st.session_state.current_session or {}
            st.markdown(f"<div class='results-header'><div><div class='eyebrow'>YOUR PRACTICE SET</div><h2>{html.escape(session.get('role', 'Interview'))}</h2><p>{html.escape(session.get('experience', ''))} · {html.escape(session.get('interview_type', ''))} · {len(questions)} questions</p></div><div class='result-spark'>✦</div></div>", unsafe_allow_html=True)
            search = st.text_input("Search questions", placeholder="Try ‘debugging’ or ‘teamwork’", key="studio_search")
            filtered = [q for q in questions if search.casefold() in (q["question"] + " " + q.get("category", "")).casefold()]
            if filtered:
                for i, q in enumerate(filtered, 1):
                    with st.container(border=True):
                        render_question_card(q, i, "studio")
            else:
                st.info("No questions match that search. Try a different keyword.")
            action_cols = st.columns(2)
            with action_cols[0]:
                if st.button("↻  Regenerate set", use_container_width=True, key="regenerate"):
                    previous = st.session_state.current_session or {}
                    api_key = get_api_key()
                    with st.spinner("Refreshing your practice set…"):
                        if api_key:
                            try:
                                generated = generate_with_ai(previous.get("role", "Software Engineer"), previous.get("experience", "Beginner"), previous.get("interview_type", "Mixed"), previous.get("skills", []), previous.get("difficulty", "Medium"), len(questions), api_key)
                                source = "AI"
                                message = "A fresh AI-generated practice set is ready."
                            except Exception:
                                generated = _sample_question_bank(previous.get("role", "Software Engineer"), previous.get("skills", []), previous.get("experience", "Beginner"), previous.get("interview_type", "Mixed"), previous.get("difficulty", "Medium"), len(questions))
                                source = "Sample"
                                message = "AI generation was unavailable, so a fresh sample set is ready."
                        else:
                            generated = _sample_question_bank(previous.get("role", "Software Engineer"), previous.get("skills", []), previous.get("experience", "Beginner"), previous.get("interview_type", "Mixed"), previous.get("difficulty", "Medium"), len(questions))
                            source = "Sample"
                            message = "A fresh sample question set is ready. Add an API key to generate with AI."
                        refreshed = {**previous, "id": f"s-{datetime.now().timestamp():.0f}", "created_at": datetime.now().isoformat(timespec="seconds"), "questions": generated, "source": source}
                        st.session_state.current_questions = generated
                        st.session_state.current_session = refreshed
                        data["sessions"].append(refreshed)
                        save_data(data)
                        st.session_state.notice = ("success" if source == "AI" else "info", message)
                    st.rerun()
            with action_cols[1]:
                try:
                    pdf_bytes = make_pdf(session)
                    st.download_button("↓  Download PDF", data=pdf_bytes, file_name=f"prepwise-{re.sub(r'[^a-z0-9]+', '-', session.get('role', 'practice').lower()).strip('-')}.pdf", mime="application/pdf", use_container_width=True, key="download_pdf")
                except ImportError:
                    st.warning("Install reportlab to enable PDF downloads.")
        else:
            st.markdown("""
            <div class="preview-panel">
              <div class="preview-orbit orbit-a"></div><div class="preview-orbit orbit-b"></div>
              <div class="preview-center"><span>✦</span></div>
              <div class="preview-copy"><div class="eyebrow">A BETTER WAY TO PREPARE</div><h2>Your next great answer<br/>starts with a question.</h2><p>Fill in your interview context and your personalized practice set will appear here.</p></div>
              <div class="preview-mini"><span>✧</span> Built around your goals</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div class='mini-benefits'><div><span>01</span> Role-aware prompts</div><div><span>02</span> Clear answer guidance</div><div><span>03</span> Practice at your pace</div></div>", unsafe_allow_html=True)

elif page == "Mock Interview":
    header("Mock Interview", "Practice out loud—or in writing—and turn answer ideas into interview confidence.")
    questions = st.session_state.current_questions
    if not questions:
        st.markdown("<div class='empty-state'><div class='empty-state-icon'>◉</div><h2>Start with a practice set</h2><p>Generate questions in the Question Studio first. Then bring them here for a guided one-question-at-a-time mock interview.</p></div>", unsafe_allow_html=True)
        if st.button("Open Question Studio", type="primary"):
            st.session_state.nav_redirect = "Question Studio"
            st.rerun()
    elif not st.session_state.mock_active:
        session = st.session_state.current_session or {}
        st.markdown(f"<div class='mock-intro'><div class='mock-orb'>◉</div><div><div class='eyebrow'>READY WHEN YOU ARE</div><h2>{html.escape(session.get('role', 'Your interview'))} practice</h2><p>{len(questions)} questions · {html.escape(session.get('interview_type', 'Mixed'))} format · Take your time, then compare your answer with the guide.</p></div></div>", unsafe_allow_html=True)
        if st.button("▶  Begin mock interview", type="primary", key="begin_mock"):
            st.session_state.mock_active = True
            st.session_state.mock_index = 0
            st.session_state.mock_answers = {}
            st.session_state.mock_revealed = False
            st.rerun()
    else:
        idx = st.session_state.mock_index
        if idx >= len(questions):
            answers = st.session_state.mock_answers
            answered = sum(1 for value in answers.values() if str(value).strip())
            st.balloons()
            st.markdown(f"<div class='completion-card'><div class='completion-icon'>✦</div><div class='eyebrow'>PRACTICE COMPLETE</div><h2>That’s another step forward.</h2><p>You worked through {len(questions)} questions and drafted {answered} answers. Review your answer guides and keep practicing the stories you want to tell.</p><div class='completion-stat'><strong>{answered}/{len(questions)}</strong><span>answers drafted</span></div></div>", unsafe_allow_html=True)
            if st.button("Finish and save progress", type="primary", key="finish_mock"):
                data["mock_interviews_completed"] = int(data.get("mock_interviews_completed", 0)) + 1
                data["sessions"].append({"id": f"mock-{datetime.now().timestamp():.0f}", "created_at": datetime.now().isoformat(timespec="seconds"), "role": (st.session_state.current_session or {}).get("role", "Interview practice"), "experience": "Mock interview", "interview_type": "Completed", "questions": [], "mock_answer_count": answered})
                save_data(data)
                st.session_state.mock_active = False
                st.session_state.mock_index = 0
                st.session_state.notice = ("success", "Mock interview progress saved to your dashboard.")
                st.rerun()
        else:
            q = questions[idx]
            progress = idx / len(questions)
            st.markdown(f"<div class='mock-progress-row'><span>QUESTION {idx + 1:02d} <span class='muted'>/ {len(questions):02d}</span></span><span>{round(progress * 100)}% COMPLETE</span></div>", unsafe_allow_html=True)
            st.progress(progress)
            st.markdown(f"<div class='mock-question-card'><div class='question-tags'>{tag(q.get('category', 'General'), 'violet')}{tag(q.get('difficulty', 'Medium'), 'neutral')}</div><h2>{html.escape(q['question'])}</h2><p>Take a moment to structure your thoughts. A clear example is often more powerful than a perfect answer.</p></div>", unsafe_allow_html=True)
            answer_key = f"mock_answer_{idx}"
            current_answer = st.text_area("Your answer", key=answer_key, height=160, placeholder="Type your answer here… You can use a simple structure: context, action, result, reflection.")
            st.session_state.mock_answers[str(idx)] = current_answer
            if not st.session_state.mock_revealed:
                if st.button("Submit answer & see guide", type="primary", key=f"submit_{idx}"):
                    st.session_state.mock_revealed = True
                    st.rerun()
            else:
                st.markdown(f"<div class='guide-reveal'><div class='answer-label'>A WAY TO APPROACH IT</div><p>{html.escape(q.get('answer', ''))}</p></div>", unsafe_allow_html=True)
                if q.get("keywords"):
                    st.markdown(" ".join(tag(k, "cyan") for k in q["keywords"]), unsafe_allow_html=True)
                if q.get("tips"):
                    for tip in q["tips"]:
                        st.markdown(f"<div class='tip-line'><span>↗</span>{html.escape(tip)}</div>", unsafe_allow_html=True)
                if st.button("Next question  →", type="primary", key=f"next_{idx}"):
                    st.session_state.mock_index += 1
                    st.session_state.mock_revealed = False
                    st.rerun()
            if st.button("End mock interview", key=f"end_mock_{idx}"):
                st.session_state.mock_index = len(questions)
                st.rerun()

elif page == "Saved Library":
    header("Saved Library", "Keep your favorite prompts close and revisit them whenever you're ready.")
    saved = data.get("saved_questions", [])
    if st.session_state.current_questions:
        with st.expander("Save from your current practice set", expanded=not saved):
            chosen = st.multiselect("Choose questions to save", options=list(range(len(st.session_state.current_questions))), format_func=lambda i: f"{i+1}. {st.session_state.current_questions[i]['question']}", key="save_picker")
            if st.button("☆  Save selected questions", type="primary", key="save_selected"):
                known = {item.get("id") for item in saved}
                for i in chosen:
                    q = st.session_state.current_questions[i].copy()
                    q["role"] = (st.session_state.current_session or {}).get("role", "Interview")
                    if q.get("id") not in known:
                        saved.append(q)
                data["saved_questions"] = saved
                save_data(data)
                st.session_state.notice = ("success", f"Saved {len(chosen)} question(s) to your library.")
                st.rerun()
    filter_text = st.text_input("Search your library", placeholder="Filter by question, role, or category", key="saved_search")
    matching = [q for q in saved if filter_text.casefold() in (q.get("question", "") + " " + q.get("role", "") + " " + q.get("category", "")).casefold()]
    if not matching:
        st.markdown("<div class='empty-state'><div class='empty-state-icon'>☆</div><h2>Your saved library is ready</h2><p>Save questions from a practice set to build your own collection of prompts and answer guides.</p></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='library-count'>{len(matching)} saved question{'s' if len(matching) != 1 else ''}</div>", unsafe_allow_html=True)
        for idx, q in enumerate(matching, 1):
            with st.container(border=True):
                st.markdown(f"<div class='saved-origin'>SAVED FROM · {html.escape(q.get('role', 'INTERVIEW').upper())}</div>", unsafe_allow_html=True)
                render_question_card(q, idx, "saved")
                if st.button("Remove from saved", key=f"remove_{q.get('id', idx)}"):
                    data["saved_questions"] = [item for item in saved if item.get("id") != q.get("id")]
                    save_data(data)
                    st.rerun()
