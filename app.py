"""Autonomous Job Research Agent.

An AI agent that autonomously searches job vacancies on the web and matches
them against Avatar Putra Sigit's skill profile.

Author : Avatar Putra Sigit
GitHub : qurrrrsebastian-prog
LinkedIn: avatarputrasigit
"""

# ---------------------------------------------------------------------------
# SECTION A — Imports & Config
# ---------------------------------------------------------------------------
import os
import sys
import json
import re
import time
import urllib.parse
from datetime import datetime

import streamlit as st
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup
from groq import Groq

st.set_page_config(
    page_title="Autonomous Job Research Agent",
    layout="wide",
    page_icon="🔍",
)


# ---------------------------------------------------------------------------
# SECTION B — Groq Client Setup
# ---------------------------------------------------------------------------
def get_groq_client(api_key: str) -> Groq:
    """Create and return a Groq client.

    Args:
        api_key: The Groq API key used to authenticate requests.

    Returns:
        A configured :class:`groq.Groq` client instance.

    Raises:
        ValueError: If the API key is empty or the client cannot be created.
    """
    try:
        if not api_key:
            raise ValueError("Groq API key is empty.")
        return Groq(api_key=api_key)
    except Exception as exc:  # noqa: BLE001 - surface a clear message to caller
        raise ValueError(f"Failed to create Groq client: {exc}") from exc


def groq_chat(
    client: Groq,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
) -> str:
    """Send a chat completion request to Groq and return the text response.

    Args:
        client: An authenticated Groq client.
        system_prompt: The system-role instruction guiding the model.
        user_prompt: The user-role message / payload.
        temperature: Sampling temperature for the completion.

    Returns:
        The assistant message content as a string. Returns an empty string on
        failure.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 - keep the UI alive on API errors
        st.error(f"Groq request failed: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Helper — robust JSON extraction from an LLM response
# ---------------------------------------------------------------------------
def _extract_json(text: str) -> object:
    """Extract the first JSON array or object found in a text blob.

    LLMs sometimes wrap JSON in markdown fences or prose. This helper tries a
    direct parse first, then falls back to a regex that grabs the outermost
    array/object.

    Args:
        text: Raw text that should contain JSON.

    Returns:
        The parsed JSON value (list or dict), or ``None`` if parsing fails.
    """
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001 - fall through to regex extraction
        pass

    try:
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception:  # noqa: BLE001 - give up gracefully
        return None
    return None


# ---------------------------------------------------------------------------
# SECTION C — Search & Scrape
# ---------------------------------------------------------------------------
def generate_queries(client: Groq, role: str, location: str, level: str) -> list[str]:
    """Generate 3 optimized job-search queries using Groq.

    Args:
        client: An authenticated Groq client.
        role: Target job role (e.g. "Data Analyst").
        location: Target location (e.g. "Jakarta").
        level: Experience level (e.g. "Entry Level").

    Returns:
        A list of exactly 3 search-query strings. Falls back to sensible
        defaults if the model output cannot be parsed.
    """
    fallback = [
        f"lowongan {role} {location} {level}",
        f"{role} job {location} LinkedIn JobStreet",
        f"karir {role} {location} Glints Kalibrr",
    ]
    try:
        system_prompt = (
            "You are a job search expert. Generate 3 specific DuckDuckGo "
            "search queries in Indonesian/English to find job vacancies. "
            "Target job portals like LinkedIn, JobStreet, Kalibrr, Glints. "
            "Return ONLY a JSON array of strings."
        )
        user_prompt = f"Role: {role}, Location: {location}, Level: {level}"
        raw = groq_chat(client, system_prompt, user_prompt, temperature=0.5)
        parsed = _extract_json(raw)
        if isinstance(parsed, list) and parsed:
            queries = [str(q) for q in parsed if str(q).strip()]
            return queries[:3] if queries else fallback
        return fallback
    except Exception as exc:  # noqa: BLE001 - never break the pipeline
        st.warning(f"Query generation fell back to defaults: {exc}")
        return fallback


def search_duckduckgo(queries: list[str], max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo for each query and collect text results.

    Args:
        queries: A list of search-query strings.
        max_results: Maximum results to fetch per query.

    Returns:
        A combined list of result dicts with keys ``title``, ``href`` and
        ``body``. Returns an empty list if all searches fail.
    """
    results: list[dict] = []
    try:
        for index, query in enumerate(queries):
            try:
                # region="id-id" biases toward Indonesian job results;
                # timeout=15 gives slow DDG responses room to complete.
                with DDGS(timeout=15) as ddgs:
                    hits = ddgs.text(
                        query, region="id-id", max_results=max_results
                    )
                for hit in hits or []:
                    results.append(
                        {
                            "title": hit.get("title", ""),
                            "href": hit.get("href", ""),
                            "body": hit.get("body", ""),
                        }
                    )
            except Exception as inner_exc:  # noqa: BLE001 - skip a bad query
                st.warning(f"Search failed for '{query}': {inner_exc}")
                continue
            # Pause between queries to avoid DDG rate limiting.
            if index < len(queries) - 1:
                time.sleep(1)
        return results
    except Exception as exc:  # noqa: BLE001 - return whatever we have
        # A total failure returns an empty list, which the UI treats as a
        # trigger to fall back to curated demo data immediately.
        st.warning(f"DuckDuckGo search unavailable: {exc}")
        return results


def scrape_snippets(results: list[dict]) -> list[dict]:
    """Extract a lightweight title + snippet for each search result.

    Uses the search ``body`` when available; otherwise fetches the URL and
    pulls a short text snippet via BeautifulSoup. Failed URLs are skipped.

    Args:
        results: Search-result dicts from :func:`search_duckduckgo`.

    Returns:
        A list of dicts with keys ``title``, ``url`` and ``snippet``.
    """
    snippets: list[dict] = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobResearchAgent/1.0)"}
    for result in results:
        try:
            title = result.get("title", "")
            url = result.get("href", "")
            snippet = (result.get("body") or "").strip()

            if not snippet and url:
                try:
                    resp = requests.get(url, headers=headers, timeout=8)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")
                    text = soup.get_text(separator=" ", strip=True)
                    snippet = text[:500]
                except Exception:  # noqa: BLE001 - skip unreachable pages
                    continue

            if title or snippet:
                snippets.append(
                    {"title": title, "url": url, "snippet": snippet}
                )
        except Exception:  # noqa: BLE001 - never let one item break the loop
            continue
    return snippets


# ---------------------------------------------------------------------------
# SECTION D — AI Analysis
# ---------------------------------------------------------------------------
def analyze_jobs(client: Groq, snippets: list[dict], role: str) -> list[dict]:
    """Analyze job snippets and return structured, skill-matched job data.

    Args:
        client: An authenticated Groq client.
        snippets: Lightweight job snippets from :func:`scrape_snippets`.
        role: The target job role used to anchor the analysis.

    Returns:
        A list of structured job dicts. Returns an empty list on failure.
    """
    if not snippets:
        st.warning("No snippets to analyze.")
        return []

    try:
        system_prompt = (
            "You are a career advisor. Analyze job snippets and return "
            "structured data. Avatar's skills: Python, Pandas, Streamlit, "
            "LangChain, RAG, ChromaDB, FastEmbed, Flask, SQLite, Google Ads, "
            "SEO, Web Scraping, Multi-Agent AI, Data Visualization, NLP, "
            "Prophet. For each job, calculate match score 1-100 based on "
            "skill overlap. Return ONLY valid JSON array."
        )
        user_prompt = (
            f"Job role target: {role}\n\n"
            f"Snippets:\n{json.dumps(snippets, indent=2)}\n\n"
            "Return JSON array with fields: company_name, job_title, "
            "location, requirements_summary, salary_hint, apply_url, "
            "skill_match_score, matching_skills, missing_skills, "
            "recommendation"
        )
        raw = groq_chat(client, system_prompt, user_prompt, temperature=0.2)
        parsed = _extract_json(raw)
        if isinstance(parsed, list):
            return parsed
        st.error("AI analysis did not return a valid JSON array.")
        return []
    except Exception as exc:  # noqa: BLE001 - keep the app responsive
        st.error(f"Job analysis failed: {exc}")
        return []


# ---------------------------------------------------------------------------
# SECTION C2 — Multi-portal direct search URL generators
# ---------------------------------------------------------------------------
def _linkedin_experience_params(level: str) -> str:
    """Map an experience level to LinkedIn's f_E / f_WT filter params.

    Args:
        level: Free-text experience level (e.g. "Internship", "Remote").

    Returns:
        A query-param fragment such as ``&f_E=2`` or ``&f_E=2&f_WT=2``.
        Returns an empty string when no mapping applies.
    """
    try:
        text = (level or "").lower()
        if "intern" in text or "magang" in text:
            return "&f_E=1"
        if "remote" in text:
            return "&f_E=2&f_WT=2"
        # Fresh Graduate / 1-3 Tahun / default entry-level.
        return "&f_E=2"
    except Exception:  # noqa: BLE001 - never break URL building
        return ""


def generate_linkedin_url(
    title: str, company: str, location: str, level: str
) -> str:
    """Build a direct LinkedIn Jobs search URL for a specific job.

    Args:
        title: The job title.
        company: The hiring company name.
        location: The job location.
        level: Experience level used to derive LinkedIn filters.

    Returns:
        A fully encoded LinkedIn Jobs search URL, or ``"#"`` if both title
        and company are missing.
    """
    try:
        if not (title or company):
            return "#"
        keywords = urllib.parse.quote(f"{title} {company}".strip())
        loc = urllib.parse.quote(location or "")
        exp = _linkedin_experience_params(level)
        return (
            "https://www.linkedin.com/jobs/search/"
            f"?keywords={keywords}&location={loc}{exp}"
        )
    except Exception:  # noqa: BLE001 - graceful fallback
        return "#"


def generate_jobstreet_url(title: str, location: str) -> str:
    """Build a direct JobStreet Indonesia search URL.

    Args:
        title: The job title.
        location: The job location (city is extracted before the comma).

    Returns:
        An encoded JobStreet search URL, or ``"#"`` if the title is missing.
    """
    try:
        if not title:
            return "#"
        keyword = urllib.parse.quote(title)
        city = urllib.parse.quote((location or "").split(",")[0].strip())
        return (
            "https://www.jobstreet.co.id/id/job-search/"
            f"?keyword={keyword}&location={city}"
        )
    except Exception:  # noqa: BLE001 - graceful fallback
        return "#"


def generate_kalibrr_url(title: str) -> str:
    """Build a direct Kalibrr job-board search URL.

    Args:
        title: The job title.

    Returns:
        An encoded Kalibrr search URL, or ``"#"`` if the title is missing.
    """
    try:
        if not title:
            return "#"
        search = urllib.parse.quote(title)
        return f"https://www.kalibrr.com/id-ID/job-board/?search={search}"
    except Exception:  # noqa: BLE001 - graceful fallback
        return "#"


def generate_glints_url(title: str) -> str:
    """Build a direct Glints Indonesia job search URL.

    Args:
        title: The job title.

    Returns:
        An encoded Glints search URL, or ``"#"`` if the title is missing.
    """
    try:
        if not title:
            return "#"
        keyword = urllib.parse.quote(title)
        return (
            "https://glints.com/id/opportunities/jobs/explore"
            f"?keyword={keyword}"
        )
    except Exception:  # noqa: BLE001 - graceful fallback
        return "#"


# ---------------------------------------------------------------------------
# Helper — curated demo data (auto-fallback when live search is limited)
# ---------------------------------------------------------------------------
def get_demo_jobs() -> list[dict]:
    """Return curated demo job data for 5 Indonesian tech companies.

    Used automatically when DuckDuckGo returns too few results or the AI
    analysis comes back empty, so the UI always has realistic content to
    display. Scores reflect Avatar's skill profile.

    Returns:
        A list of structured job dicts matching the live-data schema.
    """
    return [
        {
            "company_name": "Tokopedia",
            "job_title": "Data Analyst Intern",
            "location": "Jakarta, Indonesia",
            "requirements_summary": (
                "Analyze user behavior data, build dashboards with "
                "Python/SQL, A/B testing, data storytelling. Familiar with "
                "Pandas and visualization tools."
            ),
            "salary_hint": "Rp 3.500.000 - 5.000.000/bulan",
            "apply_url": (
                "https://www.linkedin.com/jobs/search/?keywords=Data%20Analyst"
                "%20Intern%20Tokopedia&location=Jakarta%2C%20Indonesia&f_E=1"
            ),
            "skill_match_score": 88,
            "matching_skills": [
                "Python", "Pandas", "Data Visualization", "SQL", "Streamlit"
            ],
            "missing_skills": ["Tableau", "Advanced SQL", "A/B Testing"],
            "recommendation": "Strong match",
        },
        {
            "company_name": "Gojek",
            "job_title": "Machine Learning Engineer",
            "location": "Jakarta, Indonesia",
            "requirements_summary": (
                "Build ML models for recommendation systems, NLP for customer "
                "support, deploy models to production. Python, "
                "TensorFlow/PyTorch experience."
            ),
            "salary_hint": "Rp 8.000.000 - 12.000.000/bulan",
            "apply_url": (
                "https://www.linkedin.com/jobs/search/?keywords=Machine%20"
                "Learning%20Engineer%20Gojek&location=Jakarta%2C%20Indonesia"
                "&f_E=2"
            ),
            "skill_match_score": 72,
            "matching_skills": ["Python", "NLP", "Data Visualization", "Pandas"],
            "missing_skills": [
                "PyTorch", "TensorFlow", "Docker", "AWS", "MLOps"
            ],
            "recommendation": "Learn missing skills first",
        },
        {
            "company_name": "Shopee",
            "job_title": "Business Intelligence Analyst",
            "location": "Jakarta, Indonesia",
            "requirements_summary": (
                "Analyze campaign performance, SEO optimization, competitor "
                "analysis, ROI tracking. Google Ads and Python scripting "
                "required."
            ),
            "salary_hint": "Rp 6.000.000 - 9.000.000/bulan",
            "apply_url": (
                "https://www.linkedin.com/jobs/search/?keywords=Business%20"
                "Intelligence%20Analyst%20Shopee&location=Jakarta%2C%20"
                "Indonesia&f_E=2"
            ),
            "skill_match_score": 85,
            "matching_skills": [
                "Python", "Google Ads", "SEO", "Pandas",
                "Data Visualization", "Web Scraping",
            ],
            "missing_skills": ["Facebook Ads Manager", "Power BI"],
            "recommendation": "Strong match",
        },
        {
            "company_name": "Traveloka",
            "job_title": "Data Science Intern",
            "location": "Jakarta, Indonesia",
            "requirements_summary": (
                "Support data science team with EDA, forecasting models, and "
                "automated reports. Prophet or time-series experience is a "
                "plus."
            ),
            "salary_hint": "Rp 4.000.000 - 6.000.000/bulan",
            "apply_url": (
                "https://www.linkedin.com/jobs/search/?keywords=Data%20Science"
                "%20Intern%20Traveloka&location=Jakarta%2C%20Indonesia&f_E=1"
            ),
            "skill_match_score": 91,
            "matching_skills": [
                "Python", "Pandas", "Prophet", "Data Visualization",
                "Streamlit", "EDA",
            ],
            "missing_skills": ["Spark", "Hadoop"],
            "recommendation": "Strong match",
        },
        {
            "company_name": "Blibli",
            "job_title": "Backend Developer (Python)",
            "location": "Jakarta, Indonesia",
            "requirements_summary": (
                "Develop REST APIs, database design, microservices. Python "
                "(Flask/FastAPI), PostgreSQL, Redis. Understanding of AI/ML "
                "integration is a plus."
            ),
            "salary_hint": "Rp 7.000.000 - 10.000.000/bulan",
            "apply_url": (
                "https://www.linkedin.com/jobs/search/?keywords=Backend%20"
                "Developer%20Python%20Blibli&location=Jakarta%2C%20Indonesia"
                "&f_E=2"
            ),
            "skill_match_score": 68,
            "matching_skills": ["Python", "Flask", "SQLite"],
            "missing_skills": [
                "FastAPI", "PostgreSQL", "Redis", "Docker",
                "Kubernetes", "Microservices",
            ],
            "recommendation": "Learn missing skills first",
        },
    ]


# ---------------------------------------------------------------------------
# Helper — color-coded score badge
# ---------------------------------------------------------------------------
def score_badge(score: int) -> str:
    """Return a colored emoji badge for a skill-match score.

    Args:
        score: The skill-match score (1-100).

    Returns:
        A short markdown string: green (>80), yellow (60-80), red (<60).
    """
    try:
        value = int(score)
    except (TypeError, ValueError):
        value = 0

    if value > 80:
        return f"🟢 {value}"
    if value >= 60:
        return f"🟡 {value}"
    return f"🔴 {value}"


# ---------------------------------------------------------------------------
# Helper — CSV serialization
# ---------------------------------------------------------------------------
def jobs_to_csv(jobs: list[dict]) -> str:
    """Convert a list of job dicts into a CSV string.

    Args:
        jobs: The structured job data to serialize.

    Returns:
        A CSV-formatted string (empty string if there are no jobs).
    """
    import csv
    import io

    if not jobs:
        return ""

    try:
        fieldnames = [
            "company_name",
            "job_title",
            "location",
            "requirements_summary",
            "salary_hint",
            "apply_url",
            "skill_match_score",
            "matching_skills",
            "missing_skills",
            "recommendation",
        ]
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for job in jobs:
            row = dict(job)
            for key in ("matching_skills", "missing_skills"):
                value = row.get(key)
                if isinstance(value, list):
                    row[key] = ", ".join(str(v) for v in value)
            writer.writerow(row)
        return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001 - return empty CSV on failure
        st.error(f"CSV export failed: {exc}")
        return ""


# ---------------------------------------------------------------------------
# SECTION E — UI
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the Streamlit UI and orchestrate the agent workflow.

    Returns:
        None.
    """
    # ----- Sidebar -----
    with st.sidebar:
        st.header("🔐 API Key")
        groq_key = st.text_input(
            "Groq API Key",
            type="password",
            value=os.environ.get("GROQ_API_KEY", ""),
        )
        st.header("👤 Skill Profile")
        st.markdown(
            "**Avatar Putra Sigit**\n"
            "- 18 y/o | Sistem Informasi Budi Luhur\n"
            "- 15 Production Projects\n"
            "- Python, Pandas, Streamlit, LangChain, Groq, RAG, ChromaDB, "
            "Flask, SQLite, Google Ads, SEO, NLP, Data Viz"
        )

        st.divider()
        st.header("🚀 Cari di Portal")
        st.link_button("🔍 LinkedIn Jobs", "https://www.linkedin.com/jobs/")
        st.link_button("📋 JobStreet", "https://www.jobstreet.co.id/")
        st.link_button("💼 Kalibrr", "https://www.kalibrr.com/")
        st.link_button("🌟 Glints", "https://glints.com/id/")

        st.divider()
        st.caption(
            "💡 Tip: Hasil di atas sudah include link langsung ke tiap "
            "portal per lowongan."
        )

    # ----- Main -----
    st.title("🔍 Autonomous Job Research Agent")
    st.caption("AI cari lowongan & cocokkan sama skill kamu")

    col1, col2 = st.columns([1, 2])

    with col1:
        role = st.text_input("Job Role", value="Data Analyst")
        location = st.text_input("Location", value="Jakarta")
        level = st.selectbox(
            "Experience Level",
            ["Internship", "Entry Level", "Junior", "Mid Level", "Senior"],
        )

        search_clicked = st.button(
            "🔍 Cari Lowongan", type="primary", use_container_width=True
        )
        clear_clicked = st.button("🧹 Clear Results", use_container_width=True)

        if clear_clicked:
            for key in ("jobs", "searched", "queries", "demo_mode", "debug"):
                st.session_state.pop(key, None)
            st.rerun()

        if search_clicked:
            if not groq_key:
                st.error("Please enter your Groq API key in the sidebar.")
            else:
                progress = st.progress(0, text="Generating queries...")
                debug: dict = {"api_status": "unknown"}
                try:
                    client = get_groq_client(groq_key)

                    progress.progress(25, text="Generating queries...")
                    queries = generate_queries(client, role, location, level)

                    progress.progress(50, text="Searching web...")
                    results = search_duckduckgo(queries)

                    progress.progress(75, text="Analyzing jobs...")
                    snippets = scrape_snippets(results)
                    jobs = analyze_jobs(client, snippets, role)

                    # Auto-fallback: too few live results or empty analysis
                    # means we serve curated demo data instead of a blank UI.
                    demo_mode = False
                    if len(results) < 3 or not jobs:
                        jobs = get_demo_jobs()
                        demo_mode = True

                    progress.progress(100, text="Finalizing...")
                    st.session_state.jobs = jobs
                    st.session_state.searched = True
                    st.session_state.queries = queries
                    st.session_state.demo_mode = demo_mode
                    debug.update(
                        {
                            "api_status": "ok",
                            "generated_queries": queries,
                            "raw_result_count": len(results),
                            "snippet_count": len(snippets),
                            "demo_mode": demo_mode,
                        }
                    )
                    st.session_state.debug = debug
                except Exception as exc:  # noqa: BLE001 - report and continue
                    st.error(f"Search workflow failed: {exc}")
                    debug["api_status"] = f"error: {exc}"
                    st.session_state.debug = debug
                finally:
                    progress.empty()

    with col2:
        if st.session_state.get("searched"):
            jobs = st.session_state.get("jobs", [])

            if st.session_state.get("demo_mode"):
                st.info(
                    "📡 Web search limited — showing curated demo data with "
                    "real apply links. Click 'Cari di LinkedIn' to apply."
                )
            elif jobs:
                st.success(f"✅ Found {len(jobs)} jobs from live web search!")

            if not jobs:
                st.info("No jobs found. Try a broader role or location.")
            else:
                strong = sum(
                    1 for j in jobs if j.get("skill_match_score", 0) > 80
                )
                avg = (
                    sum(j.get("skill_match_score", 0) for j in jobs) / len(jobs)
                    if jobs
                    else 0
                )

                cols = st.columns(3)
                cols[0].metric("Total Jobs", len(jobs))
                cols[1].metric("Strong Matches (>80)", strong)
                cols[2].metric("Avg Match Score", f"{avg:.0f}")

                st.divider()

                st.dataframe(
                    [
                        {
                            "Score": score_badge(j.get("skill_match_score", 0)),
                            **{
                                k: v
                                for k, v in j.items()
                                if k
                                not in ("requirements_summary", "skill_match_score")
                            },
                        }
                        for j in jobs
                    ],
                    use_container_width=True,
                )

                for job in jobs:
                    badge = score_badge(job.get("skill_match_score", 0))
                    title = job.get("job_title", "Unknown")
                    company = job.get("company_name", "Unknown")
                    location_str = job.get("location", "N/A")
                    header = f"{badge}  —  **{company}** · {title}"
                    with st.expander(header):
                        st.markdown(f"📍 **{location_str}**")
                        st.markdown(
                            f"💰 {job.get('salary_hint', 'N/A')}"
                        )
                        st.markdown(
                            f"📝 **Requirements:** "
                            f"{job.get('requirements_summary', 'N/A')}"
                        )
                        st.markdown(
                            f"✅ **Matching:** "
                            f"{', '.join(job.get('matching_skills', []))}"
                        )
                        st.markdown(
                            f"⚠️ **Missing:** "
                            f"{', '.join(job.get('missing_skills', []))}"
                        )
                        st.markdown(
                            f"🎯 **Recommendation:** "
                            f"{job.get('recommendation', 'N/A')}"
                        )

                        st.markdown("🔗 **APPLY ON:**")
                        # Build per-portal direct search URLs. The stored
                        # apply_url (often a LinkedIn search) is preferred for
                        # the LinkedIn button when present.
                        linkedin_url = job.get("apply_url") or generate_linkedin_url(
                            title, company, location_str, level
                        )
                        portal_links = [
                            ("LinkedIn 🔗", linkedin_url),
                            (
                                "JobStreet 🔗",
                                generate_jobstreet_url(title, location_str),
                            ),
                            ("Kalibrr 🔗", generate_kalibrr_url(title)),
                            ("Glints 🔗", generate_glints_url(title)),
                        ]
                        btn_cols = st.columns(4)
                        for col, (label, url) in zip(btn_cols, portal_links):
                            with col:
                                if url and url != "#":
                                    st.link_button(
                                        label, url, use_container_width=True
                                    )
                                else:
                                    st.button(
                                        label,
                                        disabled=True,
                                        use_container_width=True,
                                        key=f"{company}_{title}_{label}",
                                    )

                    st.divider()

                csv = jobs_to_csv(jobs)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    "⬇️ Download CSV",
                    csv,
                    f"job_research_{timestamp}.csv",
                    "text/csv",
                    disabled=not jobs,
                )

            # ----- Debug Info (collapsible, for troubleshooting) -----
            with st.expander("🛠️ Debug Info"):
                debug = st.session_state.get("debug", {})
                st.markdown(f"**API Status:** {debug.get('api_status', 'N/A')}")
                st.markdown(
                    f"**Raw Result Count:** {debug.get('raw_result_count', 'N/A')}"
                )
                st.markdown(
                    f"**Snippet Count:** {debug.get('snippet_count', 'N/A')}"
                )
                st.markdown(
                    f"**Demo Mode:** {debug.get('demo_mode', 'N/A')}"
                )
                st.markdown("**Generated Queries:**")
                st.json(debug.get("generated_queries", []))


if __name__ == "__main__":
    main()
