"""
PressKitLive — SQLite Database Access Layer (db.py)
Phase 1: Multi-Manager & Solo Artist Architecture
"""

import sqlite3
import os
import json
import uuid
import secrets
import hashlib
import time
import re

def _resolve_data_root():
    env_root = os.getenv("DATA_ROOT") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if env_root:
        return env_root
    if os.path.exists("/data"):
        return "/data"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

DATA_ROOT = _resolve_data_root()
DB_PATH = os.path.join(DATA_ROOT, "data", "presskit.db")
IMAGES_ROOT = os.path.join(DATA_ROOT, "images")

# Ensure required storage directories exist on disk or Railway Volume
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(IMAGES_ROOT, exist_ok=True)

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

load_env()

def save_uploaded_image(data_url, filename_prefix="upload"):
    """
    Saves a base64 Data URL (data:image/png;base64,...) as a binary file in IMAGES_ROOT.
    Returns the root-relative URL path (/assets/images/<filename>).
    """
    if not data_url or not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        return data_url

    try:
        header, encoded = data_url.split(",", 1)
        import base64
        file_bytes = base64.b64decode(encoded)

        ext = "jpg"
        if "image/png" in header:
            ext = "png"
        elif "image/webp" in header:
            ext = "webp"
        elif "image/svg+xml" in header:
            ext = "svg"
        elif "image/gif" in header:
            ext = "gif"

        filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(IMAGES_ROOT, filename)
        
        with open(filepath, "wb") as f:
            f.write(file_bytes)

        return f"/assets/images/{filename}"
    except Exception as e:
        print(f"⚠️ Error saving uploaded image: {e}")
        return data_url

# SINGLE SOURCE OF TRUTH FOR PLAN QUOTAS (Section A.2)
PLAN_QUOTAS = {
    "bireysel": 1,
    "starter": 4,
    "pro": 10,
    "enterprise": 50
}

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def slugify(name):
    """
    Sanitizes artist names into URL-safe slugs (Section B.1 XSS & Slug Fix)
    Strips special characters (<, >, ', ", etc.) and keeps only [a-z0-9-]
    """
    s = name.lower()
    for src, dst in [("ğ","g"),("ü","u"),("ş","s"),("ı","i"),("ö","o"),("ç","c")]:
        s = s.replace(src, dst)
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    return s or f"artist-{uuid.uuid4().hex[:8]}"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Managers Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS managers (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            name TEXT NOT NULL,
            agency_name TEXT,
            phone TEXT,
            plan TEXT NOT NULL DEFAULT 'starter',
            account_type TEXT NOT NULL DEFAULT 'agency',
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        """)

        # Migration: Add account_type and subscription columns to managers if missing
        cursor.execute("PRAGMA table_info(managers);")
        columns = [col[1] for col in cursor.fetchall()]
        if 'account_type' not in columns:
            cursor.execute("ALTER TABLE managers ADD COLUMN account_type TEXT NOT NULL DEFAULT 'agency';")
        if 'iyzico_subscription_ref' not in columns:
            cursor.execute("ALTER TABLE managers ADD COLUMN iyzico_subscription_ref TEXT DEFAULT NULL;")
        if 'iyzico_customer_ref' not in columns:
            cursor.execute("ALTER TABLE managers ADD COLUMN iyzico_customer_ref TEXT DEFAULT NULL;")
        if 'subscription_status' not in columns:
            cursor.execute("ALTER TABLE managers ADD COLUMN subscription_status TEXT NOT NULL DEFAULT 'none';")
        if 'is_super_admin' not in columns:
            cursor.execute("ALTER TABLE managers ADD COLUMN is_super_admin INTEGER NOT NULL DEFAULT 0;")

        # 2. Artists Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS artists (
            id TEXT PRIMARY KEY,
            manager_id TEXT NOT NULL REFERENCES managers(id),
            name TEXT NOT NULL,
            genre TEXT,
            monthly_listeners TEXT,
            avatar TEXT,
            banner TEXT,
            bio TEXT,
            short_bio TEXT,
            socials_json TEXT,
            created_at TEXT NOT NULL
        );
        """)

        # 3. Folders Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id TEXT PRIMARY KEY,
            artist_id TEXT NOT NULL REFERENCES artists(id),
            name TEXT NOT NULL,
            is_locked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)

        # 4. Photos Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id TEXT PRIMARY KEY,
            artist_id TEXT NOT NULL REFERENCES artists(id),
            folder_id TEXT NOT NULL REFERENCES folders(id),
            title TEXT NOT NULL,
            type TEXT,
            format TEXT,
            resolution TEXT,
            file_size TEXT,
            url TEXT NOT NULL,
            badge TEXT,
            created_at TEXT NOT NULL
        );
        """)

        # 5. Sessions Table (Persistent SQLite sessions surviving restarts)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            manager_id TEXT NOT NULL REFERENCES managers(id),
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            impersonated_by TEXT DEFAULT NULL,
            log_id TEXT DEFAULT NULL
        );
        """)

        # Migration: Add impersonation columns to sessions if missing (MOVED AFTER CREATE TABLE - ITEM 1 FIX)
        cursor.execute("PRAGMA table_info(sessions);")
        sess_columns = [col[1] for col in cursor.fetchall()]
        if 'impersonated_by' not in sess_columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN impersonated_by TEXT DEFAULT NULL;")
        if 'log_id' not in sess_columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN log_id TEXT DEFAULT NULL;")

        # 6. Impersonation Log Table (Section D.2)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS impersonation_log (
            id TEXT PRIMARY KEY,
            admin_id TEXT NOT NULL REFERENCES managers(id),
            target_manager_id TEXT NOT NULL REFERENCES managers(id),
            started_at TEXT NOT NULL,
            ended_at TEXT
        );
        """)

        # 7. Password Reset Tokens Table (Section B.1)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            token TEXT PRIMARY KEY,
            manager_id TEXT NOT NULL REFERENCES managers(id),
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        );
        """)

        conn.commit()
    ensure_super_admins()
    print("✅ SQLite database schema initialized at assets/data/presskit.db")

def hash_password(plain_pass, salt):
    return hashlib.pbkdf2_hmac('sha256', plain_pass.encode('utf-8'), salt.encode('utf-8'), 100000).hex()

# MANAGER CRUD
def get_manager_by_email(email):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM managers WHERE LOWER(email) = LOWER(?) AND is_active = 1", (email,)).fetchone()
        return dict(row) if row else None

def get_manager_by_email_any(email):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM managers WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
        return dict(row) if row else None

def get_manager_by_id(manager_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM managers WHERE id = ? AND is_active = 1", (manager_id,)).fetchone()
        return dict(row) if row else None

def get_manager_by_id_any(manager_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM managers WHERE id = ?", (manager_id,)).fetchone()
        return dict(row) if row else None

def toggle_manager_active_status(manager_id, is_active):
    with get_connection() as conn:
        conn.execute("UPDATE managers SET is_active = ? WHERE id = ?", (1 if is_active else 0, manager_id))
        conn.commit()
    return get_manager_by_id_any(manager_id)

def create_manager(email, password, name, agency_name="", phone="", account_type="agency"):
    salt = secrets.token_hex(16)
    pwd_hash = hash_password(password, salt)
    manager_id = f"mgr-{uuid.uuid4().hex[:12]}"
    created_at = time.strftime("%Y-%m-%d %H:%M:%S")
    plan = 'bireysel' if account_type == 'solo' else 'starter'

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO managers (id, email, password_hash, salt, name, agency_name, phone, plan, account_type, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (manager_id, email, pwd_hash, salt, name, agency_name, phone, plan, account_type, created_at))
        conn.commit()

    return get_manager_by_id(manager_id)

def update_manager_password(manager_id, new_password):
    salt = secrets.token_hex(16)
    pwd_hash = hash_password(new_password, salt)
    with get_connection() as conn:
        conn.execute("UPDATE managers SET password_hash = ?, salt = ? WHERE id = ?", (pwd_hash, salt, manager_id))
        conn.commit()
    return True

def get_manager_by_subscription_ref(subscription_ref):
    if not subscription_ref:
        return None
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM managers WHERE iyzico_subscription_ref = ? AND is_active = 1", (subscription_ref,)).fetchone()
        return dict(row) if row else None

def set_manager_subscription(manager_id, subscription_ref=None, customer_ref=None, status="active"):
    with get_connection() as conn:
        updates = []
        params = []
        if subscription_ref is not None:
            updates.append("iyzico_subscription_ref = ?")
            params.append(subscription_ref)
        if customer_ref is not None:
            updates.append("iyzico_customer_ref = ?")
            params.append(customer_ref)
        if status is not None:
            updates.append("subscription_status = ?")
            params.append(status)
        
        if updates:
            params.append(manager_id)
            sql = f"UPDATE managers SET {', '.join(updates)} WHERE id = ?"
            conn.execute(sql, tuple(params))
            conn.commit()
    return get_manager_by_id(manager_id)

def update_manager_plan(manager_id, new_plan_id):
    with get_connection() as conn:
        conn.execute("UPDATE managers SET plan = ? WHERE id = ?", (new_plan_id, manager_id))
        conn.commit()
    return get_manager_by_id(manager_id)

def ensure_super_admins():
    admin_password = os.getenv("SUPER_ADMIN_PASSWORD", "Dgru2026#PressKit!")

    admin_emails = [
        "dijitalgru@gmail.com",
        "hilalbalbayyy@gmail.com",
    ]

    for email in admin_emails:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM managers WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
            if row:
                salt = row["salt"]
                pwd_hash = hash_password(admin_password, salt)
                conn.execute(
                    "UPDATE managers SET is_super_admin = 1, password_hash = ?, salt = ? WHERE LOWER(email) = LOWER(?)",
                    (pwd_hash, salt, email)
                )
                conn.commit()
            else:
                salt = secrets.token_hex(16)
                pwd_hash = hash_password(admin_password, salt)
                manager_id = f"mgr-{uuid.uuid4().hex[:12]}"
                created_at = time.strftime("%Y-%m-%d %H:%M:%S")
                name = "Furkan Egemen Güneş" if "dijitalgru" in email else "Hilal Balbay"
                conn.execute("""
                    INSERT INTO managers (id, email, password_hash, salt, name, agency_name, phone, plan, account_type, is_super_admin, subscription_status, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, 'DijitalGru Super Admin', '', 'enterprise', 'agency', 1, 'complimentary', ?, 1)
                """, (manager_id, email, pwd_hash, salt, name, created_at))
                conn.commit()

def get_all_managers():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, email, name, agency_name, phone, plan, account_type, subscription_status, iyzico_subscription_ref, is_super_admin, created_at, is_active
            FROM managers
            ORDER BY created_at DESC
        """).fetchall()
        managers = [dict(r) for r in rows]
        for m in managers:
            artists = conn.execute("SELECT COUNT(*) FROM artists WHERE manager_id = ?", (m["id"],)).fetchone()[0]
            m["artistCount"] = artists
            m["accountType"] = m.get("account_type", "agency")
            m["subscriptionStatus"] = m.get("subscription_status", "none")
            m["isSuperAdmin"] = bool(m.get("is_super_admin"))
            m["isActive"] = bool(m.get("is_active", 1))
            m["createdAt"] = m.get("created_at", "")
        return managers

# SESSION MANAGEMENT
def create_session(manager_id, max_age_seconds=2592000, impersonated_by=None, log_id=None):
    token = secrets.token_hex(32)
    created_at = time.strftime("%Y-%m-%d %H:%M:%S")
    expires_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + max_age_seconds))

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (token, manager_id, created_at, expires_at, impersonated_by, log_id) VALUES (?, ?, ?, ?, ?, ?)",
            (token, manager_id, created_at, expires_at, impersonated_by, log_id)
        )
        conn.commit()
    return token

def log_impersonation_start(admin_id, target_manager_id):
    log_id = f"imp-{uuid.uuid4().hex[:12]}"
    started_at = time.strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO impersonation_log (id, admin_id, target_manager_id, started_at) VALUES (?, ?, ?, ?)",
            (log_id, admin_id, target_manager_id, started_at)
        )
        conn.commit()
    return log_id

def log_impersonation_end(log_id):
    if not log_id:
        return
    ended_at = time.strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute("UPDATE impersonation_log SET ended_at = ? WHERE id = ?", (ended_at, log_id))
        conn.commit()

# PASSWORD RESET TOKEN HELPERS (Section B.1)
def create_password_reset_token(manager_id, token, expires_minutes=30):
    created_at = time.strftime("%Y-%m-%d %H:%M:%S")
    expires_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + expires_minutes * 60))
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO password_reset_tokens (token, manager_id, created_at, expires_at, used) VALUES (?, ?, ?, ?, 0)",
            (token, manager_id, created_at, expires_at)
        )
        conn.commit()

def get_password_reset_token(token):
    if not token:
        return None
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM password_reset_tokens WHERE token = ?", (token,)).fetchone()
        return dict(row) if row else None

def mark_reset_token_used(token):
    with get_connection() as conn:
        conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE token = ?", (token,))
        conn.commit()

def get_session(token):
    if not token:
        return None
    with get_connection() as conn:
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        row = conn.execute("SELECT * FROM sessions WHERE token = ? AND expires_at > ?", (token, now_str)).fetchone()
        return dict(row) if row else None

def delete_session(token):
    if not token:
        return
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()

# ARTISTS CRUD
def get_artists_by_manager(manager_id):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM artists WHERE manager_id = ? ORDER BY created_at DESC", (manager_id,)).fetchall()
        artists = [dict(r) for r in rows]
        for a in artists:
            a["socials"] = json.loads(a["socials_json"]) if a.get("socials_json") else {}
            a["folders"] = get_folders_by_artist(a["id"])
            a["pressPhotos"] = get_photos_by_artist(a["id"])
            mgr = get_manager_by_id(a["manager_id"])
            if mgr:
                is_solo = (mgr.get("account_type") == "solo")
                a["manager"] = {
                    "name": mgr["name"],
                    "title": "Sanatçı / Doğrudan İletişim" if is_solo else "Resmi Menajer / Booking Agent",
                    "phone": mgr["phone"] or "",
                    "phoneRaw": (mgr["phone"] or "").replace("+", "").replace(" ", ""),
                    "email": mgr["email"],
                    "accountType": mgr.get("account_type", "agency")
                }
        return artists

def get_artist_by_id(artist_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM artists WHERE id = ?", (artist_id,)).fetchone()
        if not row:
            return None
        a = dict(row)
        a["socials"] = json.loads(a["socials_json"]) if a.get("socials_json") else {}
        a["folders"] = get_folders_by_artist(a["id"])
        a["pressPhotos"] = get_photos_by_artist(a["id"])
        mgr = get_manager_by_id(a["manager_id"])
        if mgr:
            is_solo = (mgr.get("account_type") == "solo")
            a["manager"] = {
                "name": mgr["name"],
                "title": "Sanatçı / Doğrudan İletişim" if is_solo else "Resmi Menajer / Booking Agent",
                "phone": mgr["phone"] or "",
                "phoneRaw": (mgr["phone"] or "").replace("+", "").replace(" ", ""),
                "email": mgr["email"],
                "accountType": mgr.get("account_type", "agency")
            }
        return a

def create_artist(manager_id, name, genre="Pop", monthly_listeners="3.200", avatar="", banner="", bio="", short_bio="", socials=None):
    # Sanitize and slugify artist name (Section B.1 XSS/Slug Fix)
    artist_id = slugify(name)
    if get_artist_by_id(artist_id):
        artist_id = f"{artist_id}-{uuid.uuid4().hex[:4]}"

    created_at = time.strftime("%Y-%m-%d %H:%M:%S")
    socials_json = json.dumps(socials or {})

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO artists (id, manager_id, name, genre, monthly_listeners, avatar, banner, bio, short_bio, socials_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (artist_id, manager_id, name, genre, monthly_listeners, avatar, banner, bio, short_bio, socials_json, created_at))
        
        # Create default "folder-all" folder
        conn.execute("""
            INSERT INTO folders (id, artist_id, name, is_locked, created_at)
            VALUES (?, ?, 'Tüm Görseller', 0, ?)
        """, (f"folder-all-{artist_id}", artist_id, created_at))
        
        conn.commit()

    return get_artist_by_id(artist_id)

def update_artist_info(artist_id, name=None, genre=None, avatar=None, banner=None):
    with get_connection() as conn:
        if name:
            conn.execute("UPDATE artists SET name = ? WHERE id = ?", (name, artist_id))
        if genre:
            conn.execute("UPDATE artists SET genre = ? WHERE id = ?", (genre, artist_id))
        if avatar:
            saved_avatar = save_uploaded_image(avatar, f"avatar_{artist_id}")
            conn.execute("UPDATE artists SET avatar = ? WHERE id = ?", (saved_avatar, artist_id))
        if banner:
            saved_banner = save_uploaded_image(banner, f"banner_{artist_id}")
            conn.execute("UPDATE artists SET banner = ? WHERE id = ?", (saved_banner, artist_id))
        conn.commit()
    return get_artist_by_id(artist_id)

# FOLDERS & PHOTOS CRUD
def get_folders_by_artist(artist_id):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM folders WHERE artist_id = ? ORDER BY created_at ASC", (artist_id,)).fetchall()
        folders = []
        for r in rows:
            d = dict(r)
            d["isLocked"] = bool(d["is_locked"])
            folders.append(d)
        return folders

def create_folder(artist_id, name, is_locked=False):
    folder_id = f"folder-{uuid.uuid4().hex[:8]}"
    created_at = time.strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO folders (id, artist_id, name, is_locked, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (folder_id, artist_id, name, 1 if is_locked else 0, created_at))
        conn.commit()
    return {"id": folder_id, "artist_id": artist_id, "name": name, "isLocked": is_locked}

def toggle_folder_lock(folder_id):
    with get_connection() as conn:
        row = conn.execute("SELECT is_locked FROM folders WHERE id = ?", (folder_id,)).fetchone()
        if not row:
            return False
        new_val = 0 if row["is_locked"] else 1
        conn.execute("UPDATE folders SET is_locked = ? WHERE id = ?", (new_val, folder_id))
        conn.commit()
        return bool(new_val)

def get_photos_by_artist(artist_id):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM photos WHERE artist_id = ? ORDER BY created_at DESC", (artist_id,)).fetchall()
        photos = []
        for r in rows:
            d = dict(r)
            d["folderId"] = d["folder_id"]
            d["fileSize"] = d["file_size"]
            photos.append(d)
        return photos

def create_photo(artist_id, folder_id, title, url, resolution="3808 x 5712 px (300 DPI)", badge="Yeni Görsel"):
    photo_id = f"photo-{uuid.uuid4().hex[:8]}"
    created_at = time.strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO photos (id, artist_id, folder_id, title, type, format, resolution, file_size, url, badge, created_at)
            VALUES (?, ?, ?, ?, 'Konser / Sahne', 'JPG', ?, '5.5 MB', ?, ?, ?)
        """, (photo_id, artist_id, folder_id, title, resolution, url, badge, created_at))
        conn.commit()
    return {
        "id": photo_id,
        "artistId": artist_id,
        "folderId": folder_id,
        "title": title,
        "type": "Konser / Sahne",
        "format": "JPG",
        "resolution": resolution,
        "fileSize": "5.5 MB",
        "url": url,
        "badge": badge
    }

def delete_photo(photo_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
    return True

# Initialize database schema on import
init_db()
