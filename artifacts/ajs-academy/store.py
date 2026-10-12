"""Private, single-family persistence. All mutations are serialized in PostgreSQL."""
import copy
import hmac
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import psycopg
from psycopg.types.json import Jsonb
from google.auth import identity_pool
from google.cloud import storage

TZ = ZoneInfo("America/New_York")

def now():
    return datetime.now(TZ)

def today():
    return now().date().isoformat()

TASKS = [
    ("wake", "Wake up", "Morning", "home"),
    ("brush", "Brush my teeth on time", "Morning", "brush"),
    ("dress", "Get dressed and put on shoes", "Morning", "dress"),
    ("water", "Fill my water bottle", "Morning", "water"),
    ("shoes", "Put my shoes away", "After school", "shoes"),
    ("clothes", "Put my clothes in their place", "After school", "clothes"),
    ("dinner", "Have my dinner", "Evening", "dinner"),
    ("plates", "Put my dishes away", "Evening", "plates"),
    ("shower", "Take a shower with one reminder", "Evening", "shower"),
    ("dishwasher", "Help unload the dishwasher", "Extra kindness", "chores"),
    ("laundry", "Help put laundry away", "Extra kindness", "clothes"),
]

DEFAULT = {
    "settings": {"task_points": {t[0]: 0 for t in TASKS}, "points_enabled": True,
                 "conversion": 10, "conversion_confirmed": False, "ai_points": 0,
                 "transcription": False, "arcade_until": "", "arcade_override": False,
                 "residency": "Florida", "college_years": 11, "goal": 500000,
                 "inflation": 2.5, "college_inflation": 4.0,
                  "social_ai_enabled": False, "social_audio_enabled": False,
                  "social_help_phrase": "Help me, AJ, help Connor.",
                  "social_supports": [
                      {"id": "quiet-pause", "icon": "🌿", "label": "A quiet moment",
                       "kid_request": "Could I have a quiet moment, please?",
                       "adult_request": "Please help AJ find a quiet moment."},
                      {"id": "more-time", "icon": "⏳", "label": "A little more time",
                       "kid_request": "Could I have a little more time?",
                       "adult_request": "Please give AJ a little more time."},
                      {"id": "help-understanding", "icon": "💬", "label": "Help with the words",
                       "kid_request": "Could you explain that another way?",
                       "adult_request": "Please explain that another way for AJ."},
                      {"id": "trusted-adult", "icon": "🤝", "label": "Talk with someone I trust",
                       "kid_request": "Could I talk with a grown-up I trust?",
                       "adult_request": "Please help AJ talk with a grown-up he trusts."},
                  ],
                  "social_trusted_adults": ["My parent", "My teacher", "My coach"],
                 "opening_complete": False, "custody_balance": None, "custody_asof": "",
                 "school_costs": {}, "favorite_school": "Stanford"},
    "ledger": [], "completions": {}, "diary": [], "practice": [], "wishes": [],
    "rewards": [], "requests": [], "stories": [], "finance": {}, "approved_videos": [],
    "social_interests": [], "social_phrases": [], "social_scenarios": [],
}

def upgrade_state(state):
    """Backfill defaults into an existing family document without replacing saved data."""
    if not isinstance(state, dict):
        raise ValueError("Saved Academy family records must be a JSON object.")

    def merge(saved, defaults, path):
        upgraded = copy.deepcopy(saved)
        for key, default in defaults.items():
            if key not in saved:
                upgraded[key] = copy.deepcopy(default)
            elif isinstance(default, dict):
                value = saved[key]
                if not isinstance(value, dict):
                    raise ValueError(f"Saved Academy records have an invalid {path}.{key} section.")
                upgraded[key] = merge(value, default, f"{path}.{key}")
            elif isinstance(default, list) and not isinstance(saved[key], list):
                raise ValueError(f"Saved Academy records have an invalid {path}.{key} collection.")
        return upgraded

    return merge(state, DEFAULT, "state")

def connection():
    return psycopg.connect(os.environ["DATABASE_URL"])

def load():
    with connection() as c:
        row = c.execute("SELECT data FROM academy_state WHERE id=1 FOR UPDATE").fetchone()
        if not row:
            return copy.deepcopy(DEFAULT)
        saved = row[0]
        state = upgrade_state(saved)
        if state != saved:
            c.execute("UPDATE academy_state SET data=%s WHERE id=1", (Jsonb(state),))
    return state

def change(fn):
    with connection() as c:
        c.execute("INSERT INTO academy_state(id,data) VALUES(1,%s) ON CONFLICT DO NOTHING", (Jsonb(DEFAULT),))
        s = upgrade_state(c.execute("SELECT data FROM academy_state WHERE id=1 FOR UPDATE").fetchone()[0])
        result = fn(s)
        c.execute("UPDATE academy_state SET data=%s WHERE id=1", (Jsonb(s),))
    return result

def balance(s):
    return sum(x["points"] for x in s["ledger"])

def award(s, key, points, label):
    if any(x["key"] == key for x in s["ledger"]):
        return False
    s["ledger"].append({"key": key, "points": int(points), "label": label, "date": today()})
    return True

def complete_task(task_id):
    def update(s):
        key = f"task:{today()}:{task_id}"
        if key in s["completions"]:
            return False
        s["completions"][key] = today()
        points = s["settings"]["task_points"].get(task_id, 0) if s["settings"]["points_enabled"] else 0
        award(s, key, points, next(t[1] for t in TASKS if t[0] == task_id))
        return True
    return change(update)

def authenticate(role, supplied):
    """Single-family prototype gate, with persistent global role lockout."""
    if role != "parent":
        return False, "Only parent access uses password authentication."
    expected = os.environ.get("PARENT_PASSWORD", "")
    with connection() as c:
        c.execute("INSERT INTO academy_auth_attempts(key) VALUES(%s) ON CONFLICT DO NOTHING", (role,))
        failures, blocked = c.execute("SELECT failures,blocked_until FROM academy_auth_attempts WHERE key=%s FOR UPDATE", (role,)).fetchone()
        if blocked and blocked > now():
            return False, "Too many attempts. Please wait 5 minutes."
        if expected and hmac.compare_digest(supplied.encode(), expected.encode()):
            c.execute("UPDATE academy_auth_attempts SET failures=0,blocked_until=NULL WHERE key=%s", (role,))
            return True, ""
        count = (failures if not blocked or blocked > now() else 0) + 1
        c.execute("UPDATE academy_auth_attempts SET failures=%s,blocked_until=%s WHERE key=%s",
                  (count, now() + timedelta(minutes=5) if count >= 5 else None, role))
        return False, "That password did not match."

def storage_client():
    creds = identity_pool.Credentials.from_info({
        "type": "external_account", "audience": "replit", "subject_token_type": "access_token",
        "token_url": "http://127.0.0.1:1106/token",
        "credential_source": {"url": "http://127.0.0.1:1106/credential",
                              "format": {"type": "json", "subject_token_field_name": "access_token"}},
    })
    return storage.Client(project="replit", credentials=creds)

def upload(data, mime, name):
    if len(data) > 40 * 1024 * 1024:
        raise ValueError("Please choose a file smaller than 40 MB.")
    root = os.environ["PRIVATE_OBJECT_DIR"].strip("/")
    bucket, folder = root.split("/", 1)
    path = f"{folder}/academy/{uuid.uuid4().hex}"
    blob = storage_client().bucket(bucket).blob(path)
    blob.upload_from_string(data, content_type=mime, timeout=60)
    return {"bucket": bucket, "path": path, "mime": mime, "name": name}

def download(meta):
    return storage_client().bucket(meta["bucket"]).blob(meta["path"]).download_as_bytes(timeout=60)

def approve_redemption(request_id):
    def update(s):
        r = next(x for x in s["requests"] if x["id"] == request_id)
        if r["status"] != "pending":
            return False
        if balance(s) < r["points"]:
            raise ValueError("Not enough points yet.")
        award(s, "redeem:" + r["id"], -r["points"], "Reward: " + r["title"])
        r["status"] = "approved"
        return True
    return change(update)
