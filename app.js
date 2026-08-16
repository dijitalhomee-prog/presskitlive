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

// --------------------------------------------------------------------------
// Initialization & Data Loading
// --------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  state.isPublicView = document.body.dataset.view === 'public' || window.location.pathname.includes('public.html');
  
  await checkImpersonationStatus();
  await loadArtistData();
  setupNavigation();
  setupActions();
  setupFolderModals();
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
          state.artist = paramArtistId ? (state.myArtists.find(a => a.id === paramArtistId) || state.myArtists[0]) : state.myArtists[0];
          state.isOwner = true;
        }
      }
      
      // Fallback if specific artistId requested in URL
      if (!state.artist && paramArtistId) {
        const fallbackRes = await fetch(`/api/artist?artistId=${encodeURIComponent(paramArtistId)}`);
        if (fallbackRes.ok) {
          const fallJson = await fallbackRes.json();
          if (fallJson.artist) {
            state.artist = fallJson.artist;
            state.isOwner = fallJson.isOwner || false;
          }
        }
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
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
}

function renderArtistHeader() {
  if (!state.artist) return;

  const name = state.artist.name || 'Profil Adı';

  const titleEl = document.getElementById('artistTitleName');
  if (titleEl) titleEl.innerText = name;

  const genreEl = document.getElementById('artistGenreText');
  if (genreEl) genreEl.innerText = state.artist.genre || 'Sanatçı / Oyuncu Portföyü';

  const avatarEl = document.getElementById('heroAvatar') || document.getElementById('artistAvatarImg');
  if (avatarEl) {
    if (state.artist.avatar) {
      const rawAv = state.artist.avatar;
      avatarEl.src = (rawAv.startsWith('http') || rawAv.startsWith('/') || rawAv.startsWith('data:')) ? rawAv : '/' + rawAv;
    } else {
      avatarEl.src = generateInitialsAvatar(name);
    }
  }

  const breadcrumbEl = document.getElementById('breadcrumbArtist');
  if (breadcrumbEl) breadcrumbEl.innerText = name;

  const slugBadgeEl = document.getElementById('artistSlugBadge');
  if (slugBadgeEl) slugBadgeEl.innerText = state.artist.id || 'profil';

  const heroBg = document.getElementById('heroBg');
  if (heroBg) {
    if (state.artist.banner) {
      const rawBg = state.artist.banner;
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

  // Dynamically update Socials & Platform links
  const socials = state.artist.socials || {};
  
  const linkInsta = document.getElementById('linkInstagram');
  if (linkInsta) {
    if (socials.instagram) {
      linkInsta.href = socials.instagram;
      const handle = socials.instagram.replace(/\/$/, '').split('/').pop();
      const sub = linkInsta.querySelector('.platform-sub');
      if (sub) sub.innerText = handle ? '@' + handle : 'Instagram';
      linkInsta.style.display = 'flex';
    } else {
      linkInsta.style.display = 'none';
    }
  }

  const linkSpot = document.getElementById('linkSpotify');
  if (linkSpot) {
    if (socials.spotify) {
      linkSpot.href = socials.spotify;
      linkSpot.style.display = 'flex';
    } else {
      linkSpot.style.display = 'none';
    }
  }

  const linkYt = document.getElementById('linkYoutube');
  if (linkYt) {
    if (socials.youtube) {
      linkYt.href = socials.youtube;
      linkYt.style.display = 'flex';
    } else {
      linkYt.style.display = 'none';
    }
  }

  const linkDeezer = document.getElementById('linkDeezer');
  if (linkDeezer) {
    if (socials.deezer) {
      linkDeezer.href = socials.deezer;
      linkDeezer.style.display = 'flex';
    } else {
      linkDeezer.style.display = 'none';
    }
  }
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

  const mailLink = document.getElementById('gridEmailLink');
  if (mailLink && mgr.email) mailLink.href = `mailto:${mgr.email}`;
}

function renderFoldersBar() {
  if (!state.artist) return;
  
  const foldersBar = document.getElementById('foldersBar') || document.getElementById('publicFoldersBar');
  if (!foldersBar) return;

  const photos = state.artist.pressPhotos || [];
  const folders = state.artist.folders || [];

  let html = `
    <button class="folder-pill ${state.activeFolderId === 'folder-all' ? 'active' : ''}" data-folder-id="folder-all">
      <i data-lucide="layers"></i>
      <span>Tüm Görseller</span>
      <span class="folder-info-count">(${photos.length})</span>
    </button>
  `;

  folders.forEach(f => {
    const fPhotos = photos.filter(p => p.folderId === f.id);
    const isLocked = f.isLocked;

    // Public view lock badge indicator
    let lockBadgeHTML = '';
    if (isLocked) {
      if (!state.isPublicView && state.isOwner) {
        lockBadgeHTML = `
          <span class="folder-lock-badge locked" title="Klasör Şifreli / Kilitli">
            <i data-lucide="lock" style="width:12px; height:12px;"></i> Kilitli
          </span>
        `;
      } else {
        lockBadgeHTML = `
          <span class="folder-lock-badge locked">
            <i data-lucide="lock" style="width:12px; height:12px;"></i> Şifreli
          </span>
        `;
      }
    }

    html += `
      <button class="folder-pill ${state.activeFolderId === f.id ? 'active' : ''}" data-folder-id="${escapeHTML(f.id)}">
        <i data-lucide="${isLocked ? 'folder-lock' : 'folder'}"></i>
        <span>${escapeHTML(f.name)}</span>
        <span class="folder-info-count">(${fPhotos.length})</span>
        ${lockBadgeHTML}
      </button>
    `;
  });

  foldersBar.innerHTML = html;
  if (window.lucide) lucide.createIcons();

  // Bind click handlers
  foldersBar.querySelectorAll('.folder-pill').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const targetBtn = e.target.closest('.folder-pill');
      if (!targetBtn) return;
      state.activeFolderId = targetBtn.dataset.folderId;
      renderFoldersBar();
      renderFilteredPhotos();
    });
  });
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
    galleryGrid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg);">
        <i data-lucide="image-off" style="width: 48px; height: 48px; color: var(--text-muted); margin-bottom: 12px;"></i>
        <h4 style="color: #fff; font-family: var(--font-display); font-size: 18px;">Bu klasörde henüz görsel bulunmuyor</h4>
        <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">Menajer tarafından yüklenen yüksek çözünürlüklü görseller burada sergilenecektir.</p>
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
        <div class="photo-preview-box" onclick="window.open('${safeUrl}', '_blank')">
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
// Navigation & Modals Setup
// --------------------------------------------------------------------------
function setupNavigation() {}

function setupActions() {}

function setupFolderModals() {
  const modal = document.getElementById('addFolderModal');
  const btnOpen = document.getElementById('btnOpenAddFolderModal');
  const btnClose = document.getElementById('btnCloseAddFolderModal');
  const btnCancel = document.getElementById('btnCancelAddFolder');
  const form = document.getElementById('addFolderForm');

  if (btnOpen && modal) {
    btnOpen.addEventListener('click', () => modal.classList.add('active'));
  }
  if (btnClose && modal) {
    btnClose.addEventListener('click', () => modal.classList.remove('active'));
  }
  if (btnCancel && modal) {
    btnCancel.addEventListener('click', () => modal.classList.remove('active'));
  }

  if (form && modal) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const folderName = document.getElementById('folderNameInput').value.trim();
      const isLocked = document.getElementById('folderLockedCheckbox').checked;

      if (!folderName) return;

      try {
        const res = await fetch('/api/folders/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            artistId: state.artist.id,
            name: folderName,
            isLocked: isLocked
          })
        });

        const data = await res.json();
        if (data.status === 'success') {
          modal.classList.remove('active');
          form.reset();
          await loadArtistData();
        } else if (res.status === 403) {
          alert("Bu sanatçı üzerinde klasör oluşturma yetkiniz bulunmamaktadır.");
        } else {
          alert(data.message || "Klasör eklenemedi.");
        }
      } catch (err) {
        alert("Sunucu hatası.");
      }
    });
  }
}

// Handler for photo deletion
async function deletePhotoHandler(photoId) {
  if (!confirm("Bu fotoğrafı silmek istediğinize emin misiniz?")) return;

  try {
    const res = await fetch('/api/photos/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        photoId: photoId,
        artistId: state.artist.id
      })
    });

    const data = await res.json();
    if (data.status === 'success') {
      await loadArtistData();
    } else if (res.status === 403) {
      alert("Bu fotoğrafı silme yetkiniz bulunmamaktadır.");
    } else {
      alert(data.message || "Fotoğraf silinemedi.");
    }
  } catch (err) {
    alert("İşlem gerçekleştirilemedi.");
  }
}
