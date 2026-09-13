# Real Estate Lead Qualifier
## AI-Powered Buyer Qualification and Property Matching System

> **"Our system automatically converts natural-language property enquiries into structured, scored and actionable leads — allowing brokers to focus their time on buyers most likely to convert."**

---

## Business Problem

Real estate brokers waste time manually following up with hundreds of unqualified enquiries. Most enquiries lack budget clarity, specific requirements, or purchase intent. Brokers need a system that automatically:

1. Collects buyer requirements through natural conversation
2. Matches buyers to available properties
3. Scores and ranks buyers by qualification level
4. Surfaces the most actionable leads instantly

---

## Solution

A full AI pipeline:

```
Unstructured buyer message
        ↓
   Groq AI Agent (NLU)
        ↓
 Structured Requirements
        ↓
   Property Search (CSV)
        ↓
  Matching Algorithm
        ↓
      Top 10 List
        ↓
  Lead Qualification
        ↓
     Priority Score
        ↓
    Next Action
        ↓
  Database Update
        ↓
  Broker Dashboard
```

---

## Technology Stack

| Layer       | Technology                       |
|-------------|----------------------------------|
| Frontend    | Streamlit                        |
| AI / NLU    | Groq API (llama-3.3-70b)        |
| Backend     | Python 3.9+                      |
| Data        | Pandas + CSV                     |
| Validation  | Pydantic                         |
| Config      | python-dotenv                    |

---

## Project Structure

```
real_estate_lead_qualifier/
├── app.py                    # Main Streamlit application
├── requirements.txt
├── .env                      # Your API key (create from .env.example)
├── .env.example
├── README.md
├── data/
│   ├── properties.csv        # 110 property records
│   └── buyers.csv            # Buyer leads database
├── agent/
│   ├── groq_agent.py         # Groq conversational agent
│   └── prompts.py            # System prompts
├── matching/
│   └── matcher.py            # Property scoring engine
├── qualification/
│   └── qualifier.py          # Lead qualification engine
├── database/
│   └── data_manager.py       # CSV read/write operations
└── utils/
    └── helpers.py            # Formatting utilities
```

---

## Setup

### 1. Get a Groq API Key

Sign up at https://console.groq.com and create an API key.

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```
GROQ_API_KEY=your_actual_groq_api_key_here
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## Features

### 🏠 Buyer Chat
- Natural language conversation powered by Groq llama-3.3-70b
- Extracts: name, phone, budget, location, property type, bedrooms, timeline
- Understands: "80 lakh", "Rs 80L", "eighty lakhs", "80,00,000" → same budget
- Avoids re-asking already-provided information
- Handles multi-field messages ("I'm Noel, looking for 3BHK in Kakkanad under 80L")

### 📊 Broker Dashboard
- Real-time lead metrics (Highly Qualified / Qualified / Needs Info / Low Priority)
- Full lead pipeline table sortable by qualification score
- Click any lead for detailed view with phone, budget, next action
- Priority escalation display

### 🏘️ Properties
- Browse all 110 properties
- Filter by location, type, bedrooms, availability
- Full dataset view

### 👥 Leads
- All buyer leads sorted by qualification score
- Quick overview of budget, location, match score

---

## Matching Algorithm (100-point system)

| Criteria         | Points | Logic                                    |
|------------------|--------|------------------------------------------|
| Budget           | 30     | Within range=30, 5% over=24, 20% over=10 |
| Location         | 25     | Exact=25, Same area=15, Nearby=20        |
| Property Type    | 15     | Exact=15, Semi-compatible=8              |
| Bedrooms         | 15     | Exact=15, ±1=8, ±2=3                    |
| Timeline         | 10     | Ready=10, 6mo/timeline=7-10              |
| Parking          | 5      | Match=5                                  |

---

## Qualification Scoring

| Dimension           | Max | Logic                                  |
|---------------------|-----|----------------------------------------|
| Budget Clarity      | 20  | Range=20, Max only=15                  |
| Location Clarity    | 15  | Specific location=15                   |
| Property Requirement| 15  | Type+bedrooms=15                       |
| Purchase Timeline   | 20  | ≤30 days=20, ≤60=18, ≤90=15           |
| Match Quality       | 20  | Best≥90 + 3 good=20                   |
| Engagement          | 10  | 7 fields provided=10                   |

### Status Thresholds

| Score  | Status             | Priority | Action              |
|--------|--------------------|----------|---------------------|
| 80-100 | HIGHLY_QUALIFIED   | HIGH     | Escalate to Broker  |
| 60-79  | QUALIFIED          | MEDIUM   | Schedule Site Visit |
| 40-59  | NEEDS_INFORMATION  | MEDIUM   | Collect More Info   |
| 20-39  | LOW_PRIORITY       | LOW      | Nurture             |
| 0-19   | UNQUALIFIED        | LOW      | Close               |
| —      | NO_MATCH           | LOW      | Recommend Alternatives |

---

## Example Conversation

```
AI: Hi! I'm your Real Estate Assistant. Could I start with your name?

Buyer: Noel

AI: Hi Noel! What's your phone number?

Buyer: +91 94470 12345

AI: What's your budget?

Buyer: Rs 80 lakh

AI: Great! Which location are you interested in?

Buyer: Kakkanad

AI: What type of property are you looking for?

Buyer: 3 BHK apartment

AI: When are you planning to buy?

Buyer: Within 2 months
```

**Result:**
```
🎉 Congratulations Noel! You're a Highly Qualified buyer.

Qualification Score: 88/100
Status: 🟢 HIGHLY QUALIFIED
Priority: HIGH
Next Action: ESCALATE TO BROKER

Best Match: P001 — Green Valley Residency — Rs 75L — 96% match
```

---

## Privacy

- Phone numbers are displayed **only** in the Broker Dashboard
- The buyer-facing result page shows: "A broker will contact you for further assistance."
- No external communication (no WhatsApp, SMS, or email) is triggered automatically

---

## License

MIT License — Built for hackathon demonstration purposes.
