import os
import requests
import threading
import time
from flask import Flask, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
MOCK_SDAT_DB = [
    {"ein": "52-1269677", "name": "SEVERNA PARK ATHLETIC ASSOC", "city": "SEVERNA PARK", "state_status": "Good Standing"},
    {"ein": "47-5188206", "name": "A TRIBUTE TO WOMEN OF COLOR", "city": "ODENTON", "state_status": "Good Standing"},
    {"ein": "52-2037551", "name": "21ST CENTURY EDUCATION FDN", "city": "ANNAPOLIS", "state_status": "Good Standing"},
    {"ein": "99-9999999", "name": "UNKNOWN GHOST CORP", "city": "BALTIMORE", "state_status": "Forfeited"},
]

# Environment Variables for Atlassian REST API
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL")
CONFLUENCE_USER = os.environ.get("CONFLUENCE_USER")
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN")
CONFLUENCE_SPACE = os.environ.get("CONFLUENCE_SPACE")

JIRA_URL = os.environ.get("JIRA_URL")
JIRA_USER = os.environ.get("JIRA_USER")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN")
JIRA_PROJECT = os.environ.get("JIRA_PROJECT")


class ForensicCleaner:
    """
    The Logic Core: Resolves conflicts and syncs with Confluence & Jira using REST calls.
    """

    def normalize_status(self, irs_status, state_status):
        irs = str(irs_status or "").upper()
        state = str(state_status or "").upper()

        if "REVOCATION" in irs and "GOOD STANDING" in state:
            return "Zombie Entity"
        if "REVOKED" in irs:
            return "Revoked"
        if "FORFEITED" in state or "NOT GOOD" in state:
            return "Revoked"
        if "GOOD STANDING" in state:
            return "Good Standing"
        return "Unknown"

    def clean_money(self, val):
        if not val:
            return 0
        try:
            return int(val)
        except Exception:
            return 0

    def fetch_irs_data(self, ein: str):
        clean_ein = ein.replace("-", "")
        url = f"https://projects.propublica.org/nonprofits/api/v2/organizations/{clean_ein}.json"
        try:
            time.sleep(0.1)
            headers = {"User-Agent": "AntigravityForensicUnit/1.0 (internal-research-tool)"}
            resp = requests.get(url, headers=headers, timeout=5)
            resp.raise_for_status()
            org = resp.json().get("organization", {}) if resp.content else {}
            return {
                "status": "Auto-Revocation" if org.get("revocation_date") else "Active",
                "assets": org.get("asset_amount"),
                "income": org.get("revenue_amount"),
                "mission": org.get("ntee_code"),
            }
        except Exception:
            return {"status": "Unknown", "assets": 0, "income": 0, "mission": None}

    def anneal(self):
        report = []
        for row in MOCK_SDAT_DB:
            fed = self.fetch_irs_data(row["ein"])
            status = self.normalize_status(fed["status"], row["state_status"])
            record = {
                "ein": row["ein"],
                "name": row["name"],
                "city": row["city"],
                "assets": self.clean_money(fed["assets"]),
                "income": self.clean_money(fed["income"]),
                "status": status,
                "category": fed["mission"] or "General",
                "risk_score": 100 if status in ["Zombie Entity", "Revoked"] else 0,
            }
            report.append(record)
        return report

    def sync_confluence(self, report):
        if not all([CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_TOKEN, CONFLUENCE_SPACE]):
            print("Skipping Confluence sync: missing credentials.")
            return

        auth = (CONFLUENCE_USER, CONFLUENCE_TOKEN)
        headers = {"Content-Type": "application/json"}

        # Create a single report page
        title = f"Forensic Report - {time.strftime('%Y-%m-%d %H:%M:%S')}"
        rows = ""
        for item in report:
            color = "#ffdddd" if item['risk_score'] > 0 else "#ffffff"
            rows += f"<tr style='background-color:{color}'><td>{item['ein']}</td><td>{item['name']}</td><td>{item['status']}</td><td>{item['assets']}</td></tr>"

        html_body = f"""
        <h2>Forensic Intelligence Scan</h2>
        <table>
            <thead><tr><th>EIN</th><th>Name</th><th>Status</th><th>Assets</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """

        data = {
            "title": title,
            "type": "page",
            "space": {"key": CONFLUENCE_SPACE},
            "body": {
                "storage": {
                    "value": html_body,
                    "representation": "storage"
                }
            }
        }

        try:
            resp = requests.post(f"{CONFLUENCE_URL}/wiki/rest/api/content", json=data, auth=auth, headers=headers)
            if resp.status_code == 200:
                print(f"✅ Confluence Page Created: {title}")
            else:
                print(f"❌ Confluence Error: {resp.text}")
        except Exception as e:
            print(f"❌ Confluence Exception: {e}")

    def sync_jira(self, report):
        if not all([JIRA_URL, JIRA_USER, JIRA_TOKEN, JIRA_PROJECT]):
            print("Skipping Jira sync: missing credentials.")
            return

        auth = (JIRA_USER, JIRA_TOKEN)
        headers = {"Content-Type": "application/json"}

        for item in report:
            if item['risk_score'] > 50:
                summary = f"Investigate Zombie Entity: {item['name']} ({item['ein']})"
                description = f"""
                *Entity Detected as compliance risk.*

                *EIN:* {item['ein']}
                *Name:* {item['name']}
                *City:* {item['city']}
                *Assets:* {item['assets']}
                *Status:* {item['status']}

                Please conduct forensic accountant review immediately.
                """

                payload = {
                    "fields": {
                        "project": {"key": JIRA_PROJECT},
                        "summary": summary,
                        "description": description,
                        "issuetype": {"name": "Task"}
                    }
                }

                try:
                    # Note: In a real app we'd check for duplicates first
                    resp = requests.post(f"{JIRA_URL}/rest/api/2/issue", json=payload, auth=auth, headers=headers)
                    if resp.status_code == 201:
                        print(f"✅ Jira Task Created: {summary}")
                    else:
                        print(f"❌ Jira Error: {resp.text}")
                except Exception as e:
                    print(f"❌ Jira Exception: {e}")

# --- ROUTES ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/intelligence")
def get_intelligence():
    cleaner = ForensicCleaner()
    report = cleaner.anneal()

    # Background threads for sync
    threading.Thread(target=cleaner.sync_confluence, args=(report,), daemon=True).start()
    threading.Thread(target=cleaner.sync_jira, args=(report,), daemon=True).start()

    return jsonify(report)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
