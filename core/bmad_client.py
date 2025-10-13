import os, requests

BMAD_ENABLED = os.getenv("BMAD_ENABLED", "false").lower() == "true"
BMAD_URL = os.getenv("BMAD_URL", "http://127.0.0.1:5055")

def plan(intent: str, text: str, user_id: str, user_tz: str = "America/Denver"):
    if not BMAD_ENABLED:
        return None
    try:
        r = requests.post(f"{BMAD_URL}/plan", json={
            "intent": intent,
            "input": text,
            "user": {"id": user_id, "tz": user_tz}
        }, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[BMAD] planner error: {e}")
        return None