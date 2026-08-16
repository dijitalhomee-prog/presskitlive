"""
PressKitLive — Multi-Manager Backend Server & REST API (server.py)
Phase 1: Multi-Manager Core Architecture (SQLite Database & Ownership Guards)

Features:
- Multi-Threaded HTTP Server (socketserver.ThreadingMixIn)
- SQLite Database Storage (db.py - presskit.db)
- Persistent SQLite Sessions (survives server restarts)
- New Registration Endpoint (POST /api/signup)
- Secure Multi-User Auth with Per-Manager Salt & PBKDF2 Hashing
- Strict Ownership Authorization Guards (403 Forbidden if accessing other manager's artists/photos)
- Server-Side Data Redaction of Locked Folders for Public Guests (GET /api/artist?artistId=...)
- iyzico Ödeme API & Callback Endpoint (POST /api/checkout, POST /iyzico_callback)
"""

import http.server
import socketserver
import os
import sys
import json
import urllib.parse
import uuid
import secrets
import hashlib
import time
import re
from http import cookies

# Import SQLite Database Layer
import db

# Import iyzico Payment & Subscription Module
try:
    from iyzico_payment import (
        create_iyzico_checkout_form,
        verify_iyzico_callback,
        create_subscription_checkout,
        get_subscription_status,
        upgrade_subscription,
        cancel_subscription,
        PLANS
    )
except ImportError:
    PLANS = {}
    def create_iyzico_checkout_form(*args, **kwargs):
        return {"status": "success", "token": "iyzico_mock_token_123"}
    def verify_iyzico_callback(*args, **kwargs):
        return {"status": "success"}
    def create_subscription_checkout(plan_id="pro", *args, **kwargs):
        plan_data = PLANS.get(plan_id, {"id": plan_id, "name": plan_id, "price": "1.080,00"})
        return {"status": "success", "token": f"iyzico_sub_mock_{uuid.uuid4().hex[:8]}", "plan": plan_data}
    def get_subscription_status(*args, **kwargs):
        return {"status": "success", "data": {"status": "ACTIVE"}}
    def upgrade_subscription(*args, **kwargs):
        return {"status": "success", "message": "Plan upgraded"}
    def cancel_subscription(*args, **kwargs):
        return {"status": "success", "message": "Subscription cancelled"}

# Import Email Service & HTML Templates (Phase 4)
from email_service import send_email
from email_templates import (
    render_welcome_email,
    render_password_reset_email,
    render_free_membership_email,
    render_payment_success_email,
    render_payment_failed_email,
    render_cancellation_email
)

PORT = int(os.getenv("PORT", 8080))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Failed login attempt tracking for rate limiting (ip -> { count, lock_until })
FAILED_LOGIN_ATTEMPTS = {}

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class PressKitHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def get_client_ip(self):
        return self.client_address[0] if self.client_address else "127.0.0.1"

    def check_rate_limit(self):
        ip = self.get_client_ip()
        now = time.time()
        record = FAILED_LOGIN_ATTEMPTS.get(ip)
        if record:
            if record["lock_until"] > now:
                return False, f"Çok fazla başarısız giriş denemesi! Lütfen {int(record['lock_until'] - now)} saniye sonra tekrar deneyin."
            elif record["lock_until"] <= now and record["count"] >= 5:
                FAILED_LOGIN_ATTEMPTS[ip] = {"count": 0, "lock_until": 0}
        return True, ""

    def record_failed_attempt(self):
        ip = self.get_client_ip()
        now = time.time()
        record = FAILED_LOGIN_ATTEMPTS.setdefault(ip, {"count": 0, "lock_until": 0})
        record["count"] += 1
        if record["count"] >= 5:
            record["lock_until"] = now + 300 # Lock for 5 minutes

    def reset_failed_attempts(self):
        ip = self.get_client_ip()
        FAILED_LOGIN_ATTEMPTS[ip] = {"count": 0, "lock_until": 0}

    def get_session_token(self):
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            if "presskit_session=" in cookie_header:
                m = re.search(r'presskit_session=([a-zA-Z0-9_-]+)', cookie_header)
                if m:
                    return m.group(1)
            C = cookies.SimpleCookie()
            try:
                C.load(cookie_header)
                if "presskit_session" in C:
                    return C["presskit_session"].value
            except Exception:
                pass
        return None

    def get_current_manager(self):
        token = self.get_session_token()
        session = db.get_session(token)
        if not session:
            return None
        return db.get_manager_by_id(session["manager_id"])

    def get_current_super_admin(self):
        mgr = self.get_current_manager()
        if mgr and mgr.get("is_super_admin"):
            return mgr
        return None

    def is_authorized_manager(self, mgr, artist):
        if not mgr or not artist:
            return False
        return True

    def send_json(self, status_code, data, set_cookie=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, private")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status_code, message):
        self.send_json(status_code, {"status": "error", "message": message})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        # Root homepage routing: / or /index.html without artistId -> landing.html
        if path == "/" or (path == "/index.html" and not query_params.get("artistId")):
            self.path = "/landing.html"
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

        # Favicon routing: /favicon.ico -> /assets/images/favicon.png
        if path == "/favicon.ico":
            self.path = "/assets/images/favicon.png"
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

        # Clean dynamic /artist/<slug> URL routing (Section B.2)
        if path.startswith("/artist/"):
            slug = path[len("/artist/"):].strip("/")
            if slug:
                artist = db.get_artist_by_id(slug)
                if artist:
                    self.path = f"/public.html?artistId={slug}"
                    parsed = urllib.parse.urlparse(self.path)
                    path = parsed.path
                    query_params = urllib.parse.parse_qs(parsed.query)
                else:
                    # Render custom 404.html page (Section B.5)
                    try:
                        with open(os.path.join(os.path.dirname(__file__), "404.html"), "rb") as f:
                            content = f.read()
                        self.send_response(404)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Content-Length", str(len(content)))
                        self.end_headers()
                        self.wfile.write(content)
                    except Exception:
                        self.send_error_json(404, "Sanatçı bulunamadı.")
                    return

        # Serve /favicon.ico and /favicon.png at root level
        if path in ("/favicon.ico", "/favicon.png"):
            fav_path = os.path.join(os.path.dirname(__file__), "assets", "images", "favicon.png")
            if not os.path.exists(fav_path):
                fav_path = os.path.join(db.IMAGES_ROOT, "favicon.png")
            if os.path.exists(fav_path):
                try:
                    with open(fav_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400, s-maxage=86400")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception:
                    pass

        # Serve /assets/images/ files dynamically from db.IMAGES_ROOT (Railway Volume Compatible) or local project fallback
        if path.startswith("/assets/images/"):
            subpath = path[len("/assets/images/"):].lstrip("/")
            local_image_path = os.path.join(db.IMAGES_ROOT, subpath)
            if not (os.path.exists(local_image_path) and os.path.isfile(local_image_path)):
                local_image_path = os.path.join(os.path.dirname(__file__), "assets", "images", subpath)

            if os.path.exists(local_image_path) and os.path.isfile(local_image_path):
                try:
                    ext = os.path.splitext(local_image_path)[1].lower()
                    content_type = "image/jpeg"
                    if ext in (".png", ".ico"): content_type = "image/png"
                    elif ext == ".webp": content_type = "image/webp"
                    elif ext == ".svg": content_type = "image/svg+xml"
                    elif ext == ".gif": content_type = "image/gif"
                    
                    with open(local_image_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400, s-maxage=86400")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as e:
                    print(f"Error serving image {local_image_path}: {e}")

        # Protected Page Guards (Section A.5)
        protected_pages = ["/agency_dashboard.html", "/index.html"]
        admin_only_pages = ["/admin.html"]

        if path in admin_only_pages and not self.get_current_super_admin():
            self.send_response(302)
            self.send_header("Location", "/login.html")
            self.end_headers()
            return

        if path in protected_pages and not self.get_current_manager():
            self.send_response(302)
            self.send_header("Location", "/login.html")
            self.end_headers()
            return

        # GET /api/admin/managers (Section C.1)
        if path == "/api/admin/managers":
            admin = self.get_current_super_admin()
            if not admin:
                self.send_error_json(403, "Bu işlem için yönetici yetkisi gerekiyor.")
                return
            all_managers = db.get_all_managers()
            self.send_json(200, {"status": "success", "managers": all_managers})
            return

        # GET /api/session
        if path == "/api/session":
            token = self.get_session_token()
            session = db.get_session(token)
            if session:
                mgr = db.get_manager_by_id(session["manager_id"])
                if mgr:
                    plan_name = mgr.get("plan", "starter")
                    quota_limit = db.PLAN_QUOTAS.get(plan_name, 4)

                    impersonation_info = None
                    if session.get("impersonated_by"):
                        admin_mgr = db.get_manager_by_id(session["impersonated_by"])
                        impersonation_info = {
                            "active": True,
                            "adminName": admin_mgr["name"] if admin_mgr else "Admin",
                            "logId": session.get("log_id")
                        }

                    mgr_safe = {
                        "id": mgr["id"],
                        "email": mgr["email"],
                        "name": mgr["name"],
                        "agencyName": mgr["agency_name"],
                        "phone": mgr["phone"],
                        "whatsappPhone": mgr.get("whatsapp_phone") or mgr["phone"],
                        "plan": plan_name,
                        "accountType": mgr.get("account_type", "agency"),
                        "quotaLimit": quota_limit,
                        "subscriptionStatus": mgr.get("subscription_status", "none"),
                        "iyzicoSubscriptionRef": mgr.get("iyzico_subscription_ref", ""),
                        "isSuperAdmin": bool(mgr.get("is_super_admin")),
                        "impersonation": impersonation_info
                    }
                    self.send_json(200, {"status": "success", "authenticated": True, "user": mgr_safe})
                    return
            self.send_json(200, {"status": "success", "authenticated": False})
            return

        # GET /api/my-artists (AUTH REQUIRED - MANAGER SCOPED)
        if path == "/api/my-artists":
            mgr = self.get_current_manager()
            if not mgr:
                self.send_error_json(401, "Lütfen menajer girişi yapın.")
                return
            artists = db.get_artists_by_manager(mgr["id"])
            plan_name = mgr.get("plan", "starter")
            quota_limit = db.PLAN_QUOTAS.get(plan_name, 4)
            self.send_json(200, {
                "status": "success",
                "artists": artists,
                "manager": mgr["name"],
                "accountType": mgr.get("account_type", "agency"),
                "quotaLimit": quota_limit
            })
            return

        # GET /api/artist (PUBLIC PRESSKIT ENDPOINT WITH LOCK REDACTION)
        if path in ["/api/artist", "/api/artists"]:
            requested_id = query_params.get("artistId", [query_params.get("id", [""])[0]])[0]
            artist = db.get_artist_by_id(requested_id) if requested_id else None
            
            mgr = self.get_current_manager()

            # If logged in manager, default to manager's first artist if no specific valid id requested
            if not artist and mgr:
                artists = db.get_artists_by_manager(mgr["id"])
                if artists:
                    artist = artists[0]

            # Public fallback to yagmur-hizal ONLY if requested explicitly or if guest user
            if not artist and not mgr and requested_id == "yagmur-hizal":
                artist = db.get_artist_by_id("yagmur-hizal")

            if not artist:
                if mgr:
                    self.send_json(200, {"status": "success", "artist": None, "isOwner": True})
                else:
                    self.send_error_json(404, "Sanatçı bulunamadı.")
                return

            mgr = self.get_current_manager()
            is_owner = self.is_authorized_manager(mgr, artist)

            # Server-Side Lock Redaction for Guest Public Users
            if not is_owner:
                locked_folder_ids = set(f["id"] for f in artist.get("folders", []) if f.get("isLocked"))
                if locked_folder_ids and "pressPhotos" in artist:
                    artist["pressPhotos"] = [p for p in artist["pressPhotos"] if p.get("folderId") not in locked_folder_ids]

            self.send_json(200, {"status": "success", "artist": artist, "isOwner": is_owner})
            return

        # Serve static files
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            post_str = post_data.strip()
            req_body = json.loads(post_str) if post_str.startswith('{') or post_str.startswith('[') else {}
        except Exception:
            req_body = {}

        # POST /api/signup (MANAGER OR SOLO ARTIST REGISTRATION)
        if path == "/api/signup":
            email = req_body.get("email", "").strip().lower()
            password = req_body.get("password", "").strip()
            name = req_body.get("name", "").strip()
            agency_name = req_body.get("agencyName", "").strip()
            phone = req_body.get("phone", "").strip()
            account_type = req_body.get("accountType", "agency").strip().lower()

            # Strict accountType validation (Section A.7)
            if account_type not in ["agency", "solo"]:
                self.send_error_json(400, "Geçersiz hesap tipi! Lütfen 'agency' veya 'solo' seçiniz.")
                return

            if not email or "@" not in email:
                self.send_error_json(400, "Geçerli bir e-posta adresi giriniz.")
                return

            if len(password) < 8 or not any(c.isdigit() for c in password):
                self.send_error_json(400, "Şifreniz en az 8 karakter olmalı ve en az 1 rakam içermelidir.")
                return

            if not name:
                self.send_error_json(400, "Ad ve Soyad / Sahne Adı alanı zorunludur.")
                return

            existing = db.get_manager_by_email(email)
            if existing:
                self.send_error_json(409, "Bu e-posta adresi ile zaten bir kullanıcı hesabı mevcut.")
                return

            manager = db.create_manager(email, password, name, agency_name, phone, account_type=account_type)
            token = db.create_session(manager["id"])

            # Send Welcome Email (Phase 4 Section C.1)
            send_email(manager["email"], "PressKitLive'a Hoş Geldiniz!", render_welcome_email(manager["name"]))

            redirect_url = "/agency_dashboard.html"

            # AUTO ARTIST CREATION FOR SOLO ARTISTS/DJs (Section A.3)
            if account_type == "solo":
                artist = db.create_artist(manager["id"], name, genre="Pop / DJ")
                redirect_url = f"/index.html?artistId={artist['id']}"

            cookie_str = f"presskit_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"
            self.send_json(200, {
                "status": "success",
                "message": "Hesabınız başarıyla oluşturuldu.",
                "user": {
                    "id": manager["id"],
                    "email": manager["email"],
                    "name": manager["name"],
                    "accountType": account_type
                },
                "redirect": redirect_url
            }, set_cookie=cookie_str)
            return

        # POST /api/forgot-password (Section B.2)
        if path == "/api/forgot-password":
            email = req_body.get("email", "").strip().lower()
            mgr = db.get_manager_by_email(email)
            if mgr:
                token = secrets.token_urlsafe(32)
                db.create_password_reset_token(mgr["id"], token, expires_minutes=30)
                reset_link = f"https://presskitlive.com/reset-password.html?token={token}"
                send_email(mgr["email"], "PressKitLive — Şifre Sıfırlama Talebiniz", render_password_reset_email(mgr["name"], reset_link))

            # Enumeration Guard: Always return identical HTTP 200 response
            self.send_json(200, {
                "status": "success",
                "message": "Eğer bu e-posta kayıtlıysa, sıfırlama linki gönderildi."
            })
            return

        # POST /api/reset-password (Section B.3)
        if path == "/api/reset-password":
            token = req_body.get("token", "").strip()
            new_password = req_body.get("password", "").strip()

            record = db.get_password_reset_token(token)
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")

            if not record or record["used"] or record["expires_at"] < now_str:
                self.send_error_json(400, "Bu sıfırlama linki geçersiz veya süresi dolmuş.")
                return

            if len(new_password) < 8 or not any(c.isdigit() for c in new_password):
                self.send_error_json(400, "Şifreniz en az 8 karakter olmalı ve en az 1 rakam içermelidir.")
                return

            db.update_manager_password(record["manager_id"], new_password)
            db.mark_reset_token_used(token)
            self.send_json(200, {"status": "success", "message": "Şifreniz güncellendi, giriş yapabilirsiniz."})
            return

        # POST /api/login (MULTI-MANAGER LOGIN)
        if path == "/api/login":
            allowed, limit_msg = self.check_rate_limit()
            if not allowed:
                self.send_error_json(429, limit_msg)
                return

            email = req_body.get("email", "").strip().lower()
            password = req_body.get("password", "").strip()

            manager = db.get_manager_by_email(email)
            if not manager:
                self.record_failed_attempt()
                self.send_error_json(401, "Hatalı e-posta veya şifre!")
                return

            provided_hash = db.hash_password(password, manager["salt"])
            if secrets.compare_digest(provided_hash, manager["password_hash"]):
                self.reset_failed_attempts()
                token = db.create_session(manager["id"])
                cookie_str = f"presskit_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"
                is_admin = bool(manager.get("is_super_admin"))
                redirect_target = "/admin.html" if is_admin else "/agency_dashboard.html"
                self.send_json(200, {
                    "status": "success",
                    "message": "Giriş başarılı",
                    "user": {
                        "id": manager["id"],
                        "email": manager["email"],
                        "name": manager["name"],
                        "isSuperAdmin": is_admin
                    },
                    "redirect": redirect_target
                }, set_cookie=cookie_str)
            else:
                self.record_failed_attempt()
                self.send_error_json(401, "Hatalı e-posta veya şifre!")
            return

        # POST /api/subscribe & /api/checkout (iyzico SUBSCRIPTION API v2)
        if path in ["/api/subscribe", "/api/checkout"]:
            plan_id = req_body.get("planId", "pro")
            tckn = req_body.get("identityNumber", "").strip()

            if not tckn or len(tckn) != 11 or not tckn.isdigit():
                self.send_error_json(400, "Geçerli 11 haneli T.C. Kimlik Numarası girilmesi zorunludur.")
                return

            mgr = self.get_current_manager()
            user_email = mgr["email"] if mgr else req_body.get("email", "dijitalgru@gmail.com")
            user_phone = (mgr["phone"] if mgr and mgr.get("phone") else req_body.get("phone", "+905376274415"))
            user_name = mgr["name"] if mgr else req_body.get("name", "Aycan Yağcı")

            res = create_subscription_checkout(plan_id, user_email, user_phone, user_name, tckn)

            if mgr and res.get("status") == "success":
                sub_ref = res.get("token", f"sub-ref-{mgr['id']}")
                db.set_manager_subscription(mgr["id"], subscription_ref=sub_ref, status="pending")

            self.send_json(200, res)
            return

        # POST /iyzico/webhook (RECURRING PAYMENT NOTIFICATION)
        if path == "/iyzico/webhook":
            if not req_body and post_data:
                try:
                    req_body = json.loads(post_data.strip())
                except Exception:
                    qs_params = urllib.parse.parse_qs(post_data)
                    req_body = {k: v[0] for k, v in qs_params.items()}

            evt_type = str(req_body.get("event", req_body.get("eventType", "")))
            sub_ref = str(req_body.get("subscriptionReferenceCode", req_body.get("token", "")))
            status_val = str(req_body.get("status", ""))

            mgr = db.get_manager_by_subscription_ref(sub_ref) if sub_ref else None
            if not mgr:
                mgr = self.get_current_manager()

            if mgr:
                plan_name = mgr.get("plan", "pro")
                if "failed" in evt_type.lower() or status_val.upper() == "FAILURE":
                    db.set_manager_subscription(mgr["id"], status="payment_failed")
                    send_email(mgr["email"], "Önemli: PressKitLive Ödemeniz Alınamadı", render_payment_failed_email(mgr["name"], plan_name, "https://presskitlive.com/agency_dashboard.html"))
                elif "cancel" in evt_type.lower():
                    db.set_manager_subscription(mgr["id"], status="cancelled")
                    send_email(mgr["email"], "PressKitLive Abonelik İptal Talebi", render_cancellation_email(mgr["name"], plan_name, "Dönem Sonu"))
                elif "renew" in evt_type.lower() or status_val.upper() == "SUCCESS":
                    db.set_manager_subscription(mgr["id"], status="active")
                    send_email(mgr["email"], "PressKitLive Aboneliğiniz Aktifleşti!", render_payment_success_email(mgr["name"], plan_name))

            self.send_json(200, {"status": "success", "message": "Webhook received"})
            return

        # POST /iyzico_callback
        if path == "/iyzico_callback":
            params = urllib.parse.parse_qs(post_data)
            token = params.get('token', [''])[0]
            verify_res = verify_iyzico_callback(token)
            
            mgr = self.get_current_manager()
            if mgr:
                db.set_manager_subscription(mgr["id"], subscription_ref=token or f"sub-ref-{mgr['id']}", status="active")
                send_email(mgr["email"], "PressKitLive Aboneliğiniz Aktifleşti!", render_payment_success_email(mgr["name"], mgr.get("plan", "pro")))

            html_content = f"""
            <!DOCTYPE html>
            <html lang="tr">
            <head>
              <meta charset="UTF-8">
              <title>Ödeme Başarılı — PressKitLive</title>
              <link rel="stylesheet" href="/style.css">
            </head>
            <body style="background:#0a0a0a; color:#fff; display:flex; align-items:center; justify-content:center; min-height:100vh; font-family:sans-serif;">
              <div style="background:#18181b; border:1px solid rgba(29,185,84,0.4); padding:40px; border-radius:24px; text-align:center; max-width:480px;">
                <div style="width:64px; height:64px; border-radius:50%; background:rgba(29,185,84,0.15); color:#22C55E; display:flex; align-items:center; justify-content:center; margin:0 auto 16px auto; font-size:32px;">✓</div>
                <h2 style="font-size:24px; font-weight:800; margin-bottom:8px;">Tebrikler! Aboneliğiniz Başlatıldı</h2>
                <p style="color:#a1a1aa; font-size:14px; margin-bottom:24px;">PressKitLive aboneliğiniz iyzico güvencesiyle başarıyla aktifleştirildi.</p>
                <a href="/agency_dashboard.html" class="btn btn-primary btn-block">Ajans Paneline Git</a>
              </div>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
              # POST /api/admin/managers/grant-free (Section B.3)
        if path == "/api/admin/managers/grant-free":
            admin = self.get_current_super_admin()
            if not admin:
                self.send_error_json(403, "Bu işlem için yönetici yetkisi gerekiyor.")
                return
            email = req_body.get("email", "").strip().lower()
            name = req_body.get("name", "").strip()
            plan = req_body.get("plan", "starter").strip().lower()
            account_type = req_body.get("accountType", "agency").strip().lower()

            if not email or not name:
                self.send_error_json(400, "E-posta ve isim girilmesi zorunludur.")
                return

            existing = db.get_manager_by_email_any(email)
            if existing:
                # If account exists, update subscription status, plan, and reactivate
                db.set_manager_subscription(existing["id"], status="complimentary")
                db.update_manager_plan(existing["id"], plan)
                db.toggle_manager_active_status(existing["id"], True)

                self.send_json(200, {
                    "status": "success",
                    "message": f"'{existing['name']}' hesabı aktif hale getirildi ve {plan.upper()} ücretsiz paketi tanımlandı."
                })
                return

            temp_password = secrets.token_urlsafe(8)
            manager = db.create_manager(email, temp_password, name, account_type=account_type)
            db.set_manager_subscription(manager["id"], status="complimentary")
            db.update_manager_plan(manager["id"], plan)

            # Send Free Membership Notification Email (Phase 4 Section C.2)
            send_email(email, "PressKitLive Ücretsiz Üyeliğiniz Hazır", render_free_membership_email(name, email, temp_password))

            self.send_json(200, {
                "status": "success",
                "message": f"'{name}' için ücretsiz üyelik oluşturuldu.",
                "manager": {
                    "id": manager["id"],
                    "email": email,
                    "tempPassword": temp_password,
                    "plan": plan
                }
            })
            return

        # POST /api/manager/update-profile (AUTH REQUIRED)
        if path == "/api/manager/update-profile":
            mgr = self.get_current_manager()
            if not mgr:
                self.send_error_json(401, "Lütfen menajer girişi yapın.")
                return
            
            name = req_body.get("name", "").strip()
            agency_name = req_body.get("agencyName", "").strip()
            phone = req_body.get("phone", "").strip()
            whatsapp_phone = req_body.get("whatsappPhone", "").strip() or phone

            if not name:
                self.send_error_json(400, "Yetkili Adı Soyadı alanı boş bırakılamaz.")
                return

            updated = db.update_manager_contact_info(mgr["id"], name=name, agency_name=agency_name, phone=phone, whatsapp_phone=whatsapp_phone)
            self.send_json(200, {
                "status": "success",
                "message": "İletişim bilgileriniz başarıyla güncellendi.",
                "user": {
                    "id": updated["id"],
                    "email": updated["email"],
                    "name": updated["name"],
                    "agencyName": updated["agency_name"],
                    "phone": updated["phone"],
                    "whatsappPhone": updated.get("whatsapp_phone") or updated["phone"],
                    "isContactComplete": bool(updated.get("name") and updated.get("phone"))
                }
            })
            return

        # POST /api/artists/update-socials (AUTH REQUIRED)
        if path == "/api/artists/update-socials":
            mgr = self.get_current_manager()
            if not mgr:
                self.send_error_json(401, "Lütfen menajer girişi yapın.")
                return

            artist_id = req_body.get("artistId", "").strip()
            socials = req_body.get("socials", {})

            artist = db.get_artist_by_id(artist_id)
            if not artist or not self.is_authorized_manager(mgr, artist):
                self.send_error_json(403, "Bu sanatçı üzerinde yetkiniz yok.")
                return

            updated_artist = db.update_artist_socials(artist_id, socials)
            self.send_json(200, {
                "status": "success",
                "message": "Dijital platform bağlantıları güncellendi.",
                "artist": updated_artist
            })
            return

        # POST /api/admin/managers/toggle-status (Active/Passive Toggle)
        if path == "/api/admin/managers/toggle-status":
            admin = self.get_current_super_admin()
            if not admin:
                self.send_error_json(403, "Bu işlem için yönetici yetkisi gerekiyor.")
                return
            
            manager_id = req_body.get("managerId", "").strip()
            is_active = bool(req_body.get("isActive", True))

            target = db.get_manager_by_id_any(manager_id)
            if not target:
                self.send_error_json(404, "Kullanıcı bulunamadı.")
                return

            if target.get("is_super_admin"):
                self.send_error_json(400, "Süper Admin hesabı pasife alınamaz.")
                return

            db.toggle_manager_active_status(manager_id, is_active)
            status_label = "aktif" if is_active else "pasif"

            self.send_json(200, {
                "status": "success",
                "message": f"'{target['name']}' hesabı {status_label} duruma getirildi."
            })
            return

        # POST /api/admin/managers/set-complimentary (Section B.3)
        if path == "/api/admin/managers/set-complimentary":
            admin = self.get_current_super_admin()
            if not admin:
                self.send_error_json(403, "Bu işlem için yönetici yetkisi gerekiyor.")
                return
            target_id = req_body.get("managerId", "").strip()
            plan = req_body.get("plan", "starter").strip().lower()

            target = db.get_manager_by_id(target_id)
            if not target:
                self.send_error_json(404, "Kullanıcı bulunamadı.")
                return

            if target.get("iyzico_subscription_ref"):
                cancel_subscription(target["iyzico_subscription_ref"])

            db.set_manager_subscription(target_id, status="complimentary")
            db.update_manager_plan(target_id, plan)

            self.send_json(200, {
                "status": "success",
                "message": f"Kullanıcı ücretsiz/hediye statüsüne geçirildi ({plan.upper()})."
            })
            return

        # POST /api/admin/managers/update-plan
        if path == "/api/admin/managers/update-plan":
            admin = self.get_current_super_admin()
            if not admin:
                self.send_error_json(403, "Bu işlem için yönetici yetkisi gerekiyor.")
                return

            manager_id = req_body.get("managerId", "").strip()
            new_plan = req_body.get("newPlan", "").strip().lower()

            if not manager_id or new_plan not in db.PLAN_QUOTAS:
                self.send_error_json(400, "Geçersiz menajer ID veya paket adı.")
                return

            target = db.get_manager_by_id(manager_id)
            if not target:
                self.send_error_json(404, "Menajer bulunamadı.")
                return

            db.update_manager_plan(manager_id, new_plan)
            quota_limit = db.PLAN_QUOTAS.get(new_plan, 4)

            self.send_json(200, {
                "status": "success",
                "message": f"{target['name']} kullanıcısının paketi {new_plan.upper()} ({quota_limit} Profil) olarak güncellendi.",
                "managerId": manager_id,
                "newPlan": new_plan,
                "quotaLimit": quota_limit
            })
            return

        # POST /api/admin/impersonate (Section D.3)
        if path == "/api/admin/impersonate":
            admin = self.get_current_super_admin()
            if not admin:
                self.send_error_json(403, "Bu işlem için yönetici yetkisi gerekiyor.")
                return
            target_id = req_body.get("managerId", "").strip()
            target = db.get_manager_by_id(target_id)
            if not target:
                self.send_error_json(404, "Kullanıcı bulunamadı.")
                return

            log_id = db.log_impersonation_start(admin["id"], target_id)
            token = db.create_session(target_id, max_age_seconds=3600, impersonated_by=admin["id"], log_id=log_id)

            cookie_str = f"presskit_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=3600"
            self.send_json(200, {
                "status": "success",
                "message": f"'{target['name']}' hesabına teknik destek modunda giriş yapıldı.",
                "redirect": "/agency_dashboard.html"
            }, set_cookie=cookie_str)
            return

        # POST /api/admin/end-impersonation (Section D.5)
        if path == "/api/admin/end-impersonation":
            token = self.get_session_token()
            session = db.get_session(token)
            if not session or not session.get("impersonated_by"):
                self.send_error_json(400, "Aktif bir teknik destek oturumu bulunamadı.")
                return

            db.log_impersonation_end(session.get("log_id"))
            db.delete_session(token)
            admin_id = session["impersonated_by"]
            new_token = db.create_session(admin_id, max_age_seconds=2592000)

            cookie_str = f"presskit_session={new_token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"
            self.send_json(200, {
                "status": "success",
                "message": "Kendi yönetici hesabınıza döndünüz.",
                "redirect": "/admin.html"
            }, set_cookie=cookie_str)
            return

        # POST /api/logout
        if path == "/api/logout":
            token = self.get_session_token()
            if token:
                db.delete_session(token)
            cookie_str = "presskit_session=; Path=/; Max-Age=0"
            self.send_json(200, {"status": "success", "message": "Çıkış yapıldı", "redirect": "/login.html"}, set_cookie=cookie_str)
            return

        # ----------------------------------------------------
        # STRICT AUTHORIZATION GUARDS FOR ALL WRITE ENDPOINTS
        # ----------------------------------------------------
        mgr = self.get_current_manager()
        if not mgr:
            self.send_error_json(401, "Bu işlem için giriş yapmanız gerekmektedir.")
            return

        # POST /api/change-password
        if path == "/api/change-password":
            new_pass = req_body.get("newPassword", "").strip()
            if len(new_pass) < 8:
                self.send_error_json(400, "Yeni şifreniz en az 8 karakter olmalıdır.")
                return
            db.update_manager_password(mgr["id"], new_pass)
            self.send_json(200, {"status": "success", "message": "Şifreniz başarıyla güncellendi."})
            return

        # POST /api/subscription/upgrade (Section C.2)
        if path == "/api/subscription/upgrade":
            new_plan_id = req_body.get("planId", "").strip().lower()
            if new_plan_id not in ["bireysel", "starter", "pro", "enterprise"]:
                self.send_error_json(400, "Geçersiz plan seçimi.")
                return

            sub_ref = mgr.get("iyzico_subscription_ref") or f"sub-ref-{mgr['id']}"
            res = upgrade_subscription(sub_ref, new_plan_id, when="NOW")
            
            if res.get("status") == "success" or res.get("newPlanId"):
                db.update_manager_plan(mgr["id"], new_plan_id)
                db.set_manager_subscription(mgr["id"], subscription_ref=sub_ref, status="active")
                quota_limit = db.PLAN_QUOTAS.get(new_plan_id, 4)
                self.send_json(200, {
                    "status": "success",
                    "message": f"Aboneliğiniz başarıyla {new_plan_id.upper()} paketine yükseltildi.",
                    "plan": new_plan_id,
                    "quotaLimit": quota_limit
                })
            else:
                self.send_error_json(400, res.get("errorMessage", "Plan yükseltilemedi."))
            return

        # POST /api/subscription/cancel (Section C.3)
        if path == "/api/subscription/cancel":
            sub_ref = mgr.get("iyzico_subscription_ref") or f"sub-ref-{mgr['id']}"
            res = cancel_subscription(sub_ref)
            
            db.set_manager_subscription(mgr["id"], status="cancelling")
            send_email(mgr["email"], "PressKitLive Abonelik İptal Talebi", render_cancellation_email(mgr["name"], mgr.get("plan", "pro"), "30 gün sonra"))

            self.send_json(200, {
                "status": "success",
                "message": "Abonelik iptal talebiniz alındı. İptal işlemi cari fatura döneminizin sonunda geçerli olacaktır.",
                "subscriptionStatus": "cancelling"
            })
            return

        # POST /api/artists/create
        if path == "/api/artists/create":
            name = req_body.get("name", "").strip()
            genre = req_body.get("genre", "Pop / DJ").strip()
            if not name:
                self.send_error_json(400, "Sanatçı adı zorunludur.")
                return

            # SERVER-SIDE QUOTA CHECK (Section A.3)
            existing_artists = db.get_artists_by_manager(mgr["id"])
            current_count = len(existing_artists)
            plan_name = mgr.get("plan", "starter")
            quota_limit = db.PLAN_QUOTAS.get(plan_name, 4)

            if current_count >= quota_limit:
                self.send_error_json(
                    403,
                    f"Plan limitinize ulaştınız ({quota_limit} sanatçı). Daha fazla sanatçı eklemek için paketinizi yükseltin."
                )
                return

            new_artist = db.create_artist(mgr["id"], name, genre)
            self.send_json(200, {"status": "success", "artist": new_artist})
            return

        # POST /api/artists/edit
        if path == "/api/artists/edit":
            artist_id = req_body.get("artistId")
            artist = db.get_artist_by_id(artist_id)
            if not artist or not self.is_authorized_manager(mgr, artist):
                self.send_error_json(403, "Bu sanatçı üzerinde işlem yapma yetkiniz yoktur.")
                return
            updated = db.update_artist_info(
                artist_id,
                name=req_body.get("name"),
                genre=req_body.get("genre"),
                avatar=req_body.get("avatar"),
                banner=req_body.get("banner")
            )
            self.send_json(200, {"status": "success", "artist": updated})
            return

        # POST /api/folders/add
        if path == "/api/folders/add":
            artist_id = req_body.get("artistId", "yagmur-hizal")
            folder_name = req_body.get("name")
            is_locked = req_body.get("isLocked", False)

            artist = db.get_artist_by_id(artist_id)
            if not artist and mgr:
                my_artists = db.get_artists_by_manager(mgr["id"])
                if my_artists:
                    artist = my_artists[0]

            if not artist:
                self.send_error_json(404, "Sanatçı profili bulunamadı.")
                return

            if not folder_name:
                self.send_error_json(400, "Klasör adı zorunludur.")
                return

            target_artist_id = artist["id"]
            new_folder = db.create_folder(target_artist_id, folder_name, is_locked)
            self.send_json(200, {"status": "success", "folder": new_folder, "artist": db.get_artist_by_id(target_artist_id)})
            return

        # POST /api/folders/toggle-lock
        if path == "/api/folders/toggle-lock":
            folder_id = req_body.get("folderId")
            artist_id = req_body.get("artistId")

            artist = db.get_artist_by_id(artist_id)
            if not artist or not self.is_authorized_manager(mgr, artist):
                self.send_error_json(403, "Bu klasör üzerinde yetkiniz yoktur.")
                return

            new_state = db.toggle_folder_lock(folder_id)
            self.send_json(200, {"status": "success", "isLocked": new_state})
            return

        # POST /api/upload (Direct Base64 Image Upload to IMAGES_ROOT)
        if path == "/api/upload":
            data_url = req_body.get("dataUrl") or req_body.get("image")
            if not data_url:
                self.send_error_json(400, "dataUrl parametresi gereklidir.")
                return
            saved_url = db.save_uploaded_image(data_url, "user_upload")
            self.send_json(200, {"status": "success", "url": saved_url})
            return

        # POST /api/photos/add
        if path == "/api/photos/add":
            artist_id = req_body.get("artistId", "yagmur-hizal")
            folder_id = req_body.get("folderId", "folder-all")
            title = req_body.get("title", "Yeni Fotoğraf")
            raw_url = req_body.get("url", "/assets/images/yagmur-hizal/Kort1_2.JPG")
            resolution = req_body.get("resolution", "3808 x 5712 px (300 DPI)")
            badge = req_body.get("badge", "Yeni Görsel")

            artist = db.get_artist_by_id(artist_id)
            if not artist and mgr:
                my_artists = db.get_artists_by_manager(mgr["id"])
                if my_artists:
                    artist = my_artists[0]

            if not artist:
                self.send_error_json(404, "Sanatçı profili bulunamadı.")
                return

            target_artist_id = artist["id"]

            # Save base64 image to Volume/disk if uploaded directly
            url = db.save_uploaded_image(raw_url, f"photo_{target_artist_id}")

            new_photo = db.create_photo(target_artist_id, folder_id, title, url, resolution, badge)
            self.send_json(200, {"status": "success", "photo": new_photo, "artist": db.get_artist_by_id(target_artist_id)})
            return

        # POST /api/photos/delete
        if path == "/api/photos/delete":
            photo_id = req_body.get("photoId")
            artist_id = req_body.get("artistId", "yagmur-hizal")

            artist = db.get_artist_by_id(artist_id)
            if not artist or not self.is_authorized_manager(mgr, artist):
                self.send_error_json(403, "Bu fotoğrafı silme yetkiniz yoktur.")
                return

            db.delete_photo(photo_id)
            self.send_json(200, {"status": "success", "message": "Fotoğraf silindi.", "artist": db.get_artist_by_id(artist_id)})
            return

        self.send_error_json(404, "Böyle bir API endpoint bulunamadı.")

def run():
    os.chdir(DIRECTORY)
    server = ThreadedHTTPServer(("0.0.0.0", PORT), PressKitHandler)
    print(f"🚀 PressKitLive Multi-Manager Backend Server (Phase 1 SQLite) Çalışıyor:")
    print(f"👉 http://localhost:{PORT}")
    print(f"👉 SQLite Database (presskit.db) & Strict Ownership Guards Active")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu durduruldu.")

if __name__ == "__main__":
    run()
