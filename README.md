# Project Antigravity

## MD Non-Profit Sector Intelligence Portal (Forensic Unit)

**Antigravity** is a forensic dashboard and intelligence engine that aggregates data from the IRS and MD State Registry to identify compliance anomalies ("Zombie Entities") in the non-profit sector.

### Architecture
*   **Backend:** Python Flask (`ForensicCleaner` logic core)
*   **Frontend:** HTML5, Tailwind CSS, Chart.js
*   **Integrations:**
    *   **Jira:** Auto-creates tasks for high-risk entities.
    *   **Confluence:** Auto-documents entity profiles.

### Setup
1. `pip install -r requirements.txt`
2. Set Environment Variables (see `app.py`)
3. `python app.py`
