// ==========================================================================
// PressKitLive — Multi-Language (TR / EN) Internationalization Engine
// Developed by DijitalGru™ (https://dijitalgru.com/)
// ==========================================================================

const i18nTranslations = {
  tr: {
    // Header & Brand
    nav_official_portal: "Resmi Medya Portalı",
    nav_notice_bar: "✨ PressKitLive™ Medya Merkezi: Tüm görseller ve dokümanlar orijinal çözünürlükte doğrudan indirilebilir.",
    nav_agency_login: "Ajans Girişi",
    nav_dashboard: "Yönetici Paneli",
    nav_back_to_artists: "← Tüm Sanatçılara Dön",

    // Section Titles
    section_bio: "Biyografi & Özgeçmiş",
    section_logos: "Logo & Marka Materyalleri",
    section_photos: "Yüksek Çözünürlüklü Basın Fotoğrafları (300 DPI)",
    section_folders: "Özel Doküman & Medya Klasörleri",
    section_riders: "Teknik Şartname & Sahne Planı (Rider)",
    section_socials: "Dijital Platform Bağlantıları",
    section_contact: "Yetkili İletişim & Menajerlik",
    section_discography: "Diskografi & Popüler Şarkılar",

    // Buttons & Actions
    btn_download_zip: "Tümünü ZIP Olarak İndir",
    btn_download_hd: "Yüksek Çözünürlüklü İndir (300 DPI)",
    btn_whatsapp_contact: "Menajer İle WhatsApp'tan İletişime Geç",
    btn_whatsapp_direct: "WhatsApp İle Ulaşın",
    btn_copy_link: "Bağlantıyı Kopyala",
    btn_copied: "Kopyalandı!",
    btn_preview: "Önizle",
    btn_unlock: "Şifreyi Gir & Aç",
    btn_edit_profile: "Profili Düzenle",
    btn_add_artist: "+ Yeni Profil / Portföy Ekle",
    btn_upgrade_plan: "Paketinizi Yükseltin",

    // Empty States
    empty_logos_title: "Logo & Marka Materyali Bulunmuyor",
    empty_logos_desc: "Menajer bu sanatçı için henüz vektör logo veya marka materyali yüklemedi.",
    empty_photos_title: "Fotoğraf Bulunmuyor",
    empty_photos_desc: "Bu kategoriye henüz yüksek çözünürlüklü fotoğraf eklenmedi.",
    empty_folders_title: "Klasör Bulunmuyor",
    empty_folders_desc: "Henüz özel doküman klasörü oluşturulmadı.",
    empty_riders_title: "Teknik Şartname Bulunmuyor",
    empty_riders_desc: "Henüz teknik şartname (rider) belgesi yüklenmedi.",
    empty_bio: "Henüz biyografi bilgisi girilmemiştir.",

    // Badges & Statuses
    badge_official: "Resmi Presskit Portalı",
    badge_verified: "Onaylı Sanatçı Hesabı",
    badge_locked_folder: "Şifreli Özel Klasör",
    badge_300dpi: "300 DPI Orijinal Baskı Kalitesi",

    // Dashboard UI
    dash_title: "Ajans Yönetim Paneli",
    dash_managed_portfolio: "Yönetilen Portföy",
    dash_agency_label: "AJANS & TEMSİLCİLİK",
    dash_subscription_label: "AKTİF ABONELİK",
    dash_quota_label: "PORTFÖY KOTASI",
    dash_trial_active: "7 Günlük Ücretsiz Deneme Hesabı",
    dash_trial_days_left: "Kalan Süre",
    dash_trial_expired: "7 Günlük Ücretsiz Deneme Süreniz Sona Ermiştir",

    // Language Names
    lang_tr: "Türkçe",
    lang_en: "English"
  },
  en: {
    // Header & Brand
    nav_official_portal: "Official Media Portal",
    nav_notice_bar: "✨ PressKitLive™ Media Center: Download all press assets and high-res files directly.",
    nav_agency_login: "Agency Portal Login",
    nav_dashboard: "Agency Dashboard",
    nav_back_to_artists: "← All Artists",

    // Section Titles
    section_bio: "Biography & Profile",
    section_logos: "Logos & Brand Assets",
    section_photos: "High-Resolution Press Photos (300 DPI)",
    section_folders: "Media Folders & Documents",
    section_riders: "Technical Rider & Stage Plan",
    section_socials: "Digital Platform Links",
    section_contact: "Management & Authorized Contact",
    section_discography: "Discography & Highlights",

    // Buttons & Actions
    btn_download_zip: "Download All as ZIP",
    btn_download_hd: "Download High-Res (300 DPI)",
    btn_whatsapp_contact: "Contact Manager via WhatsApp",
    btn_whatsapp_direct: "Chat on WhatsApp",
    btn_copy_link: "Copy Link",
    btn_copied: "Copied!",
    btn_preview: "Preview",
    btn_unlock: "Enter Password & Unlock",
    btn_edit_profile: "Edit Profile",
    btn_add_artist: "+ Add New Profile / Portfolio",
    btn_upgrade_plan: "Upgrade Plan",

    // Empty States
    empty_logos_title: "No Logo & Brand Assets Available",
    empty_logos_desc: "The management has not uploaded vector logos or brand assets for this artist yet.",
    empty_photos_title: "No Photos Available",
    empty_photos_desc: "No high-resolution press photos have been uploaded to this category yet.",
    empty_folders_title: "No Folders Available",
    empty_folders_desc: "No custom media folders have been created yet.",
    empty_riders_title: "No Technical Rider Available",
    empty_riders_desc: "No technical rider or stage plan document has been uploaded yet.",
    empty_bio: "Biography information has not been added yet.",

    // Badges & Statuses
    badge_official: "Official Presskit Portal",
    badge_verified: "Verified Artist Account",
    badge_locked_folder: "Password Protected Folder",
    badge_300dpi: "300 DPI Original Print Quality",

    // Dashboard UI
    dash_title: "Agency Management Dashboard",
    dash_managed_portfolio: "Managed Roster",
    dash_agency_label: "AGENCY & REPRESENTATION",
    dash_subscription_label: "ACTIVE SUBSCRIPTION",
    dash_quota_label: "ROSTER QUOTA",
    dash_trial_active: "7-Day Free Trial Account",
    dash_trial_days_left: "Time Remaining",
    dash_trial_expired: "Your 7-Day Free Trial Period Has Expired",

    // Language Names
    lang_tr: "Türkçe",
    lang_en: "English"
  }
};

let currentLang = localStorage.getItem('presskit_lang') || 'tr';

function getTranslation(key, defaultText) {
  if (i18nTranslations[currentLang] && i18nTranslations[currentLang][key]) {
    return i18nTranslations[currentLang][key];
  }
  return defaultText || key;
}

function setLanguage(lang) {
  if (lang !== 'tr' && lang !== 'en') return;
  currentLang = lang;
  localStorage.setItem('presskit_lang', lang);

  // Update HTML lang attribute
  document.documentElement.lang = lang;

  // Update all elements with data-i18n attribute
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (i18nTranslations[lang] && i18nTranslations[lang][key]) {
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        el.placeholder = i18nTranslations[lang][key];
      } else {
        el.innerText = i18nTranslations[lang][key];
      }
    }
  });

  // Update language toggle buttons active state
  document.querySelectorAll('.lang-toggle-btn').forEach(btn => {
    if (btn.dataset.lang === lang) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Trigger custom event if page scripts need re-render
  window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: lang } }));
}

function initI18n() {
  setLanguage(currentLang);
}

// Global Exports
window.setLanguage = setLanguage;
window.getTranslation = getTranslation;
window.initI18n = initI18n;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initI18n);
} else {
  initI18n();
}
