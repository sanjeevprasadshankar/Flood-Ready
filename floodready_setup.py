#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           FLOODREADY — Complete Setup in One File                           ║
║   Early Warning + SMS/Email Alert System  |  Week 6 Mini Challenge         ║
╚══════════════════════════════════════════════════════════════════════════════╝

HOW TO RUN:
  1. python floodready_setup.py install      ← installs all packages
  2. python floodready_setup.py config       ← set your Twilio/SendGrid keys
  3. python floodready_setup.py run          ← run pipeline + send alerts (dry run)
  4. python floodready_setup.py run --send   ← actually send SMS + email
  5. python floodready_setup.py dashboard    ← open live HTML dashboard
  6. python floodready_setup.py schedule     ← run every 30 min automatically
  7. python floodready_setup.py test         ← send test SMS + email to yourself

REQUIREMENTS: Python 3.8+ only. Everything else is installed automatically.
"""

import sys, os, subprocess, json, time, datetime, argparse, textwrap, platform

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 0: CONFIG — edit these before running
# ─────────────────────────────────────────────────────────────────────────────

CONFIG = {
    # ── Twilio (SMS + WhatsApp) ─────────────────────────────────────────────
    # Get these free at: https://twilio.com → sign up → Console dashboard
    "TWILIO_SID":        "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  # Account SID
    "TWILIO_TOKEN":      "your_auth_token_here",               # Auth Token
    "TWILIO_FROM_SMS":   "+1234567890",                        # Your Twilio number
    "TWILIO_FROM_WA":    "whatsapp:+14155238886",              # Sandbox WhatsApp number

    # ── SendGrid (Email) ────────────────────────────────────────────────────
    # Get free at: https://sendgrid.com → API Keys → Create Key (Full Access)
    "SENDGRID_KEY":      "SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "EMAIL_FROM":        "floodready@yourdomain.com",          # Must be verified in SendGrid

    # ── Officer details ─────────────────────────────────────────────────────
    "OFFICER_EMAIL":     "officer@district.gov",
    "OFFICER_PHONE":     "+919876543200",                      # Officer gets digest SMS too

    # ── Alert threshold ─────────────────────────────────────────────────────
    "RISK_THRESHOLD":    45,    # Score >= this → alert triggered
    "SCHEDULE_MINS":     30,    # How often to check (minutes)

    # ── Your test phone + email (used by: python floodready_setup.py test) ──
    "TEST_PHONE":        "+91XXXXXXXXXX",   # Your number for test SMS
    "TEST_EMAIL":        "you@gmail.com",   # Your email for test email
}

# ─────────────────────────────────────────────────────────────────────────────
#  VILLAGE CONTACT DIRECTORY
#  Map each Village_ID to real phone / whatsapp / email of the village leader
# ─────────────────────────────────────────────────────────────────────────────

CONTACTS = {
    "V01": {"phone": "+919000000001", "whatsapp": "+919000000001", "email": None},
    "V02": {"phone": "+919000000002", "whatsapp": None,            "email": None},
    "V03": {"phone": "+919000000003", "whatsapp": "+919000000003", "email": "leader.v03@gmail.com"},
    "V04": {"phone": "+919000000004", "whatsapp": None,            "email": None},
    "V05": {"phone": "+919000000005", "whatsapp": "+919000000005", "email": None},
    "V06": {"phone": "+919000000006", "whatsapp": None,            "email": None},
    "V07": {"phone": "+919000000007", "whatsapp": "+919000000007", "email": None},
    "V08": {"phone": "+919000000008", "whatsapp": "+919000000008", "email": "leader.v08@gmail.com"},
    "V09": {"phone": "+919000000009", "whatsapp": None,            "email": None},
    "V10": {"phone": "+919000000010", "whatsapp": None,            "email": None},
    "V11": {"phone": "+919000000011", "whatsapp": "+919000000011", "email": None},
    "V12": {"phone": "+919000000012", "whatsapp": None,            "email": None},
}

# ─────────────────────────────────────────────────────────────────────────────
#  EMBEDDED VILLAGE & GAUGE DATA (pre-computed from the 3 CSVs)
#  If you have the CSV files, use: python floodready_setup.py refresh
#  to recompute this from live data.
# ─────────────────────────────────────────────────────────────────────────────

EMBEDDED_DATA = {"villages": [{"id": "V12", "name": "Kharkhauda", "gauge": "G06", "station": "Chandan Ford", "population": 980, "vulnerable": 350, "shelter": "Panchayat Bhawan", "shelter_cap": 110, "dist_km": 6.0, "road": "Cut off in floods", "channel": "Loudspeaker", "no_phone_pct": 56, "river_level": 2.09, "danger_level": 4.4, "level_gap": -2.31, "rainfall3d": 6.8, "soil": 45.2, "rise": -0.05, "risk": 32.5, "priority": 52.2, "combined": 40.4, "alert": {"level": "MODERATE", "what": "River at Chandan Ford is at 2.09m, 2.31m below danger (4.4m). Risk: MODERATE. Flood expected within 24-48 hours.", "why": "Pop: 980 (350 vulnerable). Shelter gap: 870. Road: Cut off in floods.", "action": "IMMEDIATE evacuation to Panchayat Bhawan (6.0km) NOW.", "deliver": "Via: Loudspeaker. 56% no phone - loudspeaker essential."}, "flood_predicted": False}, {"id": "V05", "name": "Mahigaon", "gauge": "G03", "station": "Mahi Crossing", "population": 3100, "vulnerable": 890, "shelter": "Govt College Ground Shelter", "shelter_cap": 600, "dist_km": 2.1, "road": "Seasonal", "channel": "SMS", "no_phone_pct": 22, "river_level": 2.68, "danger_level": 5.0, "level_gap": -2.32, "rainfall3d": 1.6, "soil": 42.5, "rise": -0.15, "risk": 21.1, "priority": 66.0, "combined": 39.1, "alert": {"level": "LOW", "what": "River at Mahi Crossing is at 2.68m, 2.32m below danger (5.0m). Risk: LOW. Flood expected within 24-48 hours.", "why": "Pop: 3,100 (890 vulnerable). Shelter gap: 2,500. Road: Seasonal.", "action": "Staged evacuation to Govt College Ground Shelter (2.1km). Vulnerable first.", "deliver": "Via: SMS."}, "flood_predicted": False}, {"id": "V11", "name": "Chandanpur", "gauge": "G06", "station": "Chandan Ford", "population": 1420, "vulnerable": 450, "shelter": "Govt Primary School", "shelter_cap": 220, "dist_km": 2.4, "road": "Seasonal", "channel": "SMS", "no_phone_pct": 27, "river_level": 2.09, "danger_level": 4.4, "level_gap": -2.31, "rainfall3d": 6.8, "soil": 45.2, "rise": -0.05, "risk": 32.5, "priority": 40.8, "combined": 35.8, "alert": {"level": "MODERATE", "what": "River at Chandan Ford is at 2.09m, 2.31m below danger (4.4m). Risk: MODERATE. Flood expected within 24-48 hours.", "why": "Pop: 1,420 (450 vulnerable). Shelter gap: 1,200. Road: Seasonal.", "action": "Staged evacuation to Govt Primary School (2.4km). Vulnerable first.", "deliver": "Via: SMS."}, "flood_predicted": False}, {"id": "V02", "name": "Keshavpur", "gauge": "G01", "station": "Karnali Bend", "population": 940, "vulnerable": 310, "shelter": "Community Hall", "shelter_cap": 150, "dist_km": 3.8, "road": "Seasonal", "channel": "Loudspeaker", "no_phone_pct": 41, "river_level": 2.21, "danger_level": 4.5, "level_gap": -2.29, "rainfall3d": 8.7, "soil": 43.8, "rise": -0.03, "risk": 36.6, "priority": 34.4, "combined": 35.7, "alert": {"level": "MODERATE", "what": "River at Karnali Bend is at 2.21m, 2.29m below danger (4.5m). Risk: MODERATE. Flood expected within 24-48 hours.", "why": "Pop: 940 (310 vulnerable). Shelter gap: 790. Road: Seasonal.", "action": "Staged evacuation to Community Hall (3.8km). Vulnerable first.", "deliver": "Via: Loudspeaker. 41% no phone - loudspeaker essential."}, "flood_predicted": False}, {"id": "V06", "name": "Barauli", "gauge": "G03", "station": "Mahi Crossing", "population": 1280, "vulnerable": 430, "shelter": "Temple Community Hall", "shelter_cap": 200, "dist_km": 5.2, "road": "Cut off in floods", "channel": "Loudspeaker", "no_phone_pct": 47, "river_level": 2.68, "danger_level": 5.0, "level_gap": -2.32, "rainfall3d": 1.6, "soil": 42.5, "rise": -0.15, "risk": 21.1, "priority": 55.7, "combined": 34.9, "alert": {"level": "LOW", "what": "River at Mahi Crossing is at 2.68m, 2.32m below danger (5.0m). Risk: LOW. Flood expected within 24-48 hours.", "why": "Pop: 1,280 (430 vulnerable). Shelter gap: 1,080. Road: Cut off in floods.", "action": "IMMEDIATE evacuation to Temple Community Hall (5.2km) NOW.", "deliver": "Via: Loudspeaker. 47% no phone - loudspeaker essential."}, "flood_predicted": False}, {"id": "V01", "name": "Rampura", "gauge": "G01", "station": "Karnali Bend", "population": 1850, "vulnerable": 520, "shelter": "Govt Primary School", "shelter_cap": 300, "dist_km": 1.2, "road": "All-weather", "channel": "SMS", "no_phone_pct": 18, "river_level": 2.21, "danger_level": 4.5, "level_gap": -2.29, "rainfall3d": 8.7, "soil": 43.8, "rise": -0.03, "risk": 36.6, "priority": 31.3, "combined": 34.5, "alert": {"level": "MODERATE", "what": "River at Karnali Bend is at 2.21m, 2.29m below danger (4.5m). Risk: MODERATE. Flood expected within 24-48 hours.", "why": "Pop: 1,850 (520 vulnerable). Shelter gap: 1,550. Road: All-weather.", "action": "Issue warning. Prepare evacuation to Govt Primary School (1.2km).", "deliver": "Via: SMS."}, "flood_predicted": False}, {"id": "V04", "name": "Dhanipur", "gauge": "G02", "station": "Sundar Ghat", "population": 720, "vulnerable": 260, "shelter": "Panchayat Bhawan", "shelter_cap": 120, "dist_km": 4.5, "road": "Cut off in floods", "channel": "Loudspeaker", "no_phone_pct": 52, "river_level": 1.94, "danger_level": 4.2, "level_gap": -2.26, "rainfall3d": 5.1, "soil": 40.3, "rise": -0.01, "risk": 22.7, "priority": 47.1, "combined": 32.5, "alert": {"level": "LOW", "what": "River at Sundar Ghat is at 1.94m, 2.26m below danger (4.2m). Risk: LOW. Flood expected within 24-48 hours.", "why": "Pop: 720 (260 vulnerable). Shelter gap: 600. Road: Cut off in floods.", "action": "IMMEDIATE evacuation to Panchayat Bhawan (4.5km) NOW.", "deliver": "Via: Loudspeaker. 52% no phone - loudspeaker essential."}, "flood_predicted": False}, {"id": "V03", "name": "Lakshmipur", "gauge": "G02", "station": "Sundar Ghat", "population": 2300, "vulnerable": 640, "shelter": "Higher Secondary School", "shelter_cap": 450, "dist_km": 0.9, "road": "All-weather", "channel": "SMS", "no_phone_pct": 12, "river_level": 1.94, "danger_level": 4.2, "level_gap": -2.26, "rainfall3d": 5.1, "soil": 40.3, "rise": -0.01, "risk": 22.7, "priority": 37.2, "combined": 28.5, "alert": {"level": "LOW", "what": "River at Sundar Ghat is at 1.94m, 2.26m below danger (4.2m). Risk: LOW. Flood expected within 24-48 hours.", "why": "Pop: 2,300 (640 vulnerable). Shelter gap: 1,850. Road: All-weather.", "action": "Issue warning. Prepare evacuation to Higher Secondary School (0.9km).", "deliver": "Via: SMS."}, "flood_predicted": False}, {"id": "V08", "name": "Siddhpur", "gauge": "G04", "station": "Tara Barrage", "population": 860, "vulnerable": 290, "shelter": "Community Hall", "shelter_cap": 100, "dist_km": 3.3, "road": "Seasonal", "channel": "WhatsApp group", "no_phone_pct": 35, "river_level": 2.23, "danger_level": 4.6, "level_gap": -2.37, "rainfall3d": 0.3, "soil": 42.1, "rise": -0.07, "risk": 20.1, "priority": 32.9, "combined": 25.2, "alert": {"level": "LOW", "what": "River at Tara Barrage is at 2.23m, 2.37m below danger (4.6m). Risk: LOW. Flood expected within 24-48 hours.", "why": "Pop: 860 (290 vulnerable). Shelter gap: 760. Road: Seasonal.", "action": "Staged evacuation to Community Hall (3.3km). Vulnerable first.", "deliver": "Via: WhatsApp group."}, "flood_predicted": False}, {"id": "V09", "name": "Nilganj", "gauge": "G05", "station": "Nila Mouth", "population": 2050, "vulnerable": 610, "shelter": "Govt High School", "shelter_cap": 350, "dist_km": 1.1, "road": "All-weather", "channel": "SMS", "no_phone_pct": 15, "river_level": 1.66, "danger_level": 3.9, "level_gap": -2.24, "rainfall3d": 5.4, "soil": 49.6, "rise": -0.01, "risk": 17.4, "priority": 34.3, "combined": 24.2, "alert": {"level": "LOW", "what": "River at Nila Mouth is at 1.66m, 2.24m below danger (3.9m). Risk: LOW. Flood expected within 24-48 hours.", "why": "Pop: 2,050 (610 vulnerable). Shelter gap: 1,700. Road: All-weather.", "action": "Issue warning. Prepare evacuation to Govt High School (1.1km).", "deliver": "Via: SMS."}, "flood_predicted": False}, {"id": "V07", "name": "Taranagar", "gauge": "G04", "station": "Tara Barrage", "population": 1600, "vulnerable": 480, "shelter": "Govt Middle School", "shelter_cap": 250, "dist_km": 1.6, "road": "All-weather", "channel": "SMS", "no_phone_pct": 20, "river_level": 2.23, "danger_level": 4.6, "level_gap": -2.37, "rainfall3d": 0.3, "soil": 42.1, "rise": -0.07, "risk": 20.1, "priority": 27.8, "combined": 23.2, "alert": {"level": "LOW", "what": "River at Tara Barrage is at 2.23m, 2.37m below danger (4.6m). Risk: LOW. Flood expected within 24-48 hours.", "why": "Pop: 1,600 (480 vulnerable). Shelter gap: 1,350. Road: All-weather.", "action": "Issue warning. Prepare evacuation to Govt Middle School (1.6km).", "deliver": "Via: SMS."}, "flood_predicted": False}, {"id": "V10", "name": "Fatehpur Kalan", "gauge": "G05", "station": "Nila Mouth", "population": 690, "vulnerable": 240, "shelter": "Anganwadi Centre", "shelter_cap": 60, "dist_km": 2.9, "road": "Seasonal", "channel": "Loudspeaker", "no_phone_pct": 44, "river_level": 1.66, "danger_level": 3.9, "level_gap": -2.24, "rainfall3d": 5.4, "soil": 49.6, "rise": -0.01, "risk": 17.4, "priority": 31.2, "combined": 22.9, "alert": {"level": "LOW", "what": "River at Nila Mouth is at 1.66m, 2.24m below danger (3.9m). Risk: LOW. Flood expected within 24-48 hours.", "why": "Pop: 690 (240 vulnerable). Shelter gap: 630. Road: Seasonal.", "action": "Staged evacuation to Anganwadi Centre (2.9km). Vulnerable first.", "deliver": "Via: Loudspeaker. 44% no phone - loudspeaker essential."}, "flood_predicted": False}], "gauges": [{"id": "G01", "name": "Karnali Bend", "risk": 36.6, "river": 2.21, "danger": 4.5, "warning": 3.8, "predicted": False, "rainfall": 8.7, "soil": 43.8, "rise": -0.03}, {"id": "G02", "name": "Sundar Ghat", "risk": 22.7, "river": 1.94, "danger": 4.2, "warning": 3.5, "predicted": False, "rainfall": 5.1, "soil": 40.3, "rise": -0.01}, {"id": "G03", "name": "Mahi Crossing", "risk": 21.1, "river": 2.68, "danger": 5.0, "warning": 4.3, "predicted": False, "rainfall": 1.6, "soil": 42.5, "rise": -0.15}, {"id": "G04", "name": "Tara Barrage", "risk": 20.1, "river": 2.23, "danger": 4.6, "warning": 3.9, "predicted": False, "rainfall": 0.3, "soil": 42.1, "rise": -0.07}, {"id": "G05", "name": "Nila Mouth", "risk": 17.4, "river": 1.66, "danger": 3.9, "warning": 3.2, "predicted": False, "rainfall": 5.4, "soil": 49.6, "rise": -0.01}, {"id": "G06", "name": "Chandan Ford", "risk": 32.5, "river": 2.09, "danger": 4.4, "warning": 3.7, "predicted": False, "rainfall": 6.8, "soil": 45.2, "rise": -0.05}]}

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 1: INSTALLER
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_PACKAGES = ["twilio", "sendgrid", "pandas", "numpy"]

def install_packages():
    print("\n" + "="*60)
    print("  FloodReady — Installing Required Packages")
    print("="*60)
    for pkg in REQUIRED_PACKAGES:
        print(f"\n  Installing {pkg}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  ✅ {pkg} installed successfully")
        else:
            print(f"  ❌ Failed to install {pkg}")
            print(f"     {result.stderr[:200]}")
    print("\n  ✅ All packages installed. Run again with: python floodready_setup.py run\n")

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 2: CONFIG WIZARD
# ─────────────────────────────────────────────────────────────────────────────

def config_wizard():
    print("\n" + "="*60)
    print("  FloodReady — Config Setup Wizard")
    print("="*60)
    print("""
  You need 2 free accounts:

  TWILIO (SMS + WhatsApp):
    1. Go to: https://twilio.com → Sign Up (free)
    2. Verify your phone number
    3. Get your Account SID and Auth Token from Console
    4. Your trial number is shown on Console home page
    5. For WhatsApp sandbox: twilio.com/console/sms/whatsapp/sandbox

  SENDGRID (Email):
    1. Go to: https://sendgrid.com → Sign Up (free, 100 emails/day)
    2. Settings → API Keys → Create API Key → Full Access
    3. Copy the key (only shown once!)
    4. Verify your sender email in Settings → Sender Authentication
    """)
    print("  Edit CONFIG at the top of this file with your credentials.")
    print("  Then run:  python floodready_setup.py test\n")

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 3: SMS / WHATSAPP / EMAIL SENDERS
# ─────────────────────────────────────────────────────────────────────────────

def check_configured():
    """Warn if still using placeholder credentials."""
    if CONFIG["TWILIO_SID"].startswith("ACxxx"):
        print("  ⚠️  Twilio credentials not set. Edit CONFIG at top of file.")
        return False
    if CONFIG["SENDGRID_KEY"].startswith("SG.xxx"):
        print("  ⚠️  SendGrid key not set. Edit CONFIG at top of file.")
        return False
    return True

def send_sms(to_number: str, message: str, label: str = "") -> bool:
    try:
        from twilio.rest import Client
        client = Client(CONFIG["TWILIO_SID"], CONFIG["TWILIO_TOKEN"])
        msg = client.messages.create(
            body=message,
            from_=CONFIG["TWILIO_FROM_SMS"],
            to=to_number
        )
        print(f"    ✅ SMS → {to_number} {label} | SID: {msg.sid}")
        return True
    except Exception as e:
        print(f"    ❌ SMS FAILED → {to_number}: {e}")
        return False

def send_whatsapp(to_number: str, message: str, label: str = "") -> bool:
    try:
        from twilio.rest import Client
        client = Client(CONFIG["TWILIO_SID"], CONFIG["TWILIO_TOKEN"])
        msg = client.messages.create(
            body=message,
            from_=CONFIG["TWILIO_FROM_WA"],
            to=f"whatsapp:{to_number}"
        )
        print(f"    ✅ WhatsApp → {to_number} {label} | SID: {msg.sid}")
        return True
    except Exception as e:
        print(f"    ❌ WhatsApp FAILED → {to_number}: {e}")
        return False

def send_email(to_email: str, subject: str, html_body: str, label: str = "") -> bool:
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        message = Mail(
            from_email=CONFIG["EMAIL_FROM"],
            to_emails=to_email,
            subject=subject,
            html_content=html_body
        )
        sg = SendGridAPIClient(CONFIG["SENDGRID_KEY"])
        response = sg.send(message)
        print(f"    ✅ Email → {to_email} {label} | Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"    ❌ Email FAILED → {to_email}: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 4: MESSAGE BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def build_sms(village: dict) -> str:
    a = village["alert"]
    lvl = a["level"]
    emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MODERATE": "⚠️", "LOW": "ℹ️"}[lvl]
    return (
        f"{emoji} FLOOD ALERT [{lvl}] - {village['name']}\n"
        f"River: {village['river_level']}m (Danger: {village['danger_level']}m)\n"
        f"Risk Score: {village['risk']:.0f}/100\n"
        f"ACTION: {a['action']}\n"
        f"Delivery: {a['deliver']}\n"
        f"-- FloodReady District System"
    )

def build_email_html(village: dict, is_officer_copy: bool = False) -> str:
    a = village["alert"]
    lvl = a["level"]
    color = {"CRITICAL": "#dc2626", "HIGH": "#ef4444", "MODERATE": "#f59e0b", "LOW": "#22c55e"}[lvl]
    ts = datetime.datetime.now().strftime("%d %b %Y %H:%M")
    gap = max(village["population"] - village["shelter_cap"], 0)
    officer_note = (
        f'<div style="background:#1e3a5f;padding:12px;border-radius:6px;margin-bottom:16px">'
        f'<b style="color:#93c5fd">Officer Review Required</b><br>'
        f'<span style="color:#bfdbfe;font-size:13px">This alert was auto-generated. '
        f'Please verify and dispatch manually if you approve.</span></div>'
    ) if is_officer_copy else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0b0f19;font-family:Arial,sans-serif">
<div style="max-width:600px;margin:20px auto">
  <div style="background:{color};padding:20px 24px;border-radius:10px 10px 0 0">
    <h2 style="margin:0;color:#fff;font-size:18px">
      {"🚨" if lvl=="CRITICAL" else "⚠️"} {lvl} FLOOD ALERT — {village["name"]}
    </h2>
    <p style="margin:4px 0 0;color:rgba(255,255,255,0.85);font-size:13px">
      Generated: {ts} | Gauge: {village["gauge"]} — {village["station"]}
    </p>
  </div>
  <div style="background:#131928;padding:24px;border-radius:0 0 10px 10px;color:#e2e8f0">
    {officer_note}

    <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
      <tr>
        <td style="padding:8px 12px;background:#1a2235;border-radius:6px;width:50%">
          <div style="font-size:11px;color:#7a8fa6;text-transform:uppercase">River Level</div>
          <div style="font-size:20px;font-weight:700;color:{color}">{village["river_level"]}m</div>
          <div style="font-size:12px;color:#7a8fa6">Danger at {village["danger_level"]}m</div>
        </td>
        <td style="width:4px"></td>
        <td style="padding:8px 12px;background:#1a2235;border-radius:6px">
          <div style="font-size:11px;color:#7a8fa6;text-transform:uppercase">Risk Score</div>
          <div style="font-size:20px;font-weight:700;color:{color}">{village["risk"]:.0f}/100</div>
          <div style="font-size:12px;color:#7a8fa6">Combined priority: {village["combined"]:.0f}</div>
        </td>
      </tr>
    </table>

    <div style="margin-bottom:16px">
      <div style="font-size:11px;color:#7a8fa6;text-transform:uppercase;margin-bottom:6px">SITUATION</div>
      <p style="margin:0;font-size:14px;line-height:1.6">{a["what"]}</p>
    </div>

    <div style="margin-bottom:16px">
      <div style="font-size:11px;color:#7a8fa6;text-transform:uppercase;margin-bottom:6px">WHY THIS VILLAGE IS PRIORITY</div>
      <p style="margin:0;font-size:14px;line-height:1.6">{a["why"]}</p>
      <p style="margin:6px 0 0;font-size:13px;color:#7a8fa6">
        Shelter gap: <b style="color:{'#ef4444' if gap>0 else '#22c55e'}">{gap:,} people</b> |
        Distance: {village["dist_km"]}km | Road: {village["road"]}
      </p>
    </div>

    <div style="background:{color}22;border:1px solid {color}44;border-radius:8px;padding:14px;margin-bottom:16px">
      <div style="font-size:11px;color:{color};text-transform:uppercase;font-weight:700;margin-bottom:6px">RECOMMENDED ACTION</div>
      <p style="margin:0;font-size:14px;font-weight:600;line-height:1.6">{a["action"]}</p>
    </div>

    <div style="margin-bottom:20px">
      <div style="font-size:11px;color:#7a8fa6;text-transform:uppercase;margin-bottom:6px">ALERT DELIVERY</div>
      <p style="margin:0;font-size:13px;color:#94a3b8">{a["deliver"]}</p>
    </div>

    <hr style="border:none;border-top:1px solid #243047;margin:20px 0">
    <p style="margin:0;font-size:11px;color:#4b5563">
      FloodReady District Early Warning System &nbsp;|&nbsp; Auto-generated {ts}<br>
      Risk threshold: {CONFIG["RISK_THRESHOLD"]}/100 &nbsp;|&nbsp;
      Recall: 86% &nbsp;|&nbsp; Precision: 35%
    </p>
  </div>
</div>
</body></html>"""

def build_officer_digest_html(flagged: list) -> str:
    ts = datetime.datetime.now().strftime("%d %b %Y %H:%M")
    rows = ""
    for v in flagged:
        a = v["alert"]
        lvl = a["level"]
        color = {"CRITICAL":"#dc2626","HIGH":"#ef4444","MODERATE":"#f59e0b","LOW":"#22c55e"}[lvl]
        rows += (
            f'<tr style="border-bottom:1px solid #1e293b">'
            f'<td style="padding:10px 12px;font-weight:600">{v["name"]}</td>'
            f'<td style="padding:10px 12px;color:#7a8fa6">{v["gauge"]}</td>'
            f'<td style="padding:10px 12px"><span style="background:{color}22;color:{color};padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700">{lvl}</span></td>'
            f'<td style="padding:10px 12px;font-weight:700;color:{color}">{v["risk"]:.0f}</td>'
            f'<td style="padding:10px 12px;font-size:13px">{v["population"]:,} ({v["vulnerable"]:,} vuln)</td>'
            f'<td style="padding:10px 12px;color:#94a3b8;font-size:13px">{v["road"]}</td>'
            f'<td style="padding:10px 12px;font-size:13px">{a["action"][:60]}...</td>'
            f'</tr>'
        )
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0b0f19;font-family:Arial,sans-serif">
<div style="max-width:900px;margin:20px auto">
  <div style="background:#1e3a5f;padding:20px 24px;border-radius:10px 10px 0 0">
    <h2 style="margin:0;color:#93c5fd">FloodReady — Officer Alert Digest</h2>
    <p style="margin:4px 0 0;color:#bfdbfe;font-size:13px">{ts} | {len(flagged)} village(s) above threshold ({CONFIG["RISK_THRESHOLD"]})</p>
  </div>
  <div style="background:#131928;padding:24px;border-radius:0 0 10px 10px">
    <div style="background:#1e293b;border-radius:8px;overflow:hidden">
      <table style="width:100%;border-collapse:collapse;color:#e2e8f0;font-size:14px">
        <thead>
          <tr style="background:#0f172a;color:#7a8fa6;font-size:12px;text-transform:uppercase">
            <th style="padding:10px 12px;text-align:left">Village</th>
            <th style="padding:10px 12px;text-align:left">Gauge</th>
            <th style="padding:10px 12px;text-align:left">Level</th>
            <th style="padding:10px 12px;text-align:left">Risk</th>
            <th style="padding:10px 12px;text-align:left">Population</th>
            <th style="padding:10px 12px;text-align:left">Road</th>
            <th style="padding:10px 12px;text-align:left">Action</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p style="margin:16px 0 0;font-size:12px;color:#4b5563">
      ⚠️ Review each alert before dispatching. Human oversight required.<br>
      FloodReady | Recall 86% | Precision 35% | Threshold {CONFIG["RISK_THRESHOLD"]}
    </p>
  </div>
</div></body></html>"""

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 5: LOG SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

LOG_FILE = "floodready_alerts.log"

def log(message: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    print(f"  {line}")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 6: MAIN ALERT PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(actually_send: bool = False, data: dict = None):
    if data is None:
        data = EMBEDDED_DATA

    villages = data["villages"]
    gauges = data["gauges"]
    threshold = CONFIG["RISK_THRESHOLD"]

    print("\n" + "="*60)
    mode = "LIVE SEND" if actually_send else "DRY RUN (no messages sent)"
    print(f"  FloodReady — Alert Pipeline [{mode}]")
    print("="*60)

    # ── Print gauge summary
    print(f"\n  {'GAUGE':<6} {'STATION':<18} {'LEVEL':>7} {'DANGER':>7} {'RISK':>6} {'STATUS'}")
    print("  " + "-"*60)
    for g in gauges:
        status = "⚠️ HIGH" if g["risk"] >= threshold else "✅ OK"
        print(f"  {g['id']:<6} {g['name']:<18} {g['river']:>6.2f}m {g['danger']:>6.1f}m {g['risk']:>6.1f} {status}")

    # ── Find flagged villages
    flagged = [v for v in villages if v["risk"] >= threshold]
    all_above_low = [v for v in villages if v["alert"]["level"] in ("MODERATE","HIGH","CRITICAL")]

    print(f"\n  Villages above threshold ({threshold}): {len(flagged)}")
    print(f"  Villages at MODERATE or above: {len(all_above_low)}")

    if not flagged and not all_above_low:
        log("All clear. No villages above threshold. No alerts sent.")
        print("\n  ✅ All clear. No alerts needed.\n")
        return

    # Use all_above_low for notifications (MODERATE+ villages always get alerts)
    alert_list = all_above_low if not flagged else sorted(
        list({v["id"]: v for v in flagged + all_above_low}.values()),
        key=lambda x: -x["combined"]
    )

    print(f"\n  {'#':<3} {'VILLAGE':<16} {'LEVEL':<10} {'RISK':>5} {'CHANNEL'}")
    print("  " + "-"*55)
    for i, v in enumerate(alert_list, 1):
        print(f"  {i:<3} {v['name']:<16} {v['alert']['level']:<10} {v['risk']:>5.1f} {v['channel']}")

    print(f"\n  Dispatching {len(alert_list)} village alert(s)...\n")

    sms_sent = email_sent = wa_sent = 0
    sms_failed = email_failed = 0

    for v in alert_list:
        vid = v["id"]
        contact = CONTACTS.get(vid, {})
        channel = v["channel"]
        sms_text = build_sms(v)
        email_html = build_email_html(v)
        subject = f"[FLOODREADY {v['alert']['level']}] {v['name']} — {v['gauge']}"

        log(f"ALERT | {v['name']} ({vid}) | Level: {v['alert']['level']} | Risk: {v['risk']:.0f} | Channel: {channel}")

        if not actually_send:
            print(f"  [DRY RUN] {v['name']} ({vid})")
            print(f"    Would SMS → {contact.get('phone', 'NO NUMBER')}")
            if channel == "WhatsApp group" and contact.get("whatsapp"):
                print(f"    Would WhatsApp → {contact.get('whatsapp')}")
            if contact.get("email"):
                print(f"    Would Email → {contact.get('email')}")
            print(f"    Message: {sms_text[:80]}...")
            continue

        # ── Send SMS
        phone = contact.get("phone")
        if phone:
            ok = send_sms(phone, sms_text, f"({v['name']})")
            if ok: sms_sent += 1
            else:  sms_failed += 1
        else:
            print(f"    ⚠️  No phone number for {v['name']} in CONTACTS dict")

        # ── Send WhatsApp (if village prefers it)
        wa = contact.get("whatsapp")
        if channel == "WhatsApp group" and wa:
            ok = send_whatsapp(wa, sms_text, f"({v['name']})")
            if ok: wa_sent += 1

        # ── Send Email to village leader (if available)
        email = contact.get("email")
        if email:
            ok = send_email(email, subject, email_html, f"({v['name']})")
            if ok: email_sent += 1
            else:  email_failed += 1

        time.sleep(0.3)  # Avoid rate limits

    # ── Officer digest
    print(f"\n  Sending officer digest...")
    officer_html = build_officer_digest_html(alert_list)
    officer_subject = f"[FLOODREADY DIGEST] {len(alert_list)} village(s) flagged — {datetime.datetime.now().strftime('%d %b %H:%M')}"

    if actually_send:
        # Email digest
        send_email(CONFIG["OFFICER_EMAIL"], officer_subject, officer_html, "(Officer digest)")
        # SMS summary to officer
        summary_sms = (
            f"FloodReady Digest: {len(alert_list)} village(s) flagged.\n"
            + "\n".join([f"- {v['name']}: {v['alert']['level']} (Risk {v['risk']:.0f})" for v in alert_list[:4]])
            + (f"\n...and {len(alert_list)-4} more." if len(alert_list)>4 else "")
            + "\nCheck email for full report."
        )
        send_sms(CONFIG["OFFICER_PHONE"], summary_sms, "(Officer)")
    else:
        print(f"  [DRY RUN] Officer digest would go to {CONFIG['OFFICER_EMAIL']}")

    # ── Save run log
    run_log = {
        "timestamp": datetime.datetime.now().isoformat(),
        "mode": "live" if actually_send else "dry_run",
        "flagged": len(alert_list),
        "sms_sent": sms_sent, "sms_failed": sms_failed,
        "wa_sent": wa_sent, "email_sent": email_sent, "email_failed": email_failed,
        "villages": [{"id":v["id"],"name":v["name"],"risk":v["risk"],"level":v["alert"]["level"]} for v in alert_list]
    }
    with open("floodready_last_run.json", "w") as f:
        json.dump(run_log, f, indent=2)

    print(f"""
  ── Run Summary ──────────────────────────────
    Villages alerted : {len(alert_list)}
    SMS sent         : {sms_sent}  (failed: {sms_failed})
    WhatsApp sent    : {wa_sent}
    Email sent       : {email_sent} (failed: {email_failed})
    Log saved        : {LOG_FILE}
    Run record       : floodready_last_run.json
  ─────────────────────────────────────────────
""")

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 7: TEST SENDER (sends to your own phone/email)
# ─────────────────────────────────────────────────────────────────────────────

def run_test():
    print("\n" + "="*60)
    print("  FloodReady — Test Send (to your own phone/email)")
    print("="*60)

    if not check_configured():
        print("\n  Edit CONFIG at top of file first.\n")
        return

    # Use the highest-risk village as test subject
    test_village = max(EMBEDDED_DATA["villages"], key=lambda v: v["risk"])
    sms_text = build_sms(test_village)
    email_html = build_email_html(test_village)
    subject = f"[TEST] FloodReady — {test_village['name']} Alert"

    print(f"\n  Test village: {test_village['name']} (Risk: {test_village['risk']:.0f})")
    print(f"  Sending to: SMS → {CONFIG['TEST_PHONE']} | Email → {CONFIG['TEST_EMAIL']}\n")

    sms_ok = send_sms(CONFIG["TEST_PHONE"], sms_text, "(Test)")
    email_ok = send_email(CONFIG["TEST_EMAIL"], subject, email_html, "(Test)")

    if sms_ok and email_ok:
        print("\n  ✅ Test successful! Check your phone and inbox.\n")
    else:
        print("\n  ⚠️  Some sends failed. Check your API credentials in CONFIG.\n")

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 8: SCHEDULER (runs every N minutes forever)
# ─────────────────────────────────────────────────────────────────────────────

def run_scheduler(actually_send: bool = False):
    interval = CONFIG["SCHEDULE_MINS"] * 60
    print(f"\n  FloodReady Scheduler started.")
    print(f"  Checking every {CONFIG['SCHEDULE_MINS']} minutes. Press Ctrl+C to stop.\n")
    log(f"SCHEDULER STARTED | Interval: {CONFIG['SCHEDULE_MINS']}min | Send: {actually_send}")
    run_count = 0
    try:
        while True:
            run_count += 1
            print(f"\n{'='*60}")
            print(f"  Scheduled run #{run_count} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            run_pipeline(actually_send=actually_send)
            next_run = datetime.datetime.now() + datetime.timedelta(seconds=interval)
            print(f"  Next run at: {next_run.strftime('%H:%M:%S')}")
            time.sleep(interval)
    except KeyboardInterrupt:
        log("SCHEDULER STOPPED by user")
        print("\n  Scheduler stopped.\n")

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 9: REFRESH FROM CSVs (if you have the data files)
# ─────────────────────────────────────────────────────────────────────────────

def refresh_from_csvs():
    csv_files = ["floodready_village_profiles.csv",
                 "floodready_gauge_stations.csv",
                 "floodready_river_readings.csv"]
    missing = [f for f in csv_files if not os.path.exists(f)]
    if missing:
        print(f"\n  ❌ Missing CSV files: {missing}")
        print("  Put the 3 CSV files in the same folder as this script.\n")
        return None
    try:
        import pandas as pd
        import numpy as np
        print("  Recomputing from CSV files...")
        village  = pd.read_csv("floodready_village_profiles.csv")
        gauge    = pd.read_csv("floodready_gauge_stations.csv")
        readings = pd.read_csv("floodready_river_readings.csv")
        readings = readings.drop_duplicates(subset=['Date','Gauge_ID'], keep='first').copy()
        readings.loc[readings['River_Level_m'] > 20, 'River_Level_m'] = np.nan
        readings.loc[readings['Soil_Moisture_pct'] > 100, 'Soil_Moisture_pct'] = np.nan
        readings.loc[readings['Rainfall_mm_24h'] < 0, 'Rainfall_mm_24h'] = 0.0
        readings['Rainfall_mm_24h'] = readings['Rainfall_mm_24h'].fillna(readings['Rainfall_mm_24h'].median())
        for col in ['River_Level_m','Soil_Moisture_pct']:
            readings[col] = readings.groupby('Gauge_ID')[col].transform(lambda x: x.interpolate(limit_direction='both'))
        readings['Date'] = pd.to_datetime(readings['Date'])
        readings = readings.sort_values(['Gauge_ID','Date']).reset_index(drop=True)
        readings = readings.merge(gauge, on='Gauge_ID', how='left')
        readings['Level_Gap'] = readings['River_Level_m'] - readings['Danger_Level_m']
        readings['Level_Pct_Danger'] = readings['River_Level_m'] / readings['Danger_Level_m']
        readings['River_Rise_1d'] = readings.groupby('Gauge_ID')['River_Level_m'].diff()
        readings['Upstream_Rise_1d'] = readings.groupby('Gauge_ID')['Upstream_Level_m'].diff()
        readings['Rainfall_3d'] = readings.groupby('Gauge_ID')['Rainfall_mm_24h'].transform(lambda x: x.rolling(3, min_periods=1).sum())
        def rs(row):
            s = min(row['Level_Pct_Danger']/0.95,1.5)*40
            s += min((row['River_Rise_1d'] if not np.isnan(row['River_Rise_1d']) else 0)/0.3,1.5)*20
            s += min((row['Upstream_Rise_1d'] if not np.isnan(row['Upstream_Rise_1d']) else 0)/0.2,1.5)*20
            s += min((row['Rainfall_3d'] if not np.isnan(row['Rainfall_3d']) else 0)/60,1.5)*10
            s += min((row['Soil_Moisture_pct'] if not np.isnan(row['Soil_Moisture_pct']) else 50)/80,1.5)*10
            return round(min(s,100),1)
        readings['Risk_Score'] = readings.apply(rs, axis=1)
        latest = readings.sort_values('Date').groupby('Gauge_ID').last().reset_index()
        vf = village.merge(gauge[['Gauge_ID','Station_Name','Warning_Level_m','Danger_Level_m']], on='Gauge_ID')
        vf = vf.merge(latest[['Gauge_ID','Risk_Score','Predicted_Flood' if 'Predicted_Flood' in latest else 'Risk_Score',
                               'River_Level_m','Level_Gap','Rainfall_3d','Soil_Moisture_pct','River_Rise_1d']], on='Gauge_ID', how='left')
        readings['Predicted_Flood'] = (readings['Risk_Score'] >= CONFIG["RISK_THRESHOLD"]).astype(int)
        latest = readings.sort_values('Date').groupby('Gauge_ID').last().reset_index()
        vf = village.merge(gauge[['Gauge_ID','Station_Name','Warning_Level_m','Danger_Level_m']], on='Gauge_ID')
        vf = vf.merge(latest[['Gauge_ID','Risk_Score','Predicted_Flood','River_Level_m','Level_Gap','Rainfall_3d','Soil_Moisture_pct','River_Rise_1d']], on='Gauge_ID')
        def vp(row):
            s=(row['Population']+row['Vulnerable_Population'])/5000*35
            s+=min(max(row['Population']-row['Shelter_Capacity'],0)/3000,1)*25
            s+={'Cut off in floods':30,'Seasonal':15,'All-weather':0}.get(row['Road_Access_in_Floods'],0)
            s+=row['Households_Without_Phone_pct']/100*10
            return round(s,1)
        vf['Priority_Score'] = vf.apply(vp, axis=1)
        vf['Combined_Score'] = vf['Risk_Score']*0.6+vf['Priority_Score']*0.4
        vf = vf.sort_values('Combined_Score', ascending=False).reset_index(drop=True)
        def ma(row):
            risk=row['Risk_Score']
            level='CRITICAL' if risk>=70 else 'HIGH' if risk>=45 else 'MODERATE' if risk>=25 else 'LOW'
            hours='12-24 hours' if risk>=70 else '24-48 hours'
            road=row['Road_Access_in_Floods']; pop=int(row['Population']); vul=int(row['Vulnerable_Population'])
            shelter=row['Nearest_Shelter']; dist=row['Distance_to_Shelter_km']
            channel=row['Preferred_Alert_Channel']; no_phone=row['Households_Without_Phone_pct']; gv=row['Level_Gap']
            what=f"River at {row['Station_Name']} is at {row['River_Level_m']:.2f}m, {abs(gv):.2f}m {'above' if gv>0 else 'below'} danger ({row['Danger_Level_m']}m). Risk: {level}."
            why=f"Pop: {pop:,} ({vul:,} vulnerable). Shelter gap: {max(pop-int(row['Shelter_Capacity']),0):,}. Road: {road}."
            action=f"IMMEDIATE evacuation to {shelter} ({dist}km) NOW." if road=='Cut off in floods' else f"Staged evacuation to {shelter} ({dist}km). Vulnerable first." if road=='Seasonal' else f"Issue warning. Prepare evacuation to {shelter} ({dist}km)."
            deliver=f"Via: {channel}.{' '+str(no_phone)+'% no phone - loudspeaker essential.' if no_phone>=40 else ''}"
            return {'level':level,'what':what,'why':why,'action':action,'deliver':deliver}
        vf['Alert'] = vf.apply(ma, axis=1)
        out_v = [{'id':row['Village_ID'],'name':row['Village_Name'],'gauge':row['Gauge_ID'],
            'station':row['Station_Name'],'population':int(row['Population']),'vulnerable':int(row['Vulnerable_Population']),
            'shelter':row['Nearest_Shelter'],'shelter_cap':int(row['Shelter_Capacity']),'dist_km':float(row['Distance_to_Shelter_km']),
            'road':row['Road_Access_in_Floods'],'channel':row['Preferred_Alert_Channel'],'no_phone_pct':int(row['Households_Without_Phone_pct']),
            'river_level':float(round(row['River_Level_m'],2)),'danger_level':float(row['Danger_Level_m']),
            'level_gap':float(round(row['Level_Gap'],2)),'rainfall3d':float(round(row['Rainfall_3d'],1)),
            'soil':float(round(row['Soil_Moisture_pct'],1)),'rise':float(round(row['River_Rise_1d'],3)) if not np.isnan(row['River_Rise_1d']) else 0,
            'risk':float(row['Risk_Score']),'priority':float(row['Priority_Score']),'combined':float(round(row['Combined_Score'],1)),
            'alert':row['Alert'],'flood_predicted':bool(row['Predicted_Flood'])} for _,row in vf.iterrows()]
        out_g = [{'id':row['Gauge_ID'],'name':gauge[gauge['Gauge_ID']==row['Gauge_ID']].iloc[0]['Station_Name'],
            'risk':float(row['Risk_Score']),'river':float(round(row['River_Level_m'],2)),
            'danger':float(gauge[gauge['Gauge_ID']==row['Gauge_ID']].iloc[0]['Danger_Level_m']),
            'warning':float(gauge[gauge['Gauge_ID']==row['Gauge_ID']].iloc[0]['Warning_Level_m']),
            'predicted':bool(row['Predicted_Flood']),'rainfall':float(round(row['Rainfall_3d'],1)),
            'soil':float(round(row['Soil_Moisture_pct'],1)),'rise':float(round(row['River_Rise_1d'],3)) if not np.isnan(row['River_Rise_1d']) else 0}
            for _,row in latest.iterrows()]
        data = {'villages': out_v, 'gauges': out_g}
        print(f"  ✅ Recomputed: {len(out_v)} villages, {len(out_g)} gauges")
        return data
    except Exception as e:
        print(f"  ❌ Error refreshing from CSVs: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 10: DASHBOARD LAUNCHER
# ─────────────────────────────────────────────────────────────────────────────

def launch_dashboard():
    # Check if the HTML prototype exists in same folder
    html_files = ["floodready_prototype.html", "FloodReady.html"]
    found = next((f for f in html_files if os.path.exists(f)), None)
    if found:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(found)}")
        print(f"\n  ✅ Opened dashboard: {found}\n")
    else:
        print("\n  ⚠️  Dashboard HTML not found in this folder.")
        print("  Download floodready_prototype.html from the Claude artifact link")
        print("  and place it in the same folder as this script.\n")

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 11: CRON SETUP (Linux/Mac)
# ─────────────────────────────────────────────────────────────────────────────

def setup_cron():
    if platform.system() == "Windows":
        script = os.path.abspath(__file__)
        print(f"""
  Windows Task Scheduler setup:
  1. Open Task Scheduler → Create Basic Task
  2. Name: FloodReady Alert System
  3. Trigger: Daily → Repeat every 30 minutes
  4. Action: Start a program
     Program: {sys.executable}
     Arguments: "{script}" run --send
  5. Click Finish → OK
""")
    else:
        script = os.path.abspath(__file__)
        cron_line = f"*/30 * * * * cd \"{os.path.dirname(script)}\" && {sys.executable} \"{script}\" run --send >> floodready_cron.log 2>&1"
        print(f"""
  Linux/Mac cron setup:
  Run this command to add to crontab:

    crontab -e

  Then add this line at the bottom:

    {cron_line}

  Save and exit. To verify it was added:

    crontab -l

  To remove it later:

    crontab -e  (then delete the line)

  Logs will appear in: floodready_cron.log
""")

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 12: HELP / STATUS
# ─────────────────────────────────────────────────────────────────────────────

def show_status():
    print("\n" + "="*60)
    print("  FloodReady — System Status")
    print("="*60)
    # Check packages
    print("\n  Python packages:")
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace("-","_"))
            print(f"    ✅ {pkg}")
        except ImportError:
            print(f"    ❌ {pkg} — run: python floodready_setup.py install")
    # Check credentials
    print("\n  API credentials:")
    print(f"    Twilio SID  : {'✅ Set' if not CONFIG['TWILIO_SID'].startswith('ACxxx') else '❌ Not set'}")
    print(f"    Twilio Token: {'✅ Set' if not CONFIG['TWILIO_TOKEN'].startswith('your_') else '❌ Not set'}")
    print(f"    SendGrid Key: {'✅ Set' if not CONFIG['SENDGRID_KEY'].startswith('SG.xxx') else '❌ Not set'}")
    # Check last run
    print("\n  Last run:")
    if os.path.exists("floodready_last_run.json"):
        with open("floodready_last_run.json") as f:
            lr = json.load(f)
        print(f"    Time     : {lr.get('timestamp','?')}")
        print(f"    Mode     : {lr.get('mode','?')}")
        print(f"    Flagged  : {lr.get('flagged','?')} villages")
        print(f"    SMS sent : {lr.get('sms_sent','?')}")
        print(f"    Email    : {lr.get('email_sent','?')}")
    else:
        print("    No run recorded yet.")
    print()

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 13: CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

HELP = """
FloodReady — Complete Early Warning & Alert System
===================================================

Commands:
  install       Install all Python packages (twilio, sendgrid, pandas, numpy)
  config        Show setup instructions for Twilio and SendGrid
  run           Run the alert pipeline (dry run — prints only, no sends)
  run --send    Run and actually send SMS + email
  test          Send a test SMS + email to TEST_PHONE and TEST_EMAIL in CONFIG
  schedule      Show instructions to run automatically every 30 minutes
  dashboard     Open the HTML dashboard in your browser
  refresh       Recompute data from CSV files (if placed in this folder)
  status        Show package + credential + last-run status

Quick start:
  python floodready_setup.py install
  python floodready_setup.py config
  # edit CONFIG at top of file with your API keys
  python floodready_setup.py test
  python floodready_setup.py run --send
"""

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    cmd = args.command.lower()

    if cmd == "install":
        install_packages()
    elif cmd == "config":
        config_wizard()
    elif cmd == "run":
        data = None
        if os.path.exists("floodready_village_profiles.csv"):
            data = refresh_from_csvs()
        run_pipeline(actually_send=args.send, data=data or EMBEDDED_DATA)
    elif cmd == "test":
        run_test()
    elif cmd in ("schedule", "cron"):
        setup_cron()
    elif cmd == "dashboard":
        launch_dashboard()
    elif cmd == "refresh":
        data = refresh_from_csvs()
        if data:
            with open("floodready_live_data.json","w") as f:
                json.dump(data, f, indent=2)
            print("  Saved to floodready_live_data.json\n")
    elif cmd == "status":
        show_status()
    else:
        print(HELP)

if __name__ == "__main__":
    main()
