"""ui_components.py — Reusable UI components.
Author: Avatar Putra Sigit | GitHub: qurrrrsebastian-prog
"""
import streamlit as st

PRIMARY = "#7C3AED"
SECONDARY = "#A78BFA"


def render_header(title: str, subtitle: str, color: str = PRIMARY) -> None:
    """Render a gradient page header."""
    st.markdown(
        f"""
    <div style="background: linear-gradient(135deg, {color}22, {color}08);
        border-left: 4px solid {color}; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px;">
        <h1 style="color: {color}; margin: 0; font-size: 28px;">{title}</h1>
        <p style="color: #94A3B8; margin: 8px 0 0 0; font-size: 14px;">{subtitle}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Render the standard footer."""
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; color: #64748B; font-size: 12px; padding: 10px;">
        <p>Built with ❤️ by <a href="https://github.com/qurrrrsebastian-prog" target="_blank">Avatar Putra Sigit</a>
        | Founder @AVA.Group | © 2026</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_status_badge(label: str, color: str) -> None:
    """Render a small pill-style status badge."""
    st.markdown(
        f"""
    <span style="background: {color}22; color: {color}; border: 1px solid {color}44;
        border-radius: 12px; padding: 4px 12px; font-size: 12px; font-weight: 600;">{label}</span>
    """,
        unsafe_allow_html=True,
    )


def score_color(score: int) -> str:
    """Return a colour for a skill-match score."""
    if score >= 80:
        return "#059669"
    if score >= 60:
        return "#D97706"
    return "#DC2626"


def score_badge_html(score: int) -> str:
    """Return HTML for a coloured skill-match score badge."""
    color = score_color(score)
    return (f'<span style="background:{color}22;color:{color};border:1px solid '
            f'{color}55;border-radius:10px;padding:2px 10px;font-size:12px;'
            f'font-weight:700;">{score}% match</span>')


def render_job_card(job: dict) -> None:
    """Render a compact job card for the results grid."""
    score = job.get("skill_match_score", 0)
    color = score_color(score)
    st.markdown(
        f"""
    <div style="background:{PRIMARY}0d; border:1px solid {PRIMARY}33;
        border-left:4px solid {color}; border-radius:10px; padding:14px; margin:6px 0;
        min-height:150px;">
        <div style="display:flex; justify-content:space-between; align-items:start;">
            <div style="color:#F1F5F9; font-weight:600; font-size:15px;">
                {job.get('company_name','Unknown')}</div>
            {score_badge_html(score)}
        </div>
        <div style="color:{SECONDARY}; font-size:13px; margin-top:4px;">
            {job.get('job_title','Unknown')}</div>
        <div style="color:#94A3B8; font-size:12px; margin-top:6px;">
            📍 {job.get('location','N/A')}</div>
        <div style="color:#CBD5E1; font-size:12px; margin-top:2px;">
            💰 {job.get('salary_hint','N/A')}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_card(title: str, content: str, color: str = PRIMARY) -> None:
    """Render a titled content card."""
    st.markdown(
        f"""
    <div style="background: {color}11; border: 1px solid {color}33; border-radius: 10px;
        padding: 16px; margin: 8px 0;">
        <h4 style="color: {color}; margin: 0 0 8px 0;">{title}</h4>
        <p style="color: #CBD5E1; margin: 0; font-size: 13px;">{content}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
