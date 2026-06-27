# Project #16 — Autonomous Web Research Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/DuckDuckGo-DE5833?style=flat&logo=duckduckgo&logoColor=white" />
  <img src="https://img.shields.io/badge/Agentic%20AI-7B2CBF?style=flat" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" />
</p>

> AI agent yang mencari lowongan kerja di LinkedIn, JobStreet, Kalibrr, Glints — lalu cocokkan dengan skill kamu. Auto fallback data demo + skill match scoring.

---

## Demo Langsung

[![Deploy to Streamlit Cloud](https://img.shields.io/badge/Deploy-Streamlit%20Cloud-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://share.streamlit.io/deploy?repository=qurrrrsebastian-prog/autonomous-web-research)

**Tech Stack:** `DuckDuckGo Search` · `LangChain` · `Skill Matching` · `Streamlit` · `CSV Export`

---

## Fitur

| Fitur | Status |
|-------|--------|
| Multi-platform job search | ✅ |
| Skill match scoring | ✅ |
| CSV export hasil | ✅ |
| Auto fallback demo data | ✅ |
| Direct link ke job portal | ✅ |
| Tema gelap AVA purple | ✅ |

---

## Cara Menjalankan

```bash
git clone https://github.com/qurrrrsebastian-prog/autonomous-web-research.git
cd autonomous-web-research
pip install -r requirements.txt
streamlit run app.py
```

## Deploy ke Streamlit Cloud (GRATIS)

1. [share.streamlit.io](https://share.streamlit.io) → Login GitHub
2. **New app** → Pilih repo ini
3. **Deploy** (tidak perlu API key!)

---

## Struktur Project

```
autonomous-web-research/
├── app.py              # Main Streamlit app (32KB)
├── requirements.txt    # Dependencies
├── .streamlit/
│   └── config.toml    # AVA purple branding
├── .gitignore
└── LICENSE            # MIT License
```

---

**Dibuat oleh:** [Avatar Putra Sigit](https://github.com/qurrrrsebastian-prog) · Founder @AVA.Group
