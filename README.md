# LAMP Reports

**Host:** <https://visual.lamp.digital>

A lightweight Flask app that lets **users**, **analysts**, and **admins** run site‑specific Python report scripts and download the results as PDF or HTML.  
Generated files live in **`outputs/`**, while the source scripts stay in **`reports/<site>/`**.

---

## Project structure

```text
.
├── app.py                  # Flask logic, auth, endpoints, CLI helpers
├── requirements.txt
├── templates/              # Jinja2 HTML (Bootstrap 5 UI)
│   ├── base.html
│   ├── index.html
│   └── login.html
├── static/                 # CSS / JS
│   └── style.css
├── reports/                # 1 folder per site, 1 + *.py per report
│   ├── bidmc/
│   │   ├── demographics.py
│   │   └── adherence.py
│   └── butler/
│       └── overview.py
└── outputs/                # auto‑created; finished PDFs/HTML + progress *.json
```

---

## Quick‑start (local dev)

```bash
# clone & set up virtual‑env
git clone https://github.com/your‑org/LAMP-cortex-cnl.git
cd dn‑reports
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# create the first admin account
flask --app app create-admin      # prompts for username + password

# run the dev server
python app.py                     # http://localhost:5000
```

---

## User management commands

| Action | Command |
| ------ | ------- |
| List accounts | `flask --app app users list` |
| Add **user** John to **bidmc** | `flask --app app users add John --role user --site bidmc` |
| Add analyst | `flask --app app users add <name> --role analyst --site <site>` |
| Add admin | `flask --app app users add <name> --role admin` |
| Reset password | `flask --app app users passwd <username>` |
| Delete account | `flask --app app users delete <username>` |

> **GUI option:** Log in as an admin and go to `/admin/` for a CRUD table.

---

## Adding a new report script

```bash
mkdir -p reports/<site>
cp template_report.py reports/<site>/my_new_report.py
```

*Each script must accept the CLI flags specified in `app.py`.*  
Flask’s auto‑reload makes the new report appear instantly in the dropdown for users allowed to see that site.

---

## Debugging cheatsheet

| Issue | Checklist |
| ----- | --------- |
| **“Report not found”** | 1 ) File exists in `outputs/`?<br>2 ) Filename contains the task‑ID? |
| Progress stuck at 0 % | Open `<task>_progress.json` in `outputs/` for the error message. |
| Script crashes | Run it manually: `python reports/<site>/<file>.py --help` |
| DB quirks | Open `database.db` with *DB Browser for SQLite* or *TablePlus*. |

Set `FLASK_DEBUG=1` for verbose tracebacks.

---

Happy reporting!  
© 2025 BIDMC Division of Digital Psychiatry
