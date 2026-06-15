# 🔍 Autonomous Job Research Agent

![Python](https://img.shields.io/badge/Python-3.14-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-API-orange)
![DuckDuckGo](https://img.shields.io/badge/DuckDuckGo-Search-green)

AI agent that autonomously searches job vacancies across the web and matches them against your skill profile. Built for job hunters in Indonesia.

## 🚀 Features
- **Auto Query Generation** — AI generates optimized search queries for job portals
- **Multi-Source Search** — Searches across LinkedIn, JobStreet, Kalibrr, Glints via DuckDuckGo
- **Skill Match Scoring** — AI analyzes job requirements vs your skills (1-100 score)
- **Missing Skill Detection** — Know exactly what to learn before applying
- **CSV Export** — Download all results for offline tracking

## 🛠️ Tech Stack
- Python 3.14
- Streamlit (UI)
- Groq API — Llama 3.3 70B (AI analysis)
- DuckDuckGo Search (web search)
- BeautifulSoup + Requests (lightweight scraping)

## ⚡ Run Instructions

```powershell
cd C:\Users\Avatar Putra\Downloads\portfolio-sprint\autonomous-web-research
$env:GROQ_API_KEY="gsk_your_key_here"
pip install -r requirements.txt
streamlit run app.py
```

## 🧠 How It Works
1. You enter a **Job Role**, **Location**, and **Experience Level**.
2. Groq (Llama 3.3 70B) generates 3 optimized Indonesian/English search queries targeting major job portals.
3. DuckDuckGo searches the web (top 5 results per query, up to 15 URLs).
4. The agent scrapes lightweight title + snippet data from each result.
5. Groq analyzes all snippets and returns structured job data with a 1–100 skill match score.
6. Results are shown as metrics, a sortable table, and detailed expanders — plus a one-click CSV export.

## 👤 Author
**Avatar Putra Sigit**
- GitHub: [qurrrrsebastian-prog](https://github.com/qurrrrsebastian-prog)
- LinkedIn: [avatarputrasigit](https://www.linkedin.com/in/avatarputrasigit)
