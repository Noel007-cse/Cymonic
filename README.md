# Cymonic

Cymonic is a Python monorepo built around AI-powered agent applications. It's managed with [uv](https://docs.astral.sh/uv/) and currently ships two pieces:

- **`src/cymonic`** — the base `cymonic` Python package / CLI entry point for the project.
- **`real_estate_lead_qualifier`** — a full Streamlit application that turns natural-language buyer enquiries into structured, scored, and actionable real-estate leads using a Groq-powered agent.

---

## Repository Structure

```
Cymonic/
├── pyproject.toml                 # Root package config (managed with uv)
├── uv.lock                        # Locked dependency versions
├── .python-version                # Pinned Python version (3.13)
├── src/
│   └── cymonic/
│       └── __init__.py            # `cymonic` package entry point (main())
└── real_estate_lead_qualifier/
    ├── app.py                     # Streamlit application (UI + orchestration)
    ├── requirements.txt           # Standalone requirements for the sub-app
    ├── README.md                  # Detailed docs for this application
    ├── agent/
    │   ├── groq_agent.py          # Conversational agent (Groq llama-3.3-70b)
    │   └── prompts.py             # System prompts for the agent
    ├── matching/
    │   └── matcher.py             # Buyer ↔ property scoring engine
    ├── qualification/
    │   └── qualifier.py           # Lead qualification / scoring engine
    ├── database/
    │   └── data_manager.py        # CSV-backed read/write layer
    ├── utils/
    │   └── helpers.py             # Formatting helpers (currency, badges, etc.)
    └── data/
        ├── properties.csv         # Sample property listings
        └── buyers.csv             # Buyer leads database
```

---

## What's Inside

### 1. `cymonic` package

A minimal root-level Python package, installable via `uv`/`pip`, exposing a `cymonic` console script:

```bash
cymonic
# -> Hello from cymonic!
```

This is the scaffold for the project's core package — extend `src/cymonic/__init__.py` as the project grows.

### 2. Real Estate Lead Qualifier

The flagship application in this repo. It's an end-to-end pipeline that:

1. Chats with a prospective buyer in natural language (Groq `llama-3.3-70b`)
2. Extracts structured requirements (budget, location, property type, bedrooms, timeline, etc.)
3. Matches the buyer against a property database (CSV-backed) using a 100-point scoring algorithm
4. Qualifies the lead (Highly Qualified / Qualified / Needs Information / Low Priority / Unqualified)
5. Surfaces prioritized leads on a broker-facing dashboard built in Streamlit

See **[`real_estate_lead_qualifier/README.md`](real_estate_lead_qualifier/README.md)** for full details, including the matching algorithm, qualification scoring rubric, and an example conversation.

---

## Getting Started

### Prerequisites

- Python **3.13** (see `.python-version`)
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- A [Groq API key](https://console.groq.com) (required for the lead qualifier's AI agent)

### 1. Clone the repository

```bash
git clone https://github.com/Noel007-cse/Cymonic.git
cd Cymonic
```

### 2. Install the root package

Using `uv` (recommended — resolves against `uv.lock`):

```bash
uv sync
```

Or with `pip`:

```bash
pip install -e .
```

### 3. Set up and run the Real Estate Lead Qualifier

```bash
cd real_estate_lead_qualifier
pip install -r requirements.txt
cp .env.example .env      # then add your GROQ_API_KEY
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

Full setup, features, scoring tables, and an example conversation are documented in the [sub-app README](real_estate_lead_qualifier/README.md).

---

## Tech Stack

| Layer         | Technology                          |
|---------------|--------------------------------------|
| Language      | Python 3.13                          |
| Package mgmt  | uv                                    |
| Web framework | FastAPI, Streamlit                    |
| AI / Agents   | LangChain, LangGraph, Groq API        |
| HTTP client   | httpx                                 |
| Server        | uvicorn                               |
| Config        | python-dotenv                         |
| Data          | pandas, CSV                           |
| Validation    | Pydantic                              |

---

## Project Status

This repository is under active development. The `cymonic` root package currently acts as a scaffold, while `real_estate_lead_qualifier` is a working demo application (originally built for a hackathon). Contributions and issues are welcome.

## License

MIT License — see individual sub-project directories for any additional notices.
