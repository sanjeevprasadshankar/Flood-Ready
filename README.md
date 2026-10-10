# 🌊 FloodReady — Early Warning & Relief Prioritisation System

> **Week 6 Mini Challenge — Datathon Dress Rehearsal**  
> A working end-to-end flood early warning prototype: raw sensor data → risk prediction → ranked village alerts → real SMS & email delivery.

---

## What This Is

FloodReady monitors **6 river gauge stations** across a flood-prone district during monsoon season. When river levels approach danger, the system:

1. Scores flood risk at each gauge using a 5-signal model
2. Ranks all 12 villages by combined flood risk + vulnerability
3. Generates plain-language alerts with specific evacuation instructions
4. Sends real **SMS**, **WhatsApp**, and **Email** alerts to village leaders and the duty officer

---

## Files in This Project

| File | What it does |
|------|-------------|
| `floodready_setup.py` | **Main file** — the entire system in one script. Run this. |
| `floodready_prototype.html` | Interactive dashboard — open in any browser |
| `floodready_village_profiles.csv` | Village data: population, shelter, road access |
| `floodready_gauge_stations.csv` | Gauge reference: warning + danger levels |
| `floodready_river_readings.csv` | 60-day sensor readings from 6 gauges |
| `README.md` | This file |
| `floodready_alerts.log` | Auto-created: log of every alert run |
| `floodready_last_run.json` | Auto-created: summary of most recent run |

---

## Quick Start (5 minutes)

### 1 — Requirements

- Python 3.8 or newer
- That's it. Everything else installs automatically.

Check your Python version:
```bash
python --version
```

### 2 — Install packages

```bash
python floodready_setup.py install
```

Installs: `twilio`, `sendgrid`, `pandas`, `numpy`

### 3 — Get free API keys

```bash
python floodready_setup.py config
```

This prints the exact signup URLs. Here's the short version:

**Twilio (SMS + WhatsApp)** — [twilio.com](https://twilio.com)
- Sign up → verify phone → go to Console
- Copy: Account SID, Auth Token, your Twilio phone number
- For WhatsApp: enable sandbox at `twilio.com/console/sms/whatsapp/sandbox`

**SendGrid (Email)** — [sendgrid.com](https://sendgrid.com)
- Sign up → Settings → API Keys → Create Key (Full Access)
- Copy the key immediately (shown only once)
- Verify your sender email in Settings → Sender Authentication

### 4 — Edit CONFIG

Open `floodready_setup.py` in any text editor and fill in the `CONFIG` block at the very top:

```python
CONFIG = {
    "TWILIO_SID":        "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "TWILIO_TOKEN":      "your_auth_token_here",
    "TWILIO_FROM_SMS":   "+1234567890",
    "TWILIO_FROM_WA":    "whatsapp:+14155238886",
    "SENDGRID_KEY":      "SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "EMAIL_FROM":        "floodready@yourdomain.com",
    "OFFICER_EMAIL":     "officer@district.gov",
    "OFFICER_PHONE":     "+919876543200",
    "TEST_PHONE":        "+91XXXXXXXXXX",   # ← your number
    "TEST_EMAIL":        "you@gmail.com",   # ← your email
}
```

Also update the `CONTACTS` dictionary with real phone numbers for each village leader (V01–V12).

### 5 — Send a test message

```bash
python floodready_setup.py test
```

Sends one SMS + one email to `TEST_PHONE` and `TEST_EMAIL`. Check your phone and inbox. If it arrives, everything is working.

### 6 — Run the pipeline

```bash
# Dry run — see what would be sent, nothing actually goes out
python floodready_setup.py run

# Live run — actually sends SMS + email
python floodready_setup.py run --send
```

### 7 — Open the dashboard

```bash
python floodready_setup.py dashboard
```

Or just double-click `floodready_prototype.html` in your file manager.

### 8 — Schedule automatic runs

```bash
python floodready_setup.py schedule
```

Prints the exact command to paste into crontab (Linux/Mac) or Task Scheduler steps (Windows) to run automatically every 30 minutes.

---

## All Commands

```
python floodready_setup.py install      Install required packages
python floodready_setup.py config       Setup instructions for API keys
python floodready_setup.py run          Dry run — prints alerts, sends nothing
python floodready_setup.py run --send   Live run — sends SMS, WhatsApp, email
python floodready_setup.py test         Test send to your own phone + email
python floodready_setup.py schedule     How to auto-run every 30 minutes
python floodready_setup.py dashboard    Open HTML dashboard in browser
python floodready_setup.py refresh      Recompute from CSV files
python floodready_setup.py status       Check packages, keys, last run
```

---

## How the System Works

### Data Pipeline

```
3 CSV files
    │
    ▼
Data Quality Fixes
  • 3 duplicate rows removed
  • River level 99.9m (sensor fault) → interpolated
  • Soil moisture 140% (impossible) → interpolated
  • Negative rainfall → set to 0
  • 6 missing rainfall values → filled with median
  • 3 missing river levels → interpolated
    │
    ▼
Feature Engineering
  • Level % of danger threshold
  • River rise rate (1-day diff)
  • Upstream level rise (leading indicator, ~1 day lag)
  • 3-day cumulative rainfall
  • Soil moisture saturation
    │
    ▼
Risk Scoring (0–100)
    │
    ▼
Village Prioritisation
    │
    ▼
Alert Generation + Delivery
```

### Risk Score Formula

Each gauge gets a score from 0–100 based on five signals:

| Signal | Weight | Reasoning |
|--------|--------|-----------|
| River level % of danger threshold | 40% | Direct proximity to flooding |
| River rise rate (m/day) | 20% | How fast it's rising right now |
| Upstream level rise | 20% | Leading indicator — shows up 1 day before |
| 3-day cumulative rainfall | 10% | Sustained input to the basin |
| Soil moisture % | 10% | Saturated soil → less absorption |

**Threshold: Score ≥ 45 → flood predicted**

### Village Priority Formula

Each village gets a priority score that combines:

- **Population + 2× vulnerable** (elderly, children, disabled) — max 35 pts
- **Shelter capacity gap** (population minus shelter capacity) — max 25 pts
- **Road access**: Cut off in floods = 30 pts, Seasonal = 15 pts, All-weather = 0 pts
- **Households without phone** (%) — max 10 pts

**Final combined score = 60% risk + 40% priority**

This ensures villages with cut-off roads and poor phone coverage rise to the top, even if the raw flood risk is equal to other villages.

### Alert Levels

| Level | Risk Score | Action |
|-------|-----------|--------|
| 🔴 CRITICAL | ≥ 70 | Immediate evacuation — 12–24 hours |
| 🟠 HIGH | 45–69 | Begin evacuation — 24–48 hours |
| 🟡 MODERATE | 25–44 | Issue warning, prepare |
| 🟢 LOW | < 25 | Monitor, no action yet |

---

## Model Performance

Evaluated on the test set (Aug 10–29, 2026), time-based split:

| Metric | Value | Notes |
|--------|-------|-------|
| Recall | **86%** | Catches 6 of 7 real floods |
| Precision | 35% | ~3 false alarms per true flood |
| F1 Score | 0.50 | Balanced measure |
| Missed floods | 1 | Only 1 flood not caught |
| Threshold | 45 | Tuned to favour recall |

**Why recall over precision?** A missed flood can cost lives. A false alarm causes inconvenience but the duty officer reviews every alert before it goes out — that human gate filters false alarms. We accept more false alarms to avoid missing real floods.

---

## Alert Delivery

When a village is flagged, the system sends:

| Channel | Who receives | When |
|---------|-------------|------|
| SMS | Village leader's phone | Always (if phone on file) |
| WhatsApp | Village group | If village's preferred channel is WhatsApp |
| Email | Village leader | If email on file |
| Officer SMS | District officer | Summary digest of all flagged villages |
| Officer Email | District officer | Full HTML report with all village details |

Villages with ≥ 40% households without phones get a mandatory loudspeaker flag in their alert — the officer sees this and knows to deploy PA systems manually.

---

## Cost

Everything runs free during development and testing.

| Service | Free tier | Production estimate |
|---------|-----------|-------------------|
| Twilio SMS | ~15 trial messages | ₹0.65/SMS in India |
| Twilio WhatsApp | Free sandbox | ₹0.50–1/message |
| SendGrid Email | 100 emails/day free forever | Free for this use case |
| Python + cron | Free | Free |

Estimated production cost for 12 villages, 2 alerts/day: **under ₹50/month**.

---

## Project Structure (inside `floodready_setup.py`)

The single file is divided into 13 clearly labelled sections:

```
Section 0   CONFIG block — your API keys and settings
Section 1   INSTALLER — pip installs all packages
Section 2   CONFIG WIZARD — setup instructions
Section 3   SMS / WhatsApp / Email senders
Section 4   Message builders (SMS text + HTML email)
Section 5   Log system — writes to floodready_alerts.log
Section 6   Main alert pipeline — the full run() function
Section 7   Test sender — sends to your own phone/email
Section 8   Scheduler — runs every N minutes forever
Section 9   Refresh from CSVs — recomputes live data
Section 10  Dashboard launcher — opens HTML in browser
Section 11  Cron setup — Linux/Mac/Windows instructions
Section 12  Status checker
Section 13  CLI entry point — handles all commands
```

---

## Responsible AI Notes

**Missed floods vs false alarms** — Threshold set at 45 to maximise recall (86%). The duty officer reviews every alert before dispatch. No SMS goes out without human approval.

**Equity of reach** — Villages with cut-off roads and high phone-less rates score higher in the priority formula, not lower. A village of 720 people with 52% no-phone and flooded roads outranks a larger village with all-weather roads.

**Data privacy** — Village vulnerability data (population breakdowns, shelter capacity) stays local. No data is sent to third-party services except the alert message text to Twilio/SendGrid.

**Fallback** — If sensors fail or the script errors, the log records the failure and the officer is not silently left without information. The last run JSON shows exactly what happened.

**Explainability** — Every alert explains in plain language: what is happening, why this village is a priority, and what action to take. No black box.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'twilio'`**
```bash
python floodready_setup.py install
```

**SMS not arriving**
- Check `TWILIO_SID` and `TWILIO_TOKEN` are correct (no extra spaces)
- On a trial account, you can only send to verified numbers — verify the recipient at `twilio.com/console/phone-numbers/verified`
- Check `TWILIO_FROM_SMS` is your actual Twilio number (with country code, e.g. `+1...`)

**Email not arriving**
- Check spam folder first
- Make sure `EMAIL_FROM` is verified in SendGrid → Settings → Sender Authentication
- `SENDGRID_KEY` must start with `SG.` — if it doesn't, regenerate it

**WhatsApp not working**
- You must join the Twilio sandbox first: send `join <your-sandbox-word>` to `+14155238886` from the recipient's phone
- `TWILIO_FROM_WA` should be `whatsapp:+14155238886` (not just the number)

**`python` not found on Windows**
```bash
py floodready_setup.py install
# or
python3 floodready_setup.py install
```

**CSV files not found during `refresh`**
- Place all 3 CSV files in the same folder as `floodready_setup.py`
- The embedded data still works without the CSVs — `run` uses that by default

---

## Built With

- **Python 3.8+** — core language
- **pandas + numpy** — data processing and risk scoring
- **Twilio** — SMS and WhatsApp delivery
- **SendGrid** — email delivery
- **Chart.js** — gauge history charts in the dashboard
- **HTML/CSS/JS** — interactive dashboard (no framework, no build step)

---

## Submission Checklist

- [x] Working prototype (`floodready_setup.py` + `floodready_prototype.html`)
- [x] End-to-end: raw data → risk score → ranked villages → real alerts
- [x] Precision and recall reported (35% / 86%)
- [x] Data quality issues documented and fixed (8 issues)
- [x] Village prioritisation using 4 factors
- [x] Explainable plain-language alerts per village
- [x] Correct delivery channel per village preference
- [x] Architecture diagram (in the prototype dashboard)
- [x] Responsible AI reflection (4 commitments)
- [x] README

---

*FloodReady — Week 6 Mini Challenge | Built by Davidcharles (thedhanushkiran)*
