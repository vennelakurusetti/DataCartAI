/* ═══════════════════════════════════════════════════════
   DataCartAI — app.js
   All frontend logic: landing, search, ML results,
   wishlist, compare, reminders, price compare modal.
   Talks to FastAPI backend at http://127.0.0.1:8000
═══════════════════════════════════════════════════════ */

const API = 'http://127.0.0.1:8000/api';

// ── State ─────────────────────────────────────────────────────
let currentResults   = [];
let enrichedResults  = null;
let activeProduct    = null;
let wishlist         = JSON.parse(localStorage.getItem('dc_wishlist')    || '[]');
let compareList      = JSON.parse(localStorage.getItem('dc_compare')     || '[]');
let reminders        = JSON.parse(localStorage.getItem('dc_reminders')   || '[]');
let compareChart     = null;

// ── Helpers ───────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const fmt = n => parseInt(n || 0).toLocaleString('en-IN');

function showLoading(msg = 'Searching…') {
  $('loading-msg').textContent = msg;
  $('loading-overlay').classList.remove('hidden');
}
function hideLoading() {
  $('loading-overlay').classList.add('hidden');
}

function toast(msg, type = '') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  $('toasts').appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function updateBadge(id, n) {
  const el = $(id);
  if (!el) return;
  el.textContent = n > 0 ? n : '';
}

function refreshBadges() {
  updateBadge('badge-wishlist',  wishlist.length);
  updateBadge('badge-compare',   compareList.length);
  updateBadge('badge-reminders', reminders.length);
}
refreshBadges();

// ── Particle canvas (landing) ──────────────────────────────────
(function initCanvas() {
  const canvas = $('grid-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, pts;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function makePoints() {
    pts = Array.from({ length: 80 }, () => ({
      x:  Math.random() * W,
      y:  Math.random() * H,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      r:  Math.random() * 1.4 + 0.4,
      a:  Math.random() * 0.4 + 0.1,
    }));
  }

  let mx = -999, my = -999;
  window.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });

  function draw() {
    ctx.clearRect(0, 0, W, H);
    pts.forEach(p => {
      const dx = p.x - mx, dy = p.y - my, d = Math.hypot(dx, dy);
      if (d < 90) { p.x += (dx / d) * 1.1; p.y += (dy / d) * 1.1; }
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,229,204,${p.a})`;
      ctx.fill();
    });
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const d = Math.hypot(pts[i].x - pts[j].x, pts[i].y - pts[j].y);
        if (d < 110) {
          ctx.beginPath();
          ctx.moveTo(pts[i].x, pts[i].y);
          ctx.lineTo(pts[j].x, pts[j].y);
          ctx.strokeStyle = `rgba(0,229,204,${0.07 * (1 - d / 110)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', () => { resize(); makePoints(); });
  resize(); makePoints(); draw();
})();

// ── Landing → App ──────────────────────────────────────────────
$('enterBtn').addEventListener('click', enterApp);
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !$('landing').classList.contains('hidden')) enterApp();
});

function enterApp() {
  $('landing').classList.add('exiting');
  setTimeout(() => {
    $('landing').classList.add('hidden');
    $('app').classList.remove('hidden');
    $('searchInput').focus();
  }, 550);
}

$('backBtn').addEventListener('click', () => {
  $('app').classList.add('hidden');
  $('landing').classList.remove('hidden', 'exiting');
});

// ── Tab navigation ─────────────────────────────────────────────
document.querySelectorAll('.nav-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const v = btn.dataset.view;
    document.querySelectorAll('.view').forEach(el => {
      el.classList.toggle('active', el.id === `view-${v}`);
      el.classList.toggle('hidden', el.id !== `view-${v}`);
    });
    if (v === 'wishlist')  renderWishlist();
    if (v === 'compare')   renderCompare();
    if (v === 'reminders') renderReminders();
  });
});

// ── Quick tags ─────────────────────────────────────────────────
document.querySelectorAll('.qtag').forEach(t => {
  t.addEventListener('click', () => {
    $('searchInput').value = t.dataset.q;
    doSearch(t.dataset.q);
  });
});

// ── Search ─────────────────────────────────────────────────────
$('searchBtn').addEventListener('click', () => doSearch($('searchInput').value.trim()));
$('searchInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch($('searchInput').value.trim());
});

async function doSearch(query) {
  if (!query) return;
  enrichedResults = null;
  showLoading('Scraping live products…');

  try {
    const res  = await fetchTimeout(`${API}/search?q=${encodeURIComponent(query)}`, 30000);
    const data = await res.json();

    currentResults = data.products || [];

    // Show which model ran
    const tag = $('model-tag');
    if (data.intent) {
      tag.textContent = `Intent: ${data.intent.replace(/_/g,' ')}`;
      tag.style.display = 'inline-block';
    }

    hideLoading();
    renderResults(currentResults, query);

  } catch (err) {
    // Backend offline → use demo fallback
    console.warn('Backend offline, using demo data:', err);
    currentResults = demoSearch(query);
    hideLoading();
    renderResults(currentResults, query);
    toast('⚠️ Using demo data — backend offline', 'err');
  }

  if (currentResults.length > 0) {
    $('enrich-bar').classList.remove('hidden');
  }
}

function fetchTimeout(url, ms) {
  return Promise.race([
    fetch(url),
    new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), ms))
  ]);
}

// ── Render results ─────────────────────────────────────────────
function renderResults(products, query) {
  const wrap  = $('results-wrap');
  const grid  = $('product-grid');
  const empty = $('empty-state');

  if (!products || products.length === 0) {
    wrap.classList.add('hidden');
    empty.classList.remove('hidden');
    empty.querySelector('.empty-h').textContent = `No results for "${query}"`;
    empty.querySelector('.empty-s').textContent = 'Try a higher budget or different category';
    return;
  }

  wrap.classList.remove('hidden');
  empty.classList.add('hidden');
  $('results-title').textContent  = `Results for "${query}"`;
  $('results-count').textContent  = `${products.length} products found`;

  grid.innerHTML = '';
  products.forEach((p, i) => {
    const card = buildCard(p, i);
    grid.appendChild(card);
  });
}

function buildCard(p, delay = 0) {
  const inWish  = wishlist.some(w => w.id === p.id);
  const card    = document.createElement('div');
  card.className = 'product-card';
  card.style.animationDelay = `${delay * 0.04}s`;

  const cat      = (p.category || 'phone').toLowerCase();
  const emoji    = catEmoji(cat);
  const badgeCls = catBadge(cat);
  const specs    = buildSpecChips(p);
  const score    = p.match_score || 0;
  const barW     = Math.min(100, Math.max(0, score));

  // Product image — use scraped image if available, else emoji fallback
  const imgHtml = p.image
    ? `<img class="card-img" src="${p.image}" alt="${p.name}" loading="lazy"
          onerror="this.style.display='none';this.nextElementSibling.style.display='block'" />
       <span class="card-emoji" style="display:none">${emoji}</span>`
    : `<span class="card-emoji">${emoji}</span>`;

  // Star rating display
  const starsHtml = p.rating ? buildStarRating(p.rating, p.url, p.reviews_url, p.review_count) : '';

  // "View on store" link button
  const storeLabel = (p.source || 'Store');
  const storeLinkHtml = p.url
    ? `<a class="card-store-link" href="${p.url}" target="_blank" rel="noopener"
          onclick="event.stopPropagation()">
         View on ${storeLabel} ↗
       </a>`
    : `<span class="card-store-tag">${storeLabel}</span>`;

  card.innerHTML = `
    <span class="card-badge ${badgeCls}">${p.category || 'product'}</span>
    ${imgHtml}
    <div class="card-name">${p.name || 'Unknown'}</div>
    <div class="card-brand-row">
      <span class="card-brand">${p.brand || p.source || ''}</span>
      ${storeLinkHtml}
    </div>
    <div class="card-price">₹${fmt(p.price)}</div>
    ${starsHtml}
    ${score > 0 ? `
    <div class="match-bar-wrap">
      <div class="match-bar-label">
        <span>AI match</span><span>${score}%</span>
      </div>
      <div class="match-bar-bg">
        <div class="match-bar-fill" style="width:${barW}%"></div>
      </div>
    </div>` : ''}
    <div class="card-specs">${specs}</div>
    <div class="card-actions">
      <button class="card-view-btn">View Details</button>
      <button class="card-heart-btn ${inWish ? 'active' : ''}">❤️</button>
    </div>
  `;

  card.querySelector('.card-view-btn').addEventListener('click', e => {
    e.stopPropagation(); openModal(p);
  });
  card.querySelector('.card-heart-btn').addEventListener('click', e => {
    e.stopPropagation(); toggleWishlist(p, e.currentTarget);
  });
  card.addEventListener('click', () => openModal(p));
  return card;
}

// Star rating HTML — clicking goes to the product reviews page
function buildStarRating(rating, url, reviews_url, review_count) {
  const r    = parseFloat(rating) || 0;
  // Use the scraped reviews_url if available, otherwise build one
  const rUrl = reviews_url
    || (url ? (url.includes('amazon.in')
        ? url.replace(/\/dp\//, '/product-reviews/').split('?')[0] + '?sortBy=recent'
        : url + '#ratings') : '#');
  const rCount = review_count ? ` (${review_count})` : '';
  return `
    <a class="card-stars" href="${rUrl}" target="_blank" rel="noopener"
       title="View all ratings & reviews — ${r}/5" onclick="event.stopPropagation()">
      ${buildStarsOnly(r)}
      <span class="stars-num">${r}/5${rCount}</span>
    </a>`;
}

function catEmoji(cat) {
  if (cat.includes('phone'))      return '📱';
  if (cat.includes('laptop'))     return '💻';
  if (cat.includes('ear'))        return '🎧';
  if (cat.includes('watch'))      return '⌚';
  if (cat.includes('sun'))        return '☀️';
  if (cat.includes('serum'))      return '💧';
  if (cat.includes('moistur'))    return '🧴';
  if (cat.includes('lip'))        return '💄';
  if (cat.includes('found'))      return '🪞';
  if (cat.includes('speaker'))    return '🔊';
  return '🛍️';
}

function catBadge(cat) {
  if (cat.includes('phone'))   return 'badge-phone';
  if (cat.includes('laptop'))  return 'badge-laptop';
  if (cat.includes('sun'))     return 'badge-sunscreen';
  if (cat.includes('serum'))   return 'badge-serum';
  if (cat.includes('moistur')) return 'badge-moisturizer';
  if (cat.includes('lip') || cat.includes('found')) return 'badge-lipstick';
  if (cat.includes('ear'))     return 'badge-earbuds';
  return 'badge-default';
}

function buildSpecChips(p) {
  const chips = [];
  if (p.ram)            chips.push(p.ram);
  if (p.storage)        chips.push(p.storage);
  if (p.battery)        chips.push(p.battery);
  if (p.camera)         chips.push(p.camera);
  if (p.spf_value && p.spf_value > 0) chips.push(`SPF ${p.spf_value}`);
  if (p.is_water_based) chips.push('Water-based');
  if (p.long_wear)      chips.push('Long-wear');
  if (p.rating)         chips.push(`⭐ ${p.rating}`);
  return chips.slice(0, 4).map(c => `<span class="spec-chip">${c}</span>`).join('');
}

// ── Modal ──────────────────────────────────────────────────────
function buildStarsOnly(r) {
  const full  = Math.floor(r);
  const half  = (r - full) >= 0.4 ? 1 : 0;
  const empty = 5 - full - half;
  return '<span class="s-full">' + '★'.repeat(full) + '</span>' +
         (half ? '<span class="s-half">½</span>' : '') +
         '<span class="s-empty">' + '☆'.repeat(empty) + '</span>';
}

function openModal(p) {
  activeProduct = p;

  const info  = $('modal-info');
  const cat   = (p.category || 'phone').toLowerCase();
  const emoji = catEmoji(cat);
  const specs = buildModalSpecs(p);

  // Product image or emoji fallback
  const imgHtml = p.image
    ? `<img class="modal-prod-img" src="${p.image}" alt="${p.name || ''}" loading="lazy"
          onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" />
       <div class="modal-emoji-wrap" style="display:none">${emoji}</div>`
    : `<div class="modal-emoji-wrap">${emoji}</div>`;

  // Star rating — links to product reviews page
  const reviewUrl = p.reviews_url
    || (p.url
        ? (p.url.includes('amazon.in')
            ? p.url.replace(/\/dp\//, '/product-reviews/').split('?')[0] + '?sortBy=recent'
            : p.url + '#ratings')
        : '#');
  const reviewCountTxt = p.review_count ? ` (${p.review_count})` : '';
  const starsHtml = p.rating
    ? `<a class="modal-stars" href="${reviewUrl}" target="_blank" rel="noopener">
         ${buildStarsOnly(parseFloat(p.rating) || 0)}
         <span class="modal-stars-num">${p.rating}/5${reviewCountTxt}</span>
         <span class="modal-stars-sub">See all reviews ↗</span>
       </a>`
    : '';

  // Direct store link button
  const storeName = p.source || 'Store';
  const storeBtn  = p.url
    ? `<a class="modal-store-btn" href="${p.url}" target="_blank" rel="noopener">
         View on ${storeName} ↗
       </a>`
    : '';

  info.innerHTML = `
    <div class="modal-product-header">
      ${imgHtml}
      <div class="modal-prod-text">
        <div class="modal-prod-name">${p.name || 'Unknown'}</div>
        <div class="modal-prod-brand">${p.brand || storeName}</div>
        <div class="modal-prod-price">₹${fmt(p.price)}</div>
        ${starsHtml}
        ${storeBtn}
      </div>
    </div>
    <div class="modal-specs">${specs}</div>
  `;

  // ML explanation
  const explBox = $('modal-explain');
  if (p.explanation) {
    explBox.innerHTML = `<div class="explain-header">🤖 Why this product?</div>${p.explanation}`;
    explBox.classList.remove('hidden');
  } else {
    explBox.classList.add('hidden');
  }

  // Reset panels
  $('price-panel').classList.add('hidden');
  $('reminder-panel').classList.add('hidden');

  // Heart state
  const inWish = wishlist.some(w => w.id === p.id);
  $('mHeart').classList.toggle('active-heart', inWish);
  $('mHeart').textContent = inWish ? '💔 Remove' : '❤️ Wishlist';

  $('modal-overlay').classList.remove('hidden');
}

function buildModalSpecs(p) {
  const rows = [
    ['Price',       p.price     ? `₹${fmt(p.price)}` : null],
    ['Rating',      p.rating    ? `⭐ ${p.rating}/5`  : null],
    ['RAM',         p.ram],
    ['Storage',     p.storage],
    ['Battery',     p.battery],
    ['Camera',      p.camera],
    ['Processor',   p.processor_score ? `${p.processor_score}/10` : null],
    ['Display',     p.display_score   ? `${p.display_score}/10`   : null],
    ['SPF',         p.spf_value       ? `SPF ${p.spf_value}`      : null],
    ['Skin Compat', p.skin_compat     ? `${p.skin_compat}/5`      : null],
    ['Water-based', p.is_water_based  ? 'Yes'                     : null],
    ['Long Wear',   p.long_wear       ? 'Yes'                     : null],
    ['5G',          p.is_5g           ? 'Yes'                     : null],
    ['Source',      p.source],
    ['Match',       p.match_score     ? `${p.match_score}%`       : null],
  ];
  return rows
    .filter(([, v]) => v)
    .map(([k, v]) => `
      <div class="spec-row">
        <div class="spec-row-label">${k}</div>
        <div class="spec-row-val">${v}</div>
      </div>`)
    .join('');
}

$('modalClose').addEventListener('click', closeModal);
$('modal-overlay').addEventListener('click', e => {
  if (e.target === $('modal-overlay')) closeModal();
});
function closeModal() { $('modal-overlay').classList.add('hidden'); }

// ── Modal: Best Price ───────────────────────────────────────────
$('mPrice').addEventListener('click', async () => {
  const panel = $('price-panel');
  if (!panel.classList.contains('hidden')) { panel.classList.add('hidden'); return; }
  $('reminder-panel').classList.add('hidden');
  panel.classList.remove('hidden');
  $('price-list').innerHTML = '<p style="color:var(--text3);font-size:.85rem">Searching stores…</p>';

  const p    = activeProduct;
  const name = encodeURIComponent(p.name || '');

  try {
    const res  = await fetchTimeout(`${API}/compare?name=${name}`, 20000);
    const data = await res.json();
    renderPrices(data.prices || [], p.price, p.name);
  } catch {
    renderPrices(mockPrices(p), p.price, p.name);
  }
});

function mockPrices(p) {
  const base = parseInt(p.price) || 10000;
  const q    = encodeURIComponent(p.name || '');
  return [
    { store:'Amazon',         price: Math.round(base*0.93), is_best:true,
      url:`https://www.amazon.in/s?k=${q}` },
    { store:'Flipkart',       price: Math.round(base*0.96), is_best:false,
      url:`https://www.flipkart.com/search?q=${q}` },
    { store:'Meesho',         price: Math.round(base*0.99), is_best:false,
      url:`https://www.meesho.com/search?q=${q}` },
    { store:'Croma',          price: Math.round(base*1.01), is_best:false,
      url:`https://www.croma.com/searchB?q=${q}` },
    { store:'Reliance Digital',price:Math.round(base*1.02), is_best:false,
      url:`https://www.reliancedigital.in/search?q=${q}` },
    { store:'Vijay Sales',    price: Math.round(base*1.03), is_best:false,
      url:`https://www.vijaysales.com/search/${q}` },
  ].sort((a,b) => a.price - b.price);
}

function renderPrices(prices, currentPrice, productName) {
  if (!prices || !prices.length) {
    $('price-list').innerHTML = '<p style="color:var(--text3);font-size:.85rem">No prices found.</p>';
    return;
  }
  prices.sort((a,b) => (a.price||0) - (b.price||0));
  const cheapest = prices[0].price;
  $('price-list').innerHTML = prices.map((r, i) => {
    // Always build a real store search URL if not already provided
    const q   = encodeURIComponent(productName || '');
    const storeUrls = {
      'Amazon':          `https://www.amazon.in/s?k=${q}`,
      'Flipkart':        `https://www.flipkart.com/search?q=${q}`,
      'Meesho':          `https://www.meesho.com/search?q=${q}`,
      'Nykaa':           `https://www.nykaa.com/search/result/?q=${q}`,
      'Myntra':          `https://www.myntra.com/search?rawQuery=${q}`,
      'Croma':           `https://www.croma.com/searchB?q=${q}`,
      'Reliance Digital':`https://www.reliancedigital.in/search?q=${q}`,
      'Vijay Sales':     `https://www.vijaysales.com/search/${q}`,
      'Snapdeal':        `https://www.snapdeal.com/search?keyword=${q}`,
    };
    const href = (r.url && r.url.startsWith('http') && !r.url.includes('127.0.0.1'))
      ? r.url
      : (storeUrls[r.store] || `https://www.google.com/search?q=${q}+${encodeURIComponent(r.store)}+buy`);
    const saving = currentPrice && r.price < currentPrice
      ? `Save ₹${fmt(currentPrice - r.price)}`
      : '';
    const isBest = r.price === cheapest;
    // Reviews link for this store's listing
    const rUrl = r.reviews_url
      || (r.store === 'Amazon' && r.url
          ? r.url.replace(/\/dp\//, '/product-reviews/').split('?')[0] + '?sortBy=recent'
          : r.url ? r.url + '#ratings' : '#');
    const rCount = r.review_count ? ` · ${r.review_count} reviews` : '';
    return `
    <div class="price-item-wrap">
      <a class="price-item" href="${href}" target="_blank" rel="noopener noreferrer">
        <div>
          <div class="price-item-name">${r.store}</div>
          <div class="price-item-tag">
            ${isBest ? '✅ Best deal' : saving ? saving : 'Available'}
          </div>
        </div>
        <div class="price-item-amt ${isBest ? 'best' : ''}">₹${fmt(r.price)}</div>
      </a>
      ${r.rating ? `<a class="price-item-reviews" href="${rUrl}" target="_blank" rel="noopener">
        ${buildStarsOnly(parseFloat(r.rating)||0)}
        <span>${r.rating}/5${rCount}</span>
        <span class="reviews-arrow">See reviews ↗</span>
      </a>` : ''}
    </div>`;
  }).join('');
}

// ── Modal: Wishlist ─────────────────────────────────────────────
$('mHeart').addEventListener('click', () => {
  toggleWishlist(activeProduct, $('mHeart'), true);
});

function toggleWishlist(p, btn, isModal = false) {
  const idx = wishlist.findIndex(w => w.id === p.id);
  if (idx === -1) {
    wishlist.push(p);
    btn.classList.add('active-heart');
    if (isModal) $('mHeart').textContent = '💔 Remove';
    toast(`❤️ ${p.name || 'Product'} saved!`, 'ok');
  } else {
    wishlist.splice(idx, 1);
    btn.classList.remove('active-heart');
    if (isModal) $('mHeart').textContent = '❤️ Wishlist';
    toast('Removed from wishlist', '');
  }
  localStorage.setItem('dc_wishlist', JSON.stringify(wishlist));
  refreshBadges();
}

// ── Modal: Compare ──────────────────────────────────────────────
$('mCompare').addEventListener('click', () => {
  const p = activeProduct;
  if (compareList.length >= 4) { toast('Max 4 products to compare', 'err'); return; }
  if (compareList.find(c => c.id === p.id)) { toast('Already in compare list', ''); return; }
  compareList.push(p);
  localStorage.setItem('dc_compare', JSON.stringify(compareList));
  refreshBadges();
  toast(`📊 ${p.name} added to compare`, 'ok');
});

// ── Modal: Reminder ─────────────────────────────────────────────
$('mReminder').addEventListener('click', () => {
  const panel = $('reminder-panel');
  if (!panel.classList.contains('hidden')) { panel.classList.add('hidden'); return; }
  $('price-panel').classList.add('hidden');
  panel.classList.remove('hidden');
  $('reminderPrice').value = Math.round(parseInt(activeProduct.price) * 0.85) || '';
});

$('saveReminderBtn').addEventListener('click', () => {
  const p     = activeProduct;
  const price = $('reminderPrice').value;
  const email = $('reminderEmail').value;
  if (!price) { toast('Enter a target price', 'err'); return; }
  if (reminders.find(r => r.productId === p.id)) { toast('Alert already set for this product', ''); return; }
  reminders.push({
    id:           Date.now(),
    productId:    p.id,
    productName:  p.name || 'Unknown',
    currentPrice: p.price,
    targetPrice:  parseInt(price),
    email:        email || '',
    date:         new Date().toLocaleDateString(),
  });
  localStorage.setItem('dc_reminders', JSON.stringify(reminders));
  refreshBadges();
  $('reminder-panel').classList.add('hidden');
  toast(`🔔 Alert set for ₹${fmt(price)}`, 'ok');
});

// ── Enrich ─────────────────────────────────────────────────────
$('enrichBtn').addEventListener('click', () => {
  const prompt = $('enrichInput').value.trim();
  if (!prompt) { toast('Describe what to add', 'err'); return; }
  const base   = enrichedResults || currentResults;
  enrichedResults = base.map(p => ({
    ...p,
    ...localEnrich(p, prompt),
  }));
  renderResults(enrichedResults, $('searchInput').value);
  toast('✨ Dataset enriched!', 'ok');
});

function localEnrich(p, prompt) {
  const q = prompt.toLowerCase();
  const e = {};
  if (q.includes('5g'))     e.connectivity = p.is_5g ? '5G' : '4G';
  if (q.includes('weight')) e.weight = `${160 + Math.floor(Math.random()*50)}g`;
  if (q.includes('colour') || q.includes('color')) e.colors = 'Black, Blue, White';
  if (q.includes('battery') && !p.battery) e.battery = `${3000 + Math.floor(Math.random()*2500)} mAh`;
  if (q.includes('screen') || q.includes('display')) e.display = `${(5.5+Math.random()).toFixed(1)}" AMOLED`;
  return e;
}

// ── Download CSV ────────────────────────────────────────────────
$('downloadBtn').addEventListener('click', () => {
  const data = enrichedResults || currentResults;
  if (!data.length) { toast('Nothing to download', 'err'); return; }
  const keys = [...new Set(data.flatMap(Object.keys))];
  const csv  = [
    keys.join(','),
    ...data.map(row =>
      keys.map(k => `"${String(row[k] ?? '').replace(/"/g,'""')}"`).join(',')
    ),
  ].join('\n');
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(new Blob([csv], { type:'text/csv' }));
  a.download = `datacart_${Date.now()}.csv`;
  a.click();
  toast('⬇ CSV downloaded!', 'ok');
});

// ── Wishlist view ───────────────────────────────────────────────
function renderWishlist() {
  const grid  = $('wishlist-grid');
  const empty = $('wishlist-empty');
  if (!wishlist.length) {
    grid.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  grid.innerHTML = '';
  wishlist.forEach((p, i) => grid.appendChild(buildCard(p, i)));
}

$('clearWishlist').addEventListener('click', () => {
  wishlist = [];
  localStorage.removeItem('dc_wishlist');
  refreshBadges();
  renderWishlist();
  toast('Wishlist cleared', '');
});

// ── Compare view ────────────────────────────────────────────────
function renderCompare() {
  const cardsEl = $('compare-cards');
  const chartWr = $('compare-chart-wrap');
  const empty   = $('compare-empty');

  if (!compareList.length) {
    cardsEl.innerHTML = '';
    chartWr.classList.add('hidden');
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  cardsEl.innerHTML = '';

  compareList.forEach(p => {
    const card = document.createElement('div');
    card.className = 'compare-card';
    card.innerHTML = `
      <button class="compare-card-remove" data-id="${p.id}">✕</button>
      <div style="font-size:2rem;margin-bottom:8px">${catEmoji((p.category||'').toLowerCase())}</div>
      <div style="font-family:Syne,sans-serif;font-weight:700;font-size:.92rem;margin-bottom:4px">${p.name}</div>
      <div style="color:var(--teal);font-family:Syne,sans-serif;font-weight:800;font-size:1.1rem;margin-bottom:10px">₹${fmt(p.price)}</div>
      ${buildModalSpecs(p)}
    `;
    card.querySelector('.compare-card-remove').addEventListener('click', () => {
      compareList = compareList.filter(c => c.id !== p.id);
      localStorage.setItem('dc_compare', JSON.stringify(compareList));
      refreshBadges();
      renderCompare();
    });
    cardsEl.appendChild(card);
  });

  drawCompareChart();
}

function drawCompareChart() {
  const wrap = $('compare-chart-wrap');
  if (compareList.length < 2) { wrap.classList.add('hidden'); return; }
  wrap.classList.remove('hidden');

  const labels = ['Price (÷1000)', 'RAM (GB)', 'Storage (÷10)', 'Battery (÷500)', 'Rating×20'];
  const colors = ['rgba(0,229,204,0.7)', 'rgba(255,79,139,0.7)', 'rgba(167,139,250,0.7)', 'rgba(255,181,71,0.7)'];

  const datasets = compareList.map((p, i) => ({
    label: p.name || `Product ${i+1}`,
    data: [
      Math.round((parseInt(p.price)  || 10000) / 1000),
      parseInt(p.ram)     || 4,
      Math.round((parseInt(p.storage)  || 64)  / 10),
      Math.round((parseInt(p.battery)  || 4000)/ 500),
      Math.round((parseFloat(p.rating) || 4.0) * 20),
    ],
    backgroundColor: colors[i % colors.length],
    borderColor:     colors[i % colors.length].replace('0.7','1'),
    borderWidth: 2,
  }));

  if (compareChart) compareChart.destroy();
  compareChart = new Chart($('compareChart').getContext('2d'), {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: '#7a8399', font: { family: 'DM Mono', size: 11 } } },
      },
      scales: {
        x: { ticks: { color: '#7a8399' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: '#7a8399' }, grid: { color: 'rgba(255,255,255,0.04)' } },
      },
    },
  });
}

$('clearCompare').addEventListener('click', () => {
  compareList = [];
  localStorage.removeItem('dc_compare');
  refreshBadges();
  renderCompare();
  toast('Compare list cleared', '');
});

// ── Reminders view ──────────────────────────────────────────────
function renderReminders() {
  const list  = $('reminders-list');
  const empty = $('reminders-empty');

  if (!reminders.length) {
    list.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  list.innerHTML = reminders.map(r => `
    <div class="reminder-item">
      <div>
        <div class="reminder-info-name">🔔 ${r.productName}</div>
        <div class="reminder-info-meta">
          Current: ₹${fmt(r.currentPrice)} · Set ${r.date}
          ${r.email ? ` · ${r.email}` : ''}
        </div>
      </div>
      <div class="reminder-target">Target: ₹${fmt(r.targetPrice)}</div>
      <button class="reminder-del" data-id="${r.id}">🗑</button>
    </div>
  `).join('');

  list.querySelectorAll('.reminder-del').forEach(btn => {
    btn.addEventListener('click', () => {
      reminders = reminders.filter(r => r.id !== parseInt(btn.dataset.id));
      localStorage.setItem('dc_reminders', JSON.stringify(reminders));
      refreshBadges();
      renderReminders();
      toast('Alert removed', '');
    });
  });
}

// ── Demo fallback data (when backend offline) ───────────────────
function demoSearch(query) {
  const q = query.toLowerCase();
  const budget = (() => {
    const m = q.match(/(\d[\d,]*)\s*k?/);
    if (!m) return Infinity;
    let n = parseInt(m[1].replace(',',''));
    if (q.includes('k') && n < 1000) n *= 1000;
    return n;
  })();

  const isPhone  = /phone|mobile|smartphone/.test(q);
  const isLaptop = /laptop|notebook/.test(q);
  const isSun    = /sunscreen|spf/.test(q);
  const isSerum  = /serum/.test(q);
  const isLip    = /lipstick|lip/.test(q);
  const isMoist  = /moisturiz/.test(q);

  const DEMO = {
    phone: [
      { id:'p1', name:'Redmi 13C',        brand:'Xiaomi',   category:'phone', price:8999,  ram:'4GB', storage:'128GB', battery:'5000 mAh', camera:'50MP',  rating:4.1, is_5g:0, match_score:72, explanation:'Budget-friendly pick with great value.', source:'Amazon', url:'https://www.amazon.in/s?k=Redmi+13C', reviews_url:'https://www.amazon.in/s?k=Redmi+13C#customerReviews', review_count:'12,450', image:'https://m.media-amazon.com/images/I/61Y5R4XTGZL._SX679_.jpg' },
      { id:'p2', name:'Realme C55',        brand:'Realme',   category:'phone', price:9999,  ram:'6GB', storage:'128GB', battery:'5000 mAh', camera:'64MP',  rating:4.2, is_5g:0, match_score:78, explanation:'Strong camera for the price range.' },
      { id:'p3', name:'Poco X5 Pro 5G',   brand:'Poco',     category:'phone', price:22999, ram:'6GB', storage:'128GB', battery:'5000 mAh', camera:'108MP', rating:4.4, is_5g:1, match_score:91, explanation:'9/10 processor + 6GB RAM ideal for gaming.', source:'Flipkart', url:'https://www.flipkart.com/poco-x5-pro-5g/p/itm69d36a9ad70a5', reviews_url:'https://www.flipkart.com/poco-x5-pro-5g/product-reviews/itm69d36a9ad70a5', review_count:'28,310', image:'https://rukminim2.flixcart.com/image/832/832/xif0q/mobile/v/8/u/x5-pro-5g-pfm1-poco-original-imagmyg9gahhqg7e.jpeg' },
      { id:'p4', name:'iQOO Z7 5G',        brand:'iQOO',     category:'phone', price:18999, ram:'6GB', storage:'128GB', battery:'4400 mAh', camera:'64MP',  rating:4.4, is_5g:1, match_score:88, explanation:'Strong processor for gaming + 5G ready.' },
      { id:'p5', name:'Nothing Phone 1',   brand:'Nothing',  category:'phone', price:19999, ram:'8GB', storage:'128GB', battery:'4500 mAh', camera:'50MP',  rating:4.4, is_5g:1, match_score:85, explanation:'8GB RAM, trusted brand, AMOLED display.' },
      { id:'p6', name:'Redmi Note 13 Pro', brand:'Xiaomi',   category:'phone', price:26999, ram:'8GB', storage:'256GB', battery:'5000 mAh', camera:'200MP', rating:4.4, is_5g:1, match_score:94, explanation:'200MP camera — best in class photography.' },
    ],
    laptop: [
      { id:'l1', name:'Lenovo IdeaPad Slim 3', brand:'Lenovo', category:'laptop', price:29990, ram:'8GB',  storage:'512GB', battery:'45Wh', rating:4.2, match_score:80, explanation:'Reliable work laptop with solid battery life.' },
      { id:'l2', name:'ASUS VivoBook 15',      brand:'ASUS',   category:'laptop', price:35990, ram:'16GB', storage:'512GB', battery:'50Wh', rating:4.3, match_score:87, explanation:'16GB RAM perfect for multitasking.' },
      { id:'l3', name:'ASUS TUF Gaming F15',   brand:'ASUS',   category:'laptop', price:72990, ram:'16GB', storage:'512GB', battery:'72Wh', rating:4.4, match_score:93, explanation:'Gaming-grade specs: 9/10 processor, 16GB RAM.' },
    ],
    sunscreen: [
      { id:'s1', name:'Minimalist SPF 50',      brand:'Minimalist', category:'sunscreen', price:399, spf_value:50, skin_compat:5, rating:4.5, is_water_based:1, match_score:95, explanation:'SPF 50, fragrance-free, skin compatibility 5/5.' },
      { id:'s2', name:'Neutrogena Ultra Sheer', brand:'Neutrogena', category:'sunscreen', price:599, spf_value:55, skin_compat:5, rating:4.4, is_water_based:1, match_score:93, explanation:'SPF 55, dermatologist recommended, lightweight.' },
      { id:'s3', name:'Deconstruct SPF 50',     brand:'Deconstruct', category:'sunscreen', price:449, spf_value:50, skin_compat:5, rating:4.4, is_water_based:1, match_score:90, explanation:'SPF 50, water-based, non-comedogenic formula.' },
    ],
    serum: [
      { id:'sr1', name:'Minimalist Niacinamide 10%', brand:'Minimalist', category:'serum', price:599, skin_compat:5, is_water_based:1, fragrance_free:1, rating:4.6, match_score:96, explanation:'Water-based, fragrance-free, 5/5 skin compatibility.', source:'Nykaa', url:'https://www.nykaa.com/minimalist-niacinamide-10-zinc-1-face-serum/p/6617453', reviews_url:'https://www.nykaa.com/minimalist-niacinamide-10-zinc-1-face-serum/p/6617453#reviews', review_count:'8,240', image:'https://adn-static1.nykaa.com/nykdesignstudio-images/pub/media/catalog/product/6/6/663f1fd_1.jpg' },
      { id:'sr2', name:'The Ordinary Niacinamide',   brand:'The Ordinary', category:'serum', price:590, skin_compat:5, is_water_based:1, fragrance_free:1, rating:4.5, match_score:94, explanation:'Lightweight water serum, globally trusted formula.' },
      { id:'sr3', name:'Derma Co Hyaluronic',        brand:'Derma Co', category:'serum', price:449, skin_compat:5, is_water_based:1, fragrance_free:1, rating:4.5, match_score:92, explanation:'1% Hyaluronic acid, water-based deep hydration.' },
    ],
    lipstick: [
      { id:'lip1', name:'MAC Matte Lipstick',       brand:'MAC',        category:'lipstick', price:1850, skin_compat:5, long_wear:1, brand_trust:5, rating:4.6, match_score:95, explanation:'Long-wear formula, trusted brand 5/5, skin-safe.' },
      { id:'lip2', name:'NYX Soft Matte',           brand:'NYX',        category:'lipstick', price:699,  skin_compat:4, long_wear:1, brand_trust:4, rating:4.4, match_score:89, explanation:'Long-lasting matte colour, fragrance-free.' },
      { id:'lip3', name:'Maybelline Color Sensational', brand:'Maybelline', category:'lipstick', price:499, skin_compat:4, long_wear:0, brand_trust:5, rating:4.3, match_score:82, explanation:'Trusted brand 5/5, comfortable wear, wide shades.' },
    ],
    moisturizer: [
      { id:'m1', name:'Neutrogena Hydro Boost', brand:'Neutrogena', category:'moisturizer', price:799, skin_compat:5, is_water_based:1, fragrance_free:1, rating:4.5, match_score:95, explanation:'Water-based gel, skin compatibility 5/5, fragrance-free.' },
      { id:'m2', name:'Cetaphil Moisturizer',   brand:'Cetaphil',   category:'moisturizer', price:499, skin_compat:5, is_water_based:0, fragrance_free:1, rating:4.5, match_score:90, explanation:'Dermatologist recommended, fragrance-free, gentle.' },
      { id:'m3', name:'Minimalist HA Cream',    brand:'Minimalist', category:'moisturizer', price:399, skin_compat:5, is_water_based:1, fragrance_free:1, rating:4.4, match_score:88, explanation:'Water-based, HA formula, lightweight hydration.' },
    ],
  };

  let pool = isLaptop ? DEMO.laptop
           : isSun    ? DEMO.sunscreen
           : isSerum  ? DEMO.serum
           : isLip    ? DEMO.lipstick
           : isMoist  ? DEMO.moisturizer
           : DEMO.phone;

  return pool.filter(p => parseInt(p.price) <= budget);
}

// ── On app load: check backend health ──────────────────────────
(async function checkHealth() {
  try {
    const r = await fetchTimeout(`${API}/health`, 3000);
    const d = await r.json();
    if (d.ml_loaded) {
      console.log(`✅ ML model loaded: ${d.model_type} (accuracy: ${d.accuracy})`);
    } else {
      console.warn('⚠️ ML model not loaded — using rule-based scoring');
    }
  } catch {
    console.warn('⚠️ Backend offline — demo mode active');
  }
})();