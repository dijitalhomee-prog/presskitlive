"""
PressKitLive — One-Time Legacy Migration Script (migrate_legacy_data.py)
Migrates legacy assets/data/artists.json (Yağmur Hızal) to SQLite database presskit.db under manager aycan@aycanyagci.com
"""

import os
import json
import db

def migrate():
    db.init_db()

    # 1. Create or get primary manager account (Aycan Yağcı)
    manager = db.get_manager_by_email("aycan@aycanyagci.com")
    if not manager:
        print("👤 Creating primary manager account: aycan@aycanyagci.com...")
        manager = db.create_manager(
            email="aycan@aycanyagci.com",
            password="8530gjeh48",
            name="Aycan Yağcı",
            agency_name="Aycan Yağcı Booking & Management",
            phone="+90 544 535 34 35"
        )
    
    manager_id = manager["id"]
    print(f"✅ Primary Manager ID: {manager_id}")

    # Ensure default 'yagmur-hizal' artist exists in DB
    if not db.get_artist_by_id("yagmur-hizal"):
        print("🎵 Seeding default artist 'yagmur-hizal'...")
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO artists (id, manager_id, name, genre, monthly_listeners, avatar, banner, bio, short_bio, socials_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("yagmur-hizal", manager_id, "Yağmur Hızal", "Pop / Indie Pop", "1.200", "/assets/images/yagmur-hizal/Kort1_2.JPG", "/assets/images/yagmur-hizal/Kort1_2.JPG", "Yağmur Hızal resmi presskit.", "Pop / Indie Pop Sanatçısı", "{}", "2026-08-16 12:00:00"))
            conn.commit()

    # 2. Read legacy artists.json
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "data", "artists.json")
    if not os.path.exists(json_path):
        print("ℹ️ No legacy artists.json file found to migrate.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        legacy_data = json.load(f)

    if not legacy_data:
        print("ℹ️ legacy artists.json is empty.")
        return

    # 3. Import each artist, folder, and photo
    for art in legacy_data:
        art_id = art["id"]
        existing_artist = db.get_artist_by_id(art_id)
        if not existing_artist:
            print(f"🎵 Migrating artist '{art['name']}' ({art_id})...")
            with db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO artists (id, manager_id, name, genre, monthly_listeners, avatar, banner, bio, short_bio, socials_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    art_id,
                    manager_id,
                    art.get("name", "Yağmur Hızal"),
                    art.get("genre", "Pop / Indie Pop"),
                    art.get("monthlyListeners", "1.200"),
                    art.get("avatar", ""),
                    art.get("banner", ""),
                    art.get("bio", ""),
                    art.get("shortBio", ""),
                    json.dumps(art.get("socials", {})),
                    "2026-08-16 12:00:00"
                ))
                conn.commit()

        # Migrate Folders
        folders = art.get("folders", [])
        for f in folders:
            f_id = f["id"]
            with db.get_connection() as conn:
                existing_f = conn.execute("SELECT id FROM folders WHERE id = ?", (f_id,)).fetchone()
                if not existing_f:
                    print(f"  📁 Migrating folder '{f['name']}' ({f_id})...")
                    conn.execute("""
                        INSERT INTO folders (id, artist_id, name, is_locked, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (f_id, art_id, f["name"], 1 if f.get("isLocked") else 0, "2026-08-16 12:00:00"))
                    conn.commit()

        # Migrate Photos
        photos = art.get("pressPhotos", [])
        for p in photos:
            p_id = p["id"]
            with db.get_connection() as conn:
                existing_p = conn.execute("SELECT id FROM photos WHERE id = ?", (p_id,)).fetchone()
                if not existing_p:
                    print(f"  🖼️ Migrating photo '{p['title']}' ({p_id})...")
                    conn.execute("""
                        INSERT INTO photos (id, artist_id, folder_id, title, type, format, resolution, file_size, url, badge, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p_id,
                        art_id,
                        p.get("folderId", "folder-all"),
                        p.get("title", "Fotoğraf"),
                        p.get("type", "Konser / Sahne"),
                        p.get("format", "JPG"),
                        p.get("resolution", "3808 x 5712 px (300 DPI)"),
                        p.get("fileSize", "5.5 MB"),
                        p.get("url", ""),
                        p.get("badge", ""),
                        "2026-08-16 12:00:00"
                    ))
                    conn.commit()

    # 4. Backup legacy artists.json -> artists.json.bak
    bak_path = f"{json_path}.bak"
    if os.path.exists(json_path):
        os.rename(json_path, bak_path)
        print(f"🎉 Legacy migration complete! Backed up artists.json to {bak_path}")

if __name__ == "__main__":
    migrate()
