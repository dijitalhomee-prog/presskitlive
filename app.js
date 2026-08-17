// ==========================================================================
// PressKitLive — Core Application Logic
// Phase 1: Multi-Manager Architecture (SQLite REST API Integration)
// Developed by DijitalGru™ (https://dijitalgru.com/)
// ==========================================================================

let state = {
  artist: null,
  myArtists: [],
  activeFolderId: 'folder-all',
  isPublicView: false,
  isOwner: false
};

// --------------------------------------------------------------------------
// HTML Security Escaper (XSS Prevention)
// --------------------------------------------------------------------------
function escapeHTML(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ==========================================================================
// CUSTOM UI TOAST & CONFIRMATION MODAL SYSTEM
// ==========================================================================
function showToast(message, type = 'success', duration = 3500) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    document.body.appendChild(container);
  }

  const icons = {
    success: 'check-circle-2',
    error: 'alert-circle',
    warning: 'alert-triangle',
    info: 'info'
  };

  const iconName = icons[type] || 'info';

  const toast = document.createElement('div');
  toast.className = `custom-toast toast-${type}`;
  toast.innerHTML = `
    <div class="custom-toast-icon"><i data-lucide="${iconName}"></i></div>
    <div class="custom-toast-message">${escapeHTML(message)}</div>
    <button type="button" class="custom-toast-close" onclick="this.parentElement.remove()">&times;</button>
  `;

  container.appendChild(toast);
  if (window.lucide) lucide.createIcons();

  setTimeout(() => {
    toast.classList.add('hiding');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function showConfirm({
  title = 'Emin misiniz?',
  message = 'Bu işlemi gerçekleştirmek istediğinize emin misiniz?',
  confirmText = 'Evet, Devam Et',
  cancelText = 'Vazgeç',
  isDanger = true,
  icon = null
}) {
  return new Promise((resolve) => {
    let backdrop = document.getElementById('customConfirmBackdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'customConfirmBackdrop';
      backdrop.className = 'custom-confirm-backdrop';
      document.body.appendChild(backdrop);
    }

    const iconType = isDanger ? 'danger' : 'info';
    const iconName = icon || (isDanger ? 'alert-triangle' : 'help-circle');
    const confirmBtnClass = isDanger ? 'custom-confirm-btn-danger' : 'custom-confirm-btn-primary';

    backdrop.innerHTML = `
      <div class="custom-confirm-card">
        <div class="custom-confirm-icon-box ${iconType}">
          <i data-lucide="${iconName}"></i>
        </div>
        <h3 class="custom-confirm-title">${escapeHTML(title)}</h3>
        <div class="custom-confirm-message">${escapeHTML(message)}</div>
        <div class="custom-confirm-actions">
          <button type="button" class="custom-confirm-btn custom-confirm-btn-cancel" id="btnCustomConfirmCancel">
            ${escapeHTML(cancelText)}
          </button>
          <button type="button" class="custom-confirm-btn ${confirmBtnClass}" id="btnCustomConfirmOk">
            ${escapeHTML(confirmText)}
          </button>
        </div>
      </div>
    `;

    if (window.lucide) lucide.createIcons();

    requestAnimationFrame(() => backdrop.classList.add('active'));

    const cleanup = (result) => {
      backdrop.classList.remove('active');
      setTimeout(() => {
        backdrop.innerHTML = '';
        resolve(result);
      }, 250);
    };

    const cancelBtn = document.getElementById('btnCustomConfirmCancel');
    const okBtn = document.getElementById('btnCustomConfirmOk');
    if (cancelBtn) cancelBtn.onclick = () => cleanup(false);
    if (okBtn) okBtn.onclick = () => cleanup(true);
    backdrop.onclick = (e) => {
      if (e.target === backdrop) cleanup(false);
    };
  });
}

window.showToast = showToast;
window.showConfirm = showConfirm;

// --------------------------------------------------------------------------
// Initialization & Data Loading
// --------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  state.isPublicView = document.body.dataset.view === 'public' || window.location.pathname.includes('public.html');
  
  await checkImpersonationStatus();
  await checkTrialStatus();
  await loadArtistData();
  setupNavigation();
  setupActions();
  setupFolderModals();
  setupPhotoModals();
});

async function checkImpersonationStatus() {
  try {
    const res = await fetch('/api/session');
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated && data.user && data.user.impersonation && data.user.impersonation.active) {
        const impBanner = document.getElementById('impersonationBanner');
        const impName = document.getElementById('impersonationTargetName');
        if (impName) impName.innerText = data.user.name || 'Menajer';
        if (impBanner) impBanner.style.display = 'flex';
      }
    }
  } catch (e) {}
}

async function checkTrialStatus() {
  try {
    const res = await fetch('/api/session');
    if (!res.ok) return;
    const data = await res.json();
    if (!data.authenticated || !data.user) return;

    const user = data.user;
    const mainContent = document.querySelector('.main-content') || document.querySelector('.app-container');
    if (!mainContent) return;

    // Check if banner already exists
    if (document.getElementById('trialBannerWrapper')) return;

    const bannerContainer = document.createElement('div');
    bannerContainer.id = 'trialBannerWrapper';

    if (user.subscriptionStatus === 'trial_active') {
      const daysLeft = user.trialDaysLeft !== undefined ? user.trialDaysLeft : 7;
      bannerContainer.innerHTML = `
        <div class="trial-banner trial-active" style="background: linear-gradient(90deg, rgba(29, 185, 84, 0.15) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1px solid rgba(29, 185, 84, 0.4); padding: 12px 20px; border-radius: 12px; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; font-size: 13px; color: #fff;">
          <div style="display:flex; align-items:center; gap:10px;">
            <i data-lucide="zap" style="color:var(--primary); width:20px; height:20px;"></i>
            <span><strong>7 Günlük Ücretsiz Deneme Hesabı:</strong> Kalan süreniz <strong>${daysLeft} Gün</strong>. Tüm özellikler 7 gün ücretsiz kullanıma açıktır.</span>
          </div>
          <a href="/landing.html#fiyatlandirma" class="btn btn-primary btn-small" style="font-size:12px; font-weight:700; padding:6px 14px; white-space:nowrap; text-decoration:none;">
            Aboneliğe Yükselt
          </a>
        </div>
      `;
      mainContent.insertBefore(bannerContainer, mainContent.firstChild);
      if (window.lucide) lucide.createIcons();
    } else if (user.subscriptionStatus === 'trial_expired' || user.subscriptionStatus === 'passive') {
      bannerContainer.innerHTML = `
        <div class="trial-banner trial-expired" style="background: linear-gradient(90deg, rgba(239, 68, 68, 0.2) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1px solid rgba(239, 68, 68, 0.4); padding: 16px 20px; border-radius: 12px; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; font-size: 14px; color: #fff; box-shadow: 0 8px 24px rgba(239, 68, 68, 0.15);">
          <div style="display:flex; align-items:center; gap:12px;">
            <i data-lucide="alert-triangle" style="color:#ef4444; width:26px; height:26px; flex-shrink:0;"></i>
            <div>
              <strong style="color:#fff; font-size:15px; display:block;">⚠️ 7 Günlük Ücretsiz Deneme Süreniz Sona Ermiştir</strong>
              <span style="color:var(--text-subdued); font-size:13px;">Hesabınız otomatik olarak pasif duruma düşmüştür. Portallarınızı canlı tutmak için lütfen bir abonelik paketi seçiniz.</span>
            </div>
          </div>
          <a href="/landing.html#fiyatlandirma" class="btn btn-spotify" style="padding:10px 18px; font-weight:800; font-size:13px; white-space:nowrap; flex-shrink:0; text-decoration:none;">
            <i data-lucide="credit-card"></i> Abonelik Paketlerini İncele
          </a>
        </div>
      `;
      mainContent.insertBefore(bannerContainer, mainContent.firstChild);
      if (window.lucide) lucide.createIcons();
    }
  } catch (e) {}
}

async function endImpersonation() {
  try {
    const res = await fetch('/api/admin/end-impersonation', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success' && data.redirect) {
      window.location.href = data.redirect;
    } else {
      alert(data.message || "Yönetici hesabına dönülemedi.");
    }
  } catch (err) {
    alert("Sunucuya bağlanılamadı.");
  }
}

async function loadArtistData() {
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const paramArtistId = urlParams.get('artistId') || urlParams.get('id');

    if (state.isPublicView) {
      // PUBLIC PRESSKIT VIEW
      const targetId = paramArtistId || 'yagmur-hizal';
      const apiRes = await fetch(`/api/artist?artistId=${encodeURIComponent(targetId)}`);
      if (apiRes.ok) {
        const apiJson = await apiRes.json();
        if (apiJson.artist) {
          state.artist = apiJson.artist;
          state.isOwner = apiJson.isOwner || false;
        }
      }
    } else {
      // MANAGER / ADMIN VIEW
      const apiRes = await fetch('/api/my-artists');
      if (apiRes.ok) {
        const apiJson = await apiRes.json();
        if (apiJson.artists && apiJson.artists.length > 0) {
          state.myArtists = apiJson.artists;
        }
      }

      let matched = null;
      if (paramArtistId && state.myArtists.length > 0) {
        const normParam = String(paramArtistId).toLowerCase().trim();
        matched = state.myArtists.find(a => 
          String(a.id).toLowerCase() === normParam || 
          String(a.slug || '').toLowerCase() === normParam ||
          String(a.name || '').toLowerCase() === normParam
        );
      }

      if (matched) {
        state.artist = matched;
        state.isOwner = true;
      } else if (paramArtistId) {
        // Fetch specific artist by ID/slug from server
        const fallbackRes = await fetch(`/api/artist?artistId=${encodeURIComponent(paramArtistId)}`);
        if (fallbackRes.ok) {
          const fallJson = await fallbackRes.json();
          if (fallJson.artist) {
            state.artist = fallJson.artist;
            state.isOwner = fallJson.isOwner || false;
          }
        }
      }

      if (!state.artist && state.myArtists.length > 0) {
        state.artist = state.myArtists[0];
        state.isOwner = true;
      }
    }

    if (state.artist) {
      renderArtistHeader();
      renderManagerInfo();
      renderFoldersBar();
      renderFilteredPhotos();
    }
  } catch (error) {
    console.error('Artist data load error:', error);
  }
}

// --------------------------------------------------------------------------
// UI Renderers
// --------------------------------------------------------------------------
function generateInitialsAvatar(name) {
  const initials = (name || 'P').split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'P';
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
    <rect width="200" height="200" fill="#18181b"/>
    <circle cx="100" cy="100" r="88" fill="#27272a" stroke="#1db854" stroke-width="5"/>
    <text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="70" font-weight="900" fill="#1db854">${initials}</text>
  </svg>`;
  try {
    return 'data:image/svg+xml;base64,' + window.btoa(unescape(encodeURIComponent(svg)));
  } catch (e) {
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }
}

function renderArtistHeader() {
  if (!state.artist) return;

  const name = state.artist.name || 'Profil Adı';

  if (name) {
    if (state.isPublicView) {
      document.title = `${name} — Resmi Presskit Portalı | PressKitLive`;
    } else {
      document.title = `${name} — Menajer Yönetim Paneli | PressKitLive`;
    }
  }

  const titleEl = document.getElementById('heroArtistName') || document.getElementById('artistTitleName');
  if (titleEl) titleEl.innerText = name;

  const genreEl = document.getElementById('artistGenreText');
  if (genreEl) {
    if (state.artist.genre) {
      genreEl.innerText = state.artist.genre;
      const genrePill = document.getElementById('genreMetaPill');
      if (genrePill) genrePill.style.display = 'inline-flex';
    } else {
      const genrePill = document.getElementById('genreMetaPill');
      if (genrePill) genrePill.style.display = 'none';
    }
  }

  const avatarEl = document.getElementById('heroAvatar') || document.getElementById('artistAvatarImg');
  if (avatarEl) {
    avatarEl.onerror = function() {
      this.onerror = null;
      this.src = generateInitialsAvatar(name);
    };
    if (state.artist.avatar && state.artist.avatar.trim() !== '') {
      const rawAv = state.artist.avatar.trim();
      avatarEl.src = (rawAv.startsWith('http') || rawAv.startsWith('/') || rawAv.startsWith('data:')) ? rawAv : '/' + rawAv;
    } else {
      avatarEl.src = generateInitialsAvatar(name);
    }
  }

  const breadcrumbEl = document.getElementById('breadcrumbArtist');
  if (breadcrumbEl) breadcrumbEl.innerText = name;

  const activeSlug = state.artist.slug || state.artist.id || 'profil';
  const slugBadgeEl = document.getElementById('artistSlugBadge');
  if (slugBadgeEl) slugBadgeEl.innerText = activeSlug;

  const heroBg = document.getElementById('heroBg');
  if (heroBg) {
    if (state.artist.banner && state.artist.banner.trim() !== '') {
      const rawBg = state.artist.banner.trim();
      const bgUrl = (rawBg.startsWith('http') || rawBg.startsWith('/')) ? rawBg : '/' + rawBg;
      heroBg.style.backgroundImage = `url('${bgUrl}')`;
    } else {
      heroBg.style.backgroundImage = 'linear-gradient(180deg, #18181b 0%, #09090b 100%)';
    }
  }

  const listenersEl = document.getElementById('monthlyListenersText');
  if (listenersEl) {
    if (state.artist.monthlyListeners) {
      listenersEl.innerText = `${state.artist.monthlyListeners} Takipçi / Dinleyici`;
      listenersEl.style.display = 'inline-block';
    } else {
      listenersEl.style.display = 'none';
    }
  }

  // Dynamically update Logo & Tipografi text previews
  const logoGoldPrev = document.getElementById('logoGoldPreview');
  if (logoGoldPrev) logoGoldPrev.innerText = name.toUpperCase();

  const logoTextPrev = document.getElementById('logoTextPreview');
  if (logoTextPrev) logoTextPrev.innerText = name.toUpperCase();

  const logoCardTitle1 = document.getElementById('logoCardTitle1');
  if (logoCardTitle1) logoCardTitle1.innerText = `${name} Tipografi Logosu`;

  // Dynamically render multi-sectoral platform links and uploaded logos
  renderPlatformLinks();
  renderLogos();
}

function renderLogos() {
  const grid = document.getElementById('logoCardsGrid');
  if (!grid || !state || !state.artist) return;

  const pressPhotos = state.artist.pressPhotos || [];
  // Filter photos that are tagged as Logo / Marka OR uploaded via Add Logo modal
  const logos = pressPhotos.filter(p => {
    if (!p) return false;
    const badge = (p.badge || '').toLowerCase();
    const title = (p.title || '').toLowerCase();
    const folderId = (p.folderId || '').toLowerCase();
    return badge.includes('logo') || badge.includes('marka') || title.includes('logo') || folderId.includes('logo');
  });

  if (logos.length === 0) {
    if (state.isPublicView) {
      grid.innerHTML = `
        <div class="empty-state-box" style="grid-column: 1 / -1; text-align: center; padding: 40px 20px; background: var(--bg-surface); border: 1px dashed var(--border-glass); border-radius: 12px; width: 100%;">
          <i data-lucide="layers" style="width: 36px; height: 36px; color: var(--text-subdued); margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto;"></i>
          <h4 style="color: #fff; margin: 0 0 6px 0; font-size: 16px; font-weight: 700;">${typeof getTranslation==='function' ? getTranslation('empty_logos_title', 'Logo & Marka Materyali Bulunmuyor') : 'Logo & Marka Materyali Bulunmuyor'}</h4>
          <p style="color: var(--text-subdued); font-size: 13px; margin: 0;">${typeof getTranslation==='function' ? getTranslation('empty_logos_desc', 'Bu sanatçı için henüz kamuya açık logo veya marka dosyası yüklenmemiştir.') : 'Bu sanatçı için henüz kamuya açık logo veya marka dosyası yüklenmemiştir.'}</p>
        </div>
      `;
    } else {
      grid.innerHTML = `
        <div class="empty-state-box" style="grid-column: 1 / -1; text-align: center; padding: 40px 20px; background: var(--bg-surface); border: 1px dashed var(--border-glass); border-radius: 12px; width: 100%;">
          <i data-lucide="layers" style="width: 36px; height: 36px; color: var(--text-subdued); margin-bottom: 10px; display: block; margin-left: auto; margin-right: auto;"></i>
          <h4 style="color: #fff; margin: 0 0 6px 0; font-size: 16px; font-weight: 700;">${typeof getTranslation==='function' ? getTranslation('empty_logos_title', 'Henüz Logo veya Marka Materyali Eklenmedi') : 'Henüz Logo veya Marka Materyali Eklenmedi'}</h4>
          <p style="color: var(--text-subdued); font-size: 13px; margin: 0 0 16px 0;">${typeof getTranslation==='function' ? getTranslation('empty_logos_desc', 'Afiş ve tasarım işleri için sanatçınızın logosunu veya vektörel marka metnini ekleyin.') : 'Afiş ve tasarım işleri için sanatçınızın logosunu veya vektörel marka metnini ekleyin.'}</p>
          <button class="btn btn-primary btn-small" onclick="document.getElementById('addLogoModal').classList.add('active')" style="margin: 0 auto; display: inline-flex;">
            <i data-lucide="upload-cloud"></i> + Logo Ekle
          </button>
        </div>
      `;
    }
    if (window.lucide) lucide.createIcons();
    return;
  }

  // Render uploaded logos
  let html = '';
  logos.forEach(p => {
    const rawUrl = p.url || '';
    const imgUrl = (rawUrl.startsWith('http') || rawUrl.startsWith('/') || rawUrl.startsWith('data:')) ? rawUrl : '/' + rawUrl;
    const format = p.resolution || 'PNG';
    const downloadLabel = typeof getTranslation === 'function' ? getTranslation('btn_download_hd', `${format} İndir`) : `${format} İndir`;

    html += `
      <div class="logo-card" id="logoCard-${escapeHTML(p.id)}">
        <div class="logo-preview-box dark-bg" style="background:#09090b; padding:24px; display:flex; align-items:center; justify-content:center; border-radius:12px 12px 0 0; min-height:140px; border-bottom:1px solid var(--border-subtle);">
          <img src="${imgUrl}" alt="${escapeHTML(p.title)}" style="max-height:100px; max-width:100%; object-fit:contain;">
        </div>
        <div class="logo-card-info" style="padding:16px;">
          <h4 style="color:#fff; margin:0 0 6px 0; font-size:16px; font-weight:700;">${escapeHTML(p.title)}</h4>
          <p style="color:var(--text-subdued); font-size:12px; margin:0 0 14px 0;">300 DPI Yüksek Çözünürlüklü Marka Dosyası (${escapeHTML(format)})</p>
          <div class="logo-card-actions" style="display:flex; gap:8px; align-items:center;">
            <a href="${imgUrl}" download="${escapeHTML(p.title)}" class="btn btn-outline" style="flex-grow:1; justify-content:center;">
              <i data-lucide="download"></i> ${escapeHTML(format)} ${downloadLabel}
            </a>
            ${!state.isPublicView ? `
              <button type="button" class="btn-delete-icon" style="background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.3); color:#ef4444; border-radius:8px; width:38px; height:38px; display:flex; align-items:center; justify-content:center; cursor:pointer; flex-shrink:0;" title="Logoyu Sil" onclick="deletePhotoHandler('${escapeHTML(p.id)}', '${escapeHTML(p.title)}')">
                <i data-lucide="trash-2" style="width:16px; height:16px;"></i>
              </button>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  });

  grid.innerHTML = html;
  if (window.lucide) lucide.createIcons();
}

function renderPlatformLinks() {
  const grid = document.getElementById('platformLinksGrid');
  if (!grid || !state || !state.artist) return;

  const socials = state.artist.socials || {};
  
  const platforms = [
    { key: 'instagram', name: 'Instagram', icon: 'instagram', color: '#e1306c', defaultSub: '@profil' },
    { key: 'youtube', name: 'YouTube / Showreel', icon: 'video', color: '#ff0000', defaultSub: 'Resmi Kanal & Video Klip' },
    { key: 'behance', name: 'Behance', icon: 'palette', color: '#0057ff', defaultSub: 'Visual & Tasarım Portföyü' },
    { key: 'linkedin', name: 'LinkedIn', icon: 'linkedin', color: '#0a66c2', defaultSub: 'Kurumsal & Profesyonel Profil' },
    { key: 'imdb', name: 'IMDb', icon: 'film', color: '#f3ce13', defaultSub: 'Sinema & Cast Kaydı' },
    { key: 'vimeo', name: 'Vimeo', icon: 'video', color: '#1ab7ea', defaultSub: 'Showreel & Video Deposu' },
    { key: 'spotify', name: 'Spotify', icon: 'disc', color: '#1db954', defaultSub: 'Müzik Profili' },
    { key: 'website', name: 'Web Sitesi / Portföy', icon: 'globe', color: '#60a5fa', defaultSub: 'Resmi İnternet Sitesi' }
  ];

  let html = '';
  let count = 0;

  platforms.forEach(p => {
    const url = socials[p.key];
    if (url && String(url).trim()) {
      count++;
      let subText = p.defaultSub;
      if (p.key === 'instagram') {
        const handle = String(url).replace(/\/$/, '').split('/').pop();
        subText = handle ? '@' + handle : '@instagram';
      } else if (p.key === 'website') {
        subText = String(url).replace(/^https?:\/\//, '').replace(/\/$/, '');
      }

      html += `
        <a href="${escapeHTML(url)}" target="_blank" class="platform-card ${p.key}" style="border-left: 3px solid ${p.color};">
          <div class="platform-icon" style="color: ${p.color};"><i data-lucide="${p.icon}"></i></div>
          <div class="platform-info">
            <span class="platform-name">${p.name}</span>
            <span class="platform-sub">${escapeHTML(subText)}</span>
          </div>
          <i data-lucide="external-link" class="arrow-icon"></i>
        </a>
      `;
    }
  });

  if (count === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 32px 16px; background: rgba(24, 24, 27, 0.4); border: 1px dashed var(--border-subtle); border-radius: var(--radius-lg);">
        <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 12px;">Henüz eklenmiş dijital platform bağlantısı bulunmuyor.</p>
        <button type="button" class="btn btn-spotify btn-small" onclick="if(typeof openEditSocialsModal==='function') openEditSocialsModal()">
          <i data-lucide="plus"></i> + Bağlantı Ekle / Düzenle
        </button>
      </div>
    `;
  } else {
    grid.innerHTML = html;
  }

  if (window.lucide) lucide.createIcons();
}

function renderManagerInfo() {
  if (!state.artist || !state.artist.manager) return;
  const mgr = state.artist.manager;

  const heroNameEl = document.getElementById('heroManagerName');
  if (heroNameEl) heroNameEl.innerText = mgr.name || 'Menajer';

  const heroPhoneEl = document.getElementById('heroManagerPhone');
  if (heroPhoneEl) heroPhoneEl.innerText = mgr.phone || '';

  const cardNameEl = document.getElementById('cardManagerName');
  if (cardNameEl) cardNameEl.innerText = mgr.name || 'Menajer';

  const cardPhoneEl = document.getElementById('cardManagerPhone');
  if (cardPhoneEl) cardPhoneEl.innerText = mgr.phone || 'Belirtilmedi';

  const cardEmailEl = document.getElementById('cardManagerEmail');
  if (cardEmailEl) cardEmailEl.innerText = mgr.email || '';

  const updateWaBtn = (btnEl) => {
    if (!btnEl) return;
    const waRaw = mgr.whatsappRaw || mgr.phoneRaw;
    if (waRaw) {
      btnEl.style.display = 'inline-flex';
      btnEl.href = `https://wa.me/${waRaw}?text=Merhaba%20${encodeURIComponent(mgr.name)}%2C%20${encodeURIComponent(state.artist.name)}%20presskit%20ve%20rezervasyon%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum.`;
    } else {
      btnEl.style.display = 'none';
    }
  };

  updateWaBtn(document.getElementById('btnHeroWhatsapp'));
  updateWaBtn(document.getElementById('btnPublicHeroWhatsapp'));
  updateWaBtn(document.getElementById('gridWhatsappLink'));

  const phoneLink = document.getElementById('gridPhoneLink');
  if (phoneLink) {
    if (mgr.phoneRaw) {
      phoneLink.style.display = 'inline-flex';
      phoneLink.href = `tel:+${mgr.phoneRaw}`;
    } else {
      phoneLink.style.display = 'none';
    }
  }

  const countBadgeEl = document.getElementById('sidebarArtistCountBadge');
  if (countBadgeEl) {
    if (state.myArtists && state.myArtists.length > 0) {
      countBadgeEl.innerText = `${state.myArtists.length} Sanatçı`;
    } else {
      countBadgeEl.innerText = `Konsol`;
    }
  }

  const adminLinkEl = document.getElementById('sidebarAdminLink');
  if (adminLinkEl && mgr && mgr.isSuperAdmin) {
    adminLinkEl.style.display = 'flex';
  }

  const mailLink = document.getElementById('gridEmailLink');
  if (mailLink && mgr.email) mailLink.href = `mailto:${mgr.email}`;

  renderSidebarPortfolio();
}

function renderSidebarPortfolio() {
  const container = document.getElementById('sidebarPortfolioList');
  if (!container) return;

  const artists = (state.myArtists && state.myArtists.length > 0) ? state.myArtists : (state.artist ? [state.artist] : []);

  if (artists.length === 0) {
    container.innerHTML = `
      <div class="portfolio-empty-note">
        <span>Henüz bağlı sanatçı yok</span>
        <a href="agency_dashboard.html" class="btn-add-artist-mini">+ Sanatçı Ekle</a>
      </div>
    `;
    return;
  }

  let html = '';
  artists.forEach(a => {
    const isCurrent = (state.artist && (state.artist.id === a.id || state.artist.slug === a.slug));
    const avatarUrl = a.avatar && a.avatar.trim() !== '' ? a.avatar.trim() : generateInitialsAvatar(a.name);
    const safeAvatar = (avatarUrl.startsWith('http') || avatarUrl.startsWith('/') || avatarUrl.startsWith('data:')) ? avatarUrl : '/' + avatarUrl;
    const genre = a.genre || 'Sanatçı';

    html += `
      <a href="/index.html?artistId=${escapeHTML(a.id)}" class="portfolio-artist-item ${isCurrent ? 'active' : ''}" title="${escapeHTML(a.name)} — ${escapeHTML(genre)}">
        <img src="${safeAvatar}" alt="${escapeHTML(a.name)}" class="portfolio-artist-avatar" onerror="this.onerror=null; this.src=generateInitialsAvatar('${escapeHTML(a.name)}');">
        <div class="portfolio-artist-info">
          <span class="portfolio-artist-name">${escapeHTML(a.name)}</span>
          <span class="portfolio-artist-genre">${escapeHTML(genre)}</span>
        </div>
        ${isCurrent ? '<span class="active-indicator-dot" title="Şu an aktif olan sanatçı"></span>' : ''}
      </a>
    `;
  });

  container.innerHTML = html;
  if (window.lucide) lucide.createIcons();
}

function renderFoldersBar() {
  if (!state.artist) return;
  
  const foldersBar = document.getElementById('foldersBar') || document.getElementById('publicFoldersBar');
  if (!foldersBar) return;

  const photos = state.artist.pressPhotos || [];
  const rawFolders = state.artist.folders || [];

  // Filter out duplicate default folder named 'Tüm Görseller' or 'Tüm Klasörler'
  const folders = rawFolders.filter(f => {
    const name = (f.name || '').trim().toLowerCase();
    return name !== 'tüm görseller' && name !== 'tüm klasörler';
  });

  const txtAllPhotos = typeof getTranslation === 'function' ? getTranslation('tab_all_photos', 'Tüm Görseller') : 'Tüm Görseller';
  const txtLocked = typeof getTranslation === 'function' ? getTranslation('badge_folder_locked', 'Kilitli') : 'Kilitli';
  const txtUnlocked = typeof getTranslation === 'function' ? getTranslation('badge_folder_open', 'Açık') : 'Açık';
  const txtProtected = typeof getTranslation === 'function' ? getTranslation('badge_locked_folder', 'Şifreli') : 'Şifreli';

  let html = `
    <button class="folder-pill ${state.activeFolderId === 'folder-all' ? 'active' : ''}" data-folder-id="folder-all">
      <i data-lucide="layers"></i>
      <span>${txtAllPhotos}</span>
      <span class="folder-info-count">(${photos.length})</span>
    </button>
  `;

  folders.forEach(f => {
    const fPhotos = photos.filter(p => p.folderId === f.id);
    const isLocked = f.isLocked;

    let lockBadgeHTML = '';
    let deleteBtnHTML = '';
    if (!state.isPublicView) {
      lockBadgeHTML = `
        <span class="folder-lock-btn ${isLocked ? 'locked' : 'unlocked'}" onclick="toggleFolderLockHandler(event, '${escapeHTML(f.id)}')" title="${isLocked ? 'Klasör Kilitli (Açmak İçin Tıklayın)' : 'Klasör Açık (Kilitlemek İçin Tıklayın)'}">
          <i data-lucide="${isLocked ? 'lock' : 'unlock'}" style="width:12px; height:12px;"></i>
          <span>${isLocked ? txtLocked : txtUnlocked}</span>
        </span>
      `;
      deleteBtnHTML = `
        <span class="folder-delete-btn" onclick="deleteFolderHandler(event, '${escapeHTML(f.id)}', '${escapeHTML(f.name)}')" title="Klasörü Sil">
          <i data-lucide="x"></i>
        </span>
      `;
    } else if (isLocked) {
      lockBadgeHTML = `
        <span class="folder-lock-badge locked">
          <i data-lucide="lock" style="width:12px; height:12px;"></i> ${txtProtected}
        </span>
      `;
    }

    html += `
      <button class="folder-pill ${state.activeFolderId === f.id ? 'active' : ''}" data-folder-id="${escapeHTML(f.id)}">
        <i data-lucide="${isLocked ? 'folder-lock' : 'folder'}"></i>
        <span>${escapeHTML(f.name)}</span>
        <span class="folder-info-count">(${fPhotos.length})</span>
        ${lockBadgeHTML}
        ${deleteBtnHTML}
      </button>
    `;
  });

  foldersBar.innerHTML = html;
  if (window.lucide) lucide.createIcons();

  // Show/Hide top header "Seçili Klasörü Sil" button
  const headerDelBtn = document.getElementById('btnDeleteFolderHeader');
  if (headerDelBtn) {
    if (!state.isPublicView && state.activeFolderId && state.activeFolderId !== 'folder-all') {
      headerDelBtn.style.display = 'inline-flex';
    } else {
      headerDelBtn.style.display = 'none';
    }
  }

  // Bind click handlers
  foldersBar.querySelectorAll('.folder-pill').forEach(btn => {
    btn.addEventListener('click', (e) => {
      if (e.target.closest('.folder-lock-btn') || e.target.closest('.folder-delete-btn')) return; // Ignore pill select when action buttons clicked
      const targetBtn = e.target.closest('.folder-pill');
      if (!targetBtn) return;
      state.activeFolderId = targetBtn.dataset.folderId;
      renderFoldersBar();
      renderFilteredPhotos();
    });
  });
}

async function deleteActiveFolderHandler() {
  if (!state.activeFolderId || state.activeFolderId === 'folder-all') {
    alert("Lütfen önce silmek istediğiniz özel klasörü seçiniz.");
    return;
  }
  const folder = (state.artist.folders || []).find(f => f.id === state.activeFolderId);
  const folderName = folder ? folder.name : 'Klasör';
  deleteFolderHandler(null, state.activeFolderId, folderName);
}

async function deleteFolderHandler(e, folderId, folderName) {
  if (e) e.stopPropagation();
  
  const confirmed = await showConfirm({
    title: 'Klasörü Sil',
    message: `"${folderName}" klasörünü ve içerisindeki tüm görselleri silmek istediğinize emin misiniz?\n\nBu işlem geri alınamaz!`,
    confirmText: 'Evet, Klasörü Sil',
    cancelText: 'Vazgeç',
    isDanger: true,
    icon: 'trash-2'
  });

  if (!confirmed) return;

  try {
    const res = await fetch('/api/folders/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        folderId: folderId,
        artistId: getActiveArtistId()
      })
    });

    const data = await res.json();
    if (data.status === 'success') {
      state.activeFolderId = 'folder-all';
      await loadArtistData();
      showToast(`"${folderName}" klasörü ve içerisindeki tüm görseller başarıyla silindi.`, 'success');
    } else {
      showToast(data.message || "Klasör silinemedi.", 'error');
    }
  } catch (err) {
    showToast("Sunucu hatası. Klasör silinemedi.", 'error');
  }
}

async function toggleFolderLockHandler(e, folderId) {
  if (e) e.stopPropagation();
  try {
    const res = await fetch('/api/folders/toggle-lock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        folderId: folderId,
        artistId: getActiveArtistId()
      })
    });
    const data = await res.json();
    if (data.status === 'success') {
      await loadArtistData();
    } else {
      alert(data.message || "Kilit durumu değiştirilemedi.");
    }
  } catch (err) {
    alert("Sunucu hatası.");
  }
}

function renderFilteredPhotos() {
  if (!state.artist) return;

  const galleryGrid = document.getElementById('galleryGrid') || document.getElementById('publicGalleryGrid');
  if (!galleryGrid) return;

  let photos = state.artist.pressPhotos || [];
  const folders = state.artist.folders || [];

  // Filter photos by folder
  if (state.activeFolderId === 'folder-all') {
    if (state.isPublicView) {
      const lockedFolderIds = new Set(folders.filter(f => f.isLocked).map(f => f.id));
      photos = photos.filter(p => !lockedFolderIds.has(p.folderId));
    }
  } else {
    photos = photos.filter(p => p.folderId === state.activeFolderId);
  }

  if (photos.length === 0) {
    const canDeleteThisFolder = !state.isPublicView && state.activeFolderId !== 'folder-all';
    galleryGrid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg);">
        <i data-lucide="image-off" style="width: 48px; height: 48px; color: var(--text-muted); margin-bottom: 12px;"></i>
        <h4 style="color: #fff; font-family: var(--font-display); font-size: 18px;">Bu klasörde henüz görsel bulunmuyor</h4>
        <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">Menajer tarafından yüklenen yüksek çözünürlüklü görseller burada sergilenecektir.</p>
        ${canDeleteThisFolder ? `
          <button type="button" class="btn btn-outline btn-small" onclick="deleteActiveFolderHandler()" style="margin-top:16px; border-color: rgba(239, 68, 68, 0.5); color: #ef4444;">
            <i data-lucide="trash-2"></i> Bu Boş Klasörü Sil
          </button>
        ` : ''}
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  let html = '';
  photos.forEach(p => {
    const isLockedFolder = folders.some(f => f.id === p.folderId && f.isLocked);
    
    let rawUrl = p.url || '';
    if (rawUrl && !rawUrl.startsWith('http') && !rawUrl.startsWith('/')) {
      rawUrl = '/' + rawUrl;
    }
    const safeUrl = escapeHTML(rawUrl);

    let actionButtons = '';
    if (!state.isPublicView && state.isOwner) {
      actionButtons = `
        <button type="button" class="btn btn-outline btn-sm" onclick="deletePhotoHandler('${escapeHTML(p.id)}')" title="Fotoğrafı Sil" style="border-color: rgba(239, 68, 68, 0.4); color: #EF4444;">
          <i data-lucide="trash-2"></i> Sil
        </button>
      `;
    }

    html += `
      <div class="photo-card" id="card-${escapeHTML(p.id)}">
        <div class="photo-preview-box" onclick="openPhotoLightbox('${safeUrl}', '${escapeHTML(p.title)}', '${escapeHTML(p.resolution || '3808 x 5712 px (300 DPI)')}')" style="cursor: pointer;" title="Resmi Mevcut Sayfada Büyüt">
          <img src="${safeUrl}" alt="${escapeHTML(p.title)}" class="photo-preview-img" loading="lazy">
          <span class="photo-badge">${escapeHTML(p.badge || '300 DPI')}</span>
        </div>
        <div class="photo-details" style="padding: 16px;">
          <h4 class="photo-title" style="font-family: var(--font-display); font-size: 15px; font-weight: 700; color: #fff; margin-bottom: 6px;">${escapeHTML(p.title)}</h4>
          <div style="font-size: 12px; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px; margin-bottom: 14px;">
            <span><i data-lucide="maximize-2" style="width: 12px; height: 12px;"></i> ${escapeHTML(p.resolution || '3808 x 5712 px (300 DPI)')}</span>
            <span><i data-lucide="file-check" style="width: 12px; height: 12px;"></i> Baskıya Hazır High-Res JPG</span>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <a href="${safeUrl}" download class="btn btn-spotify btn-sm" style="flex: 1; justify-content: center;">
              <i data-lucide="download"></i> 300 DPI İndir
            </a>
            ${actionButtons}
          </div>
        </div>
      </div>
    `;
  });

  galleryGrid.innerHTML = html;
  if (window.lucide) lucide.createIcons();
}

// --------------------------------------------------------------------------
// Photo Lightbox In-Page Viewer
// --------------------------------------------------------------------------
function openPhotoLightbox(url, title, resolution) {
  const modal = document.getElementById('photoLightboxModal');
  const img = document.getElementById('lightboxImg');
  const titleEl = document.getElementById('lightboxTitle');
  const resEl = document.getElementById('lightboxRes');
  const dlBtn = document.getElementById('lightboxDownloadBtn');

  if (img) img.src = url;
  if (titleEl) titleEl.innerText = title || 'Görsel Önizleme';
  if (resEl) resEl.innerText = resolution || '3808 x 5712 px (300 DPI)';
  if (dlBtn) dlBtn.href = url;

  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    if (window.lucide) lucide.createIcons();
  }
}

function closePhotoLightbox(e) {
  if (e && e.target && e.target.id === 'lightboxImg') return; // Don't close if clicking the image itself
  const modal = document.getElementById('photoLightboxModal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closePhotoLightbox();
});

// --------------------------------------------------------------------------
// Navigation & Modals Setup
// --------------------------------------------------------------------------
function getActiveArtistId() {
  const urlParams = new URLSearchParams(window.location.search);
  const paramId = urlParams.get('artistId') || urlParams.get('id');
  if (state && state.artist) {
    return state.artist.id || state.artist.slug || paramId || '';
  }
  return paramId || '';
}

window.copyArtistUrlToClipboard = async function(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }

  const activeArtistId = getActiveArtistId() || 'zuhal';
  const origin = window.location.origin;
  const shareableUrl = `${origin}/public.html?artistId=${encodeURIComponent(activeArtistId)}`;

  let copied = false;

  // Method 1: Navigator Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(shareableUrl);
      copied = true;
    } catch (err) {
      console.warn("Clipboard API writeText failed, trying execCommand fallback...", err);
    }
  }

  // Method 2: Synchronous execCommand fallback
  if (!copied) {
    try {
      const textArea = document.createElement('textarea');
      textArea.value = shareableUrl;
      textArea.style.position = 'fixed';
      textArea.style.top = '0';
      textArea.style.left = '0';
      textArea.style.width = '2em';
      textArea.style.height = '2em';
      textArea.style.padding = '0';
      textArea.style.border = 'none';
      textArea.style.outline = 'none';
      textArea.style.boxShadow = 'none';
      textArea.style.background = 'transparent';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      copied = document.execCommand('copy');
      document.body.removeChild(textArea);
    } catch (err) {
      console.warn("execCommand failed...", err);
    }
  }

  // Feedback Notification
  if (copied) {
    if (window.showToast) {
      showToast("Sanatçı Presskit Linki Panoya Kopyalandı! 📋", "success");
    } else {
      alert("Sanatçı Presskit Linki Kopyalandı:\n" + shareableUrl);
    }
  } else {
    // Method 3: Prompt fallback if browser security completely blocks clipboard
    window.prompt("Sanatçı Presskit Bağlantısı (Kopyalamak için Cmd+C / Ctrl+C basın):", shareableUrl);
  }

  // Update UI badge visual state
  const copyBtn = document.getElementById('btnCopyPageUrl') || document.querySelector('.domain-info-badge');
  if (copyBtn) {
    const copyLabel = copyBtn.querySelector('.btn-copy-label');
    if (copyLabel) {
      copyLabel.innerHTML = '<i data-lucide="check" style="width:12px; height:12px;"></i> Kopyalandı!';
      copyLabel.style.background = '#1db954';
      copyLabel.style.color = '#000000';
      if (window.lucide) lucide.createIcons();

      setTimeout(() => {
        copyLabel.innerHTML = '<i data-lucide="copy" style="width:12px; height:12px;"></i> Kopyala';
        copyLabel.style.background = '';
        copyLabel.style.color = '';
        if (window.lucide) lucide.createIcons();
      }, 2500);
    }
  }
};

function setupCopyUrlButton() {
  const copyBtn = document.getElementById('btnCopyPageUrl');
  if (copyBtn) {
    copyBtn.onclick = (e) => window.copyArtistUrlToClipboard(e);
  }
}

function setupActions() {
  setupCopyUrlButton();
}

function setupFolderModals() {
  const modal = document.getElementById('addFolderModal') || document.getElementById('newFolderModal');
  const btnOpen = document.getElementById('btnOpenAddFolderModal') || document.getElementById('btnOpenNewFolderModal');
  const btnClose = document.getElementById('btnCloseAddFolderModal') || document.getElementById('btnCloseNewFolderModal');
  const btnCancel = document.getElementById('btnCancelAddFolder') || document.getElementById('btnCancelNewFolder');
  const form = document.getElementById('addFolderForm') || document.getElementById('newFolderForm');

  if (btnOpen && modal) {
    btnOpen.onclick = (e) => {
      e.preventDefault();
      modal.classList.add('active');
    };
  }
  if (btnClose && modal) {
    btnClose.onclick = (e) => {
      e.preventDefault();
      modal.classList.remove('active');
    };
  }
  if (btnCancel && modal) {
    btnCancel.onclick = (e) => {
      e.preventDefault();
      modal.classList.remove('active');
    };
  }

  if (form && modal) {
    form.onsubmit = async (e) => {
      e.preventDefault();
      const inputName = document.getElementById('folderNameInput') || document.getElementById('inputFolderName');
      const folderName = inputName ? inputName.value.trim() : '';

      const lockEl = document.getElementById('folderLockedCheckbox') || document.getElementById('inputFolderLock');
      let isLocked = false;
      if (lockEl) {
        isLocked = (lockEl.type === 'checkbox') ? lockEl.checked : (lockEl.value === 'true');
      }

      if (!folderName) {
        alert("Lütfen bir klasör adı yazınız.");
        return;
      }

      const activeArtistId = getActiveArtistId();

      try {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) { submitBtn.disabled = true; submitBtn.innerText = 'Oluşturuluyor...'; }

        const res = await fetch('/api/folders/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            artistId: activeArtistId,
            name: folderName,
            isLocked: isLocked
          })
        });

        const data = await res.json();
        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerText = 'Klasörü Oluştur'; }

        if (data.status === 'success') {
          modal.classList.remove('active');
          if (inputName) inputName.value = '';
          await loadArtistData();
          alert('Klasör başarıyla oluşturuldu.');
        } else {
          alert(data.message || "Klasör eklenemedi.");
        }
      } catch (err) {
        alert("Sunucu hatası.");
      }
    };
  }
}

let selectedBatchFiles = [];

function setupPhotoModals() {
  const modal = document.getElementById('addPhotoModal');
  const btnOpen = document.getElementById('btnOpenAddPhotoModal');
  const btnClose = document.getElementById('btnCloseAddPhotoModal');
  const btnCancel = document.getElementById('btnCancelAddPhoto');
  const form = document.getElementById('addPhotoForm');
  const dropZone = document.getElementById('photoDropZone');
  const fileInput = document.getElementById('inputPhotoFile');
  const displayLabel = document.getElementById('photoFileNameDisplay');

  if (btnOpen && modal) {
    btnOpen.onclick = (e) => {
      e.preventDefault();
      selectedBatchFiles = [];
      if (displayLabel) displayLabel.innerText = "Fotoğrafları Sürükleyip Bırakın veya Seçin";
      const select = document.getElementById('selectTargetFolder');
      if (select && state && state.artist && state.artist.folders) {
        select.innerHTML = state.artist.folders.map(f => `<option value="${escapeHTML(f.id)}">${escapeHTML(f.name)}</option>`).join('');
      }
      modal.classList.add('active');
    };
  }

  if (btnClose && modal) btnClose.onclick = (e) => { e.preventDefault(); modal.classList.remove('active'); };
  if (btnCancel && modal) btnCancel.onclick = (e) => { e.preventDefault(); modal.classList.remove('active'); };

  // Setup Drag & Drop & File Select Listeners
  if (dropZone && fileInput) {
    dropZone.onclick = (e) => {
      if (e.target !== fileInput) fileInput.click();
    };

    const handleFiles = (files) => {
      const validFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
      if (validFiles.length > 0) {
        selectedBatchFiles = validFiles;
        const titleInput = document.getElementById('inputPhotoTitle');
        if (validFiles.length === 1) {
          if (displayLabel) displayLabel.innerText = `📄 ${validFiles[0].name} (${(validFiles[0].size / (1024 * 1024)).toFixed(1)} MB)`;
          if (titleInput && (!titleInput.value || titleInput.value === 'Fotoğraf Paketi')) {
            titleInput.value = validFiles[0].name.split('.')[0].replace(/[-_]/g, ' ');
          }
        } else {
          if (displayLabel) displayLabel.innerText = `📷 ${validFiles.length} Adet Fotoğraf Seçildi`;
          if (titleInput && !titleInput.value) {
            titleInput.value = `Görsel Paketi (${validFiles.length} adet)`;
          }
        }
      }
    };

    fileInput.onchange = (e) => handleFiles(e.target.files);

    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('dragover');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragover');
      }, false);
    });

    dropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files) {
        handleFiles(dt.files);
      }
    }, false);
  }

  if (form && modal) {
    form.onsubmit = async (e) => {
      e.preventDefault();
      const selectEl = document.getElementById('selectTargetFolder');
      const folderId = selectEl ? selectEl.value : '';
      const titleEl = document.getElementById('inputPhotoTitle');
      const baseTitle = (titleEl && titleEl.value.trim()) ? titleEl.value.trim() : 'Görsel';
      const resEl = document.getElementById('inputPhotoRes');
      const resVal = (resEl && resEl.value.trim()) ? resEl.value.trim() : '3808 x 5712 px (300 DPI)';
      const badgeEl = document.getElementById('inputPhotoBadge');
      const badge = (badgeEl && badgeEl.value.trim()) ? badgeEl.value.trim() : 'Yeni Görsel';

      if (!folderId) {
        alert("Lütfen bir hedef klasör seçin.");
        return;
      }

      const activeArtistId = getActiveArtistId();
      const submitBtn = form.querySelector('button[type="submit"]');

      try {
        if (submitBtn) submitBtn.disabled = true;

        if (selectedBatchFiles.length === 0) {
          // Single fallback upload if no custom file selected
          const photoUrl = (typeof uploadedPhotoDataUrl !== 'undefined' && uploadedPhotoDataUrl) ? uploadedPhotoDataUrl : '/assets/images/yagmur-hizal/Kort1 2.JPG';
          if (submitBtn) submitBtn.innerText = 'Fotoğraf Ekleniyor...';

          const res = await fetch('/api/photos/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              artistId: activeArtistId,
              folderId: folderId,
              title: baseTitle,
              url: photoUrl,
              resolution: resVal,
              badge: badge
            })
          });
          const data = await res.json();
          if (submitBtn) submitBtn.disabled = false;
          if (data.status === 'success') {
            modal.classList.remove('active');
            form.reset();
            selectedBatchFiles = [];
            await loadArtistData();
            alert('Fotoğraf klasöre başarıyla eklendi.');
          } else {
            alert(data.message || "Fotoğraf eklenemedi.");
          }
        } else {
          // BATCH MULTIPLE FILE UPLOAD
          let successCount = 0;
          const totalFiles = selectedBatchFiles.length;

          for (let i = 0; i < totalFiles; i++) {
            const file = selectedBatchFiles[i];
            if (submitBtn) submitBtn.innerText = `Yükleniyor (${i + 1}/${totalFiles})...`;

            const base64Url = await new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onload = (event) => resolve(event.target.result);
              reader.onerror = (error) => reject(error);
              reader.readAsDataURL(file);
            });

            const photoTitle = (totalFiles === 1) ? baseTitle : `${baseTitle} - ${file.name.split('.')[0].replace(/[-_]/g, ' ')}`;

            const res = await fetch('/api/photos/add', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                artistId: activeArtistId,
                folderId: folderId,
                title: photoTitle,
                url: base64Url,
                resolution: resVal,
                badge: badge
              })
            });

            const data = await res.json();
            if (data.status === 'success') {
              successCount++;
            }
          }

          if (submitBtn) { submitBtn.disabled = false; submitBtn.innerText = 'Fotoğrafları Ekle'; }

          if (successCount > 0) {
            modal.classList.remove('active');
            form.reset();
            selectedBatchFiles = [];
            if (displayLabel) displayLabel.innerText = "Fotoğrafları Sürükleyip Bırakın veya Seçin";
            await loadArtistData();
            alert(`${successCount} adet fotoğraf klasöre başarıyla yüklendi.`);
          } else {
            alert("Fotoğraflar yüklenemedi.");
          }
        }
      } catch (err) {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerText = 'Fotoğrafları Ekle'; }
        alert("Yükleme sırasında hata oluştu.");
      }
    };
  }
}

// Handler for photo deletion
async function deletePhotoHandler(photoId) {
  const confirmed = await showConfirm({
    title: 'Fotoğrafı Sil',
    message: 'Bu fotoğrafı depodan kalıcı olarak silmek istediğinize emin misiniz?',
    confirmText: 'Evet, Sil',
    cancelText: 'Vazgeç',
    isDanger: true,
    icon: 'trash-2'
  });

  if (!confirmed) return;

  try {
    const activeArtistId = getActiveArtistId();
    const res = await fetch('/api/photos/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        photoId: photoId,
        artistId: activeArtistId
      })
    });

    const data = await res.json();
    if (data.status === 'success') {
      await loadArtistData();
      showToast("Fotoğraf başarıyla silindi.", 'success');
    } else {
      showToast(data.message || "Fotoğraf silinemedi.", 'error');
    }
  } catch (err) {
    showToast("İşlem gerçekleştirilemedi.", 'error');
  }
}

// Re-render UI components on language change
window.addEventListener('languageChanged', (e) => {
  if (state && state.artist) {
    if (typeof renderLogos === 'function') renderLogos();
    if (typeof renderPlatformLinks === 'function') renderPlatformLinks();
    if (typeof renderFoldersBar === 'function') renderFoldersBar();
    if (typeof renderGalleryPhotos === 'function') renderGalleryPhotos();
    if (typeof renderSidebarPortfolio === 'function') renderSidebarPortfolio();
  }
});
