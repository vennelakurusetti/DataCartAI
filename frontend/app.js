/* -----------------------------------------------
   DataCartAI � app.js
   Full client-side logic. Works standalone (demo
   data) AND connects to FastAPI backend if running.
----------------------------------------------- */

const API = 'http://127.0.0.1:9000';

// -- Particle canvas on landing ------------------
(function initParticles() {
  const canvas = document.getElementById('particle-canvas');
  const ctx = canvas.getContext('2d');
  let W, H, particles;

  function resize() {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function makeParticles() {
    particles = Array.from({ length: 90 }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.5 + 0.4,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      alpha: Math.random() * 0.5 + 0.1,
    }));
  }

  let mouse = { x: -999, y: -999 };
  window.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; });

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      const dx = p.x - mouse.x, dy = p.y - mouse.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 100 && dist > 0) {
        p.x += dx / dist * 1.2;
        p.y += dy / dist * 1.2;
      }
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,229,255,${p.alpha})`;
      ctx.fill();
    });

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < 120) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(0,229,255,${0.08 * (1 - d / 120)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', () => { resize(); makeParticles(); });
  resize(); makeParticles(); draw();
})();

document.getElementById('enterBtn').addEventListener('click', enterApp);
document.addEventListener('keydown', e => { if (e.key === 'Enter' && !document.getElementById('landing').classList.contains('hidden')) enterApp(); });

function enterApp() {
  const landing = document.getElementById('landing');
  landing.classList.add('exit');
  setTimeout(() => {
    landing.classList.add('hidden');
    document.getElementById('app').classList.remove('hidden');
    document.getElementById('searchInput').focus();
  }, 650);
}

let currentResults = [];
let enrichedResults = null;
let currentProduct = null;
let wishlist = JSON.parse(localStorage.getItem('dc_wishlist') || '[]');
let compareList = JSON.parse(localStorage.getItem('dc_compare') || '[]');
let reminders = JSON.parse(localStorage.getItem('dc_reminders') || '[]');

document.querySelectorAll('.nav-btn[data-view]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const view = btn.dataset.view;
    document.querySelectorAll('.view').forEach(v => {
      v.classList.toggle('active', v.id === `view-${view}`);
      v.classList.toggle('hidden', v.id !== `view-${view}`);
    });
    if (view === 'wishlist') renderWishlist();
    if (view === 'compare') renderCompare();
    if (view === 'reminders') renderReminders();
  });
});

document.querySelectorAll('.quick-tag').forEach(tag => {
  tag.addEventListener('click', () => {
    document.getElementById('searchInput').value = tag.dataset.q;
    doSearch(tag.dataset.q);
  });
});

document.getElementById('searchBtn').addEventListener('click', () => doSearch(document.getElementById('searchInput').value.trim()));
document.getElementById('searchInput').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(document.getElementById('searchInput').value.trim()); });

async function doSearch(query) {
  if (!query) return;
  showLoading('Searching for the best deals�');
  enrichedResults = null;

  try {
    const res = await fetchWithTimeout(`${API}/search?q=${encodeURIComponent(query)}`, 3000);
    if (res.ok) {
      const data = await res.json();
      currentResults = data.products || data;
    } else {
      currentResults = localSearch(query);
    }
  } catch {
    currentResults = localSearch(query);
  }

  hideLoading();
  renderResults(currentResults, query);

  if (currentResults.length > 0) {
    document.getElementById('enrich-bar').classList.remove('hidden');
  }
}

function fetchWithTimeout(url, ms) {
  return Promise.race([
    fetch(url),
    new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), ms))
  ]);
}

function renderResults(products, query) {
  console.log('DEBUG PRODUCTS:', products); // Debug: log products in renderResults
  const section = document.getElementById('results-section');
  const grid = document.getElementById('product-grid');
  const empty = document.getElementById('empty-state');
  const title = document.getElementById('results-title');
  const count = document.getElementById('results-count');

  if (!products || products.length === 0) {
    section.classList.add('hidden');
    empty.classList.remove('hidden');
    empty.querySelector('p').innerHTML = `No results for <em>"${query}"</em>.<br>Try "phones under 15000" or "laptops under 50k"`;
    return;
  }

  section.classList.remove('hidden');
  empty.classList.add('hidden');
  title.textContent = `Results for "${query}"`;
  count.textContent = `${products.length} products found`;

  grid.innerHTML = '';
  products.forEach((p, i) => {
    const card = createProductCard(p, i);
    grid.appendChild(card);
  });
}

function createProductCard(p, delay = 0) {
  const inWishlist = wishlist.some(w => w.id === p.id);
  const card = document.createElement('div');
  card.className = 'product-card';
  card.style.animationDelay = `${delay * 0.05}s`;

  const cat = (p.category || 'phone').toLowerCase();
  const badgeClass = cat.includes('laptop') ? 'badge-laptop' :
                     cat.includes('ear')    ? 'badge-earbuds' :
                     cat.includes('watch')  ? 'badge-watch'   : 'badge-phone';

  const emoji = cat.includes('laptop') ? '??' :
                cat.includes('ear')    ? '??' :
                cat.includes('watch')  ? '?' : '??';

  const specs = buildSpecTags(p);

  card.innerHTML = `
    <span class="product-card-badge ${badgeClass}">${p.category || 'Phone'}</span>
    ${p.image ? `<img class="product-img" src="${p.image}" alt="${p.name || 'Product'}"/>` : `<span class="product-emoji">${emoji}</span>`}
    <div class="product-name">${p.name || p.model || 'Unknown'}</div>
    <div class="product-brand">${p.brand || ''}</div>
    <div class="product-price">₹${formatPrice(p.price)}</div>
    <div class="product-specs">${specs}</div>
    <div class="product-card-actions">
      <button class="card-btn card-btn-primary">View Details</button>
      <button class="card-btn card-btn-heart ${inWishlist ? 'active' : ''}" title="Save to wishlist">${inWishlist ? '❤️' : '🤍'}</button>
    </div>
  `;

  card.querySelector('.card-btn-primary').addEventListener('click', (e) => {
    e.stopPropagation();
    openModal(p);
  });

  const heartBtn = card.querySelector('.card-btn-heart');
  heartBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleWishlist(p, heartBtn);
  });

  card.addEventListener('click', () => openModal(p));
  return card;
}

function buildSpecTags(p) {
  const tags = [];
  if (p.ram) tags.push(p.ram);
  if (p.storage) tags.push(p.storage);
  if (p.battery) tags.push(p.battery);
  if (p.camera) tags.push(p.camera);
  if (p.display) tags.push(p.display);
  if (p.processor) tags.push(p.processor);
  return tags.slice(0, 4).map(t => `<span class="spec-tag">${t}</span>`).join('');
}

function openModal(p) {
  currentProduct = p;
  const modal = document.getElementById('product-modal');
  const content = document.getElementById('modal-content');

  const cat = (p.category || 'phone').toLowerCase();
  const emoji = cat.includes('laptop') ? '??' : cat.includes('ear') ? '??' : cat.includes('watch') ? '?' : '??';
  const specs = buildModalSpecs(p);

  content.innerHTML = `
    <div class="modal-product-header">
      <div class="modal-emoji">${emoji}</div>
      <div class="modal-product-info">
        <div class="modal-product-name">${p.name || p.model || 'Unknown'}</div>
        <div class="modal-product-brand">${p.brand || ''}</div>
        <div class="modal-product-price">?${formatPrice(p.price)}</div>
      </div>
    </div>
    <div class="modal-specs-grid">${specs}</div>
  `;

  document.getElementById('price-panel').classList.add('hidden');
  document.getElementById('fit-panel').classList.add('hidden');
  document.getElementById('reminder-panel').classList.add('hidden');
  document.getElementById('fit-result').classList.add('hidden');

  const inWishlist = wishlist.some(w => w.id === p.id);
  document.getElementById('modalWishlist').textContent = inWishlist ? '?? Remove from Wishlist' : '?? Save to Wishlist';

  modal.classList.remove('hidden');
}

function buildModalSpecs(p) {
  const rows = [
    ['Brand', p.brand],
    ['Price', p.price ? `?${formatPrice(p.price)}` : null],
    ['RAM', p.ram],
    ['Storage', p.storage],
    ['Battery', p.battery],
    ['Camera', p.camera],
    ['Display', p.display],
    ['Processor', p.processor],
    ['OS', p.os],
    ['Rating', p.rating ? `? ${p.rating}/5` : null],
  ];
  return rows
    .filter(([, v]) => v)
    .map(([k, v]) => `<div class="modal-spec-row"><div class="modal-spec-label">${k}</div><div class="modal-spec-value">${v}</div></div>`)
    .join('');
}

document.getElementById('modalClose').addEventListener('click', () => {
  document.getElementById('product-modal').classList.add('hidden');
});
document.getElementById('product-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('product-modal')) document.getElementById('product-modal').classList.add('hidden');
});

document.getElementById('modalBestPrice').addEventListener('click', async () => {
  const panel = document.getElementById('price-panel');
  const fitPanel = document.getElementById('fit-panel');
  const reminderPanel = document.getElementById('reminder-panel');
  const resultsEl = document.getElementById('price-results');

  // Always show price panel, hide others
  panel.classList.remove('hidden');
  fitPanel.classList.add('hidden');
  reminderPanel.classList.add('hidden');
  panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
  resultsEl.innerHTML = '<div style="color:var(--text3);font-size:0.85rem;padding:12px 0">🔎 Searching best prices across stores…</div>';

  const p = currentProduct;
  const name = encodeURIComponent(p.name || p.model || '');

  try {
    const res = await fetchWithTimeout(`${API}/best-price?name=${name}&price=${p.price}`, 4000);
    if (res.ok) {
      const data = await res.json();
      renderPriceResults(data.results);
      return;
    }
  } catch {}

  const base = parseInt(p.price) || 10000;
  const stores = [
    { name: 'Amazon', discount: 0.08, icon: '??', tag: 'Prime Deal' },
    { name: 'Flipkart', discount: 0.06, icon: '???', tag: 'Sale Price' },
    { name: 'Croma', discount: 0.03, icon: '??', tag: 'Store Pick-up' },
    { name: 'Reliance Digital', discount: 0.01, icon: '??', tag: 'EMI Available' },
  ];

  const results = stores.map(s => ({
    store: s.name,
    icon: s.icon,
    price: Math.round(base * (1 - s.discount)),
    tag: s.tag,
    url: `https://www.${s.name.toLowerCase().replace(' ','')}.com/s?k=${name}`,
  }));

  renderPriceResults(results);
});

function renderPriceResults(results) {
  const el = document.getElementById('price-results');
  const sorted = [...results].sort((a, b) => a.price - b.price);
  el.innerHTML = sorted.map((r, i) => `
    <a class="price-item" href="${r.url || '#'}" target="_blank" rel="noopener">
      <div>
        <div class="price-item-name">${r.icon || ''} ${r.store}</div>
        <div class="price-item-meta">${r.tag || ''} ${i === 0 ? '? Best Deal' : ''}</div>
      </div>
      <div class="price-item-price">?${formatPrice(r.price)}</div>
    </a>
  `).join('');
}

document.getElementById('modalFitMe').addEventListener('click', () => {
  const fitPanel = document.getElementById('fit-panel');
  const pricePanel = document.getElementById('price-panel');
  const reminderPanel = document.getElementById('reminder-panel');
  // Always show fit panel, hide others
  fitPanel.classList.remove('hidden');
  pricePanel.classList.add('hidden');
  reminderPanel.classList.add('hidden');
  fitPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

document.getElementById('fitAnalyzeBtn').addEventListener('click', async () => {
  const use = document.getElementById('fitUse').value;
  const prio = document.getElementById('fitPrice').value;
  const p = currentProduct;
  const res = document.getElementById('fit-result');

  res.classList.remove('hidden');
  res.textContent = '? Analysing�';

  try {
    const resp = await fetchWithTimeout(`${API}/fit?name=${encodeURIComponent(p.name)}&use=${use}&priority=${prio}&price=${p.price}`, 4000);
    if (resp.ok) {
      const data = await resp.json();
      res.textContent = data.verdict;
      return;
    }
  } catch {}

  res.innerHTML = generateLocalVerdict(p, use, prio);
});

function generateLocalVerdict(p, use, prio) {
  const name = p.name || p.model;
  const price = parseInt(p.price) || 0;
  const useMap = {
    gaming: { look: ['processor','ram'], emoji: '??', label: 'gaming' },
    camera: { look: ['camera'], emoji: '??', label: 'photography' },
    work: { look: ['ram','storage','display'], emoji: '??', label: 'productivity' },
    social: { look: ['display','camera'], emoji: '??', label: 'social media' },
    battery: { look: ['battery'], emoji: '??', label: 'all-day use' },
  };

  const ctx = useMap[use] || useMap.social;
  const hasFeature = ctx.look.some(f => p[f]);
  const score = hasFeature ? 'great' : 'decent';

  let msg = `${ctx.emoji} <strong>${name}</strong> is a <strong>${score} choice</strong> for ${ctx.label}. `;
  if (p.battery) msg += `Battery: ${p.battery}. `;
  if (p.camera) msg += `Camera: ${p.camera}. `;
  if (p.ram) msg += `RAM: ${p.ram}. `;

  if (prio === 'very' && price > 15000) {
    msg += `<br><br>?? <em>If budget is your top priority, consider phones in the ?8k�12k range for better value.</em>`;
  } else if (prio === 'premium') {
    msg += `<br><br>?? <em>If you want the very best, look at ?${formatPrice(price + 5000)}+ options for extra features.</em>`;
  } else {
    msg += `<br><br>? <em>This seems like a solid value-for-money choice!</em>`;
  }

  return msg;
}

document.getElementById('modalWishlist').addEventListener('click', () => {
  const btn = document.getElementById('modalWishlist');
  toggleWishlist(currentProduct, btn, true);
});

function toggleWishlist(p, btn, isModal = false) {
  const idx = wishlist.findIndex(w => w.id === p.id);
  if (idx === -1) {
    wishlist.push(p);
    if (btn) {
      btn.classList.add('active');
      if (isModal) btn.textContent = '?? Remove from Wishlist';
    }
    showToast(`?? ${p.name || p.model} saved!`, 'success');
  } else {
    wishlist.splice(idx, 1);
    if (btn) {
      btn.classList.remove('active');
      if (isModal) btn.textContent = '?? Save to Wishlist';
    }
    showToast('Removed from wishlist', '');
  }
  localStorage.setItem('dc_wishlist', JSON.stringify(wishlist));
  updateBadge('wishlist-count', wishlist.length);
}

document.getElementById('modalCompare').addEventListener('click', () => {
  const p = currentProduct;
  if (compareList.length >= 4) { showToast('Max 4 products for comparison', 'error'); return; }
  if (compareList.find(c => c.id === p.id)) { showToast('Already in compare list', ''); return; }
  compareList.push(p);
  localStorage.setItem('dc_compare', JSON.stringify(compareList));
  updateBadge('compare-count', compareList.length);
  showToast(`?? ${p.name || p.model} added to compare!`, 'success');
});

document.getElementById('modalReminder').addEventListener('click', () => {
  const panel = document.getElementById('reminder-panel');
  panel.classList.toggle('hidden');
  document.getElementById('price-panel').classList.add('hidden');
  document.getElementById('fit-panel').classList.add('hidden');
  if (!panel.classList.contains('hidden')) document.getElementById('reminderPrice').value = Math.round(parseInt(currentProduct.price) * 0.85) || '';
});

document.getElementById('saveReminderBtn').addEventListener('click', () => {
  const price = document.getElementById('reminderPrice').value;
  const email = document.getElementById('reminderEmail').value;
  const p = currentProduct;

  if (!price) { showToast('Enter a target price', 'error'); return; }
  if (reminders.find(r => r.productId === p.id)) { showToast('Reminder already set for this product', ''); return; }

  const reminder = {
    id: Date.now(),
    productId: p.id,
    productName: p.name || p.model,
    currentPrice: p.price,
    targetPrice: parseInt(price),
    email: email || 'N/A',
    createdAt: new Date().toLocaleDateString(),
  };

  reminders.push(reminder);
  localStorage.setItem('dc_reminders', JSON.stringify(reminders));
  updateBadge('reminder-count', reminders.length);
  document.getElementById('reminder-panel').classList.add('hidden');
  showToast(`?? Alert set for ?${formatPrice(price)}!`, 'success');
});

document.getElementById('enrichBtn').addEventListener('click', async () => {
  const prompt = document.getElementById('enrichInput').value.trim();
  if (!prompt) { showToast('Describe what to add�', 'error'); return; }

  showLoading('Enriching dataset with AI�');
  try {
    const res = await fetchWithTimeout(`${API}/enrich`, 8000);
    if (res.ok) {
      const data = await res.json();
      enrichedResults = data.products;
      hideLoading();
      renderResults(enrichedResults, `Enriched � ${document.getElementById('searchInput').value}`);
      showToast('? Dataset enriched!', 'success');
      return;
    }
  } catch {}

  const results = (enrichedResults || currentResults).map(p => ({ ...p, ...generateEnrichment(p, prompt) }));
  enrichedResults = results;
  hideLoading();
  renderResults(results, `Enriched � ${document.getElementById('searchInput').value}`);
  showToast('? Dataset enriched locally!', 'success');
});

function generateEnrichment(p, prompt) {
  const lower = prompt.toLowerCase();
  const extra = {};
  if (lower.includes('battery')) extra.battery = extra.battery || `${3000 + Math.floor(Math.random()*3000)} mAh`;
  if (lower.includes('screen') || lower.includes('display')) extra.display = extra.display || `${(5.5 + Math.random()).toFixed(1)}" AMOLED`;
  if (lower.includes('weight')) extra.weight = `${160 + Math.floor(Math.random()*60)}g`;
  if (lower.includes('5g')) extra.connectivity = '5G / WiFi 6 / BT 5.3';
  if (lower.includes('colour') || lower.includes('color')) extra.colors = 'Black, Blue, White, Green';
  if (lower.includes('rating')) extra.rating = (3.5 + Math.random() * 1.5).toFixed(1);
  return extra;
}

document.getElementById('downloadBtn').addEventListener('click', () => {
  const data = enrichedResults || currentResults;
  if (!data.length) { showToast('Nothing to download', 'error'); return; }

  const keys = [...new Set(data.flatMap(Object.keys))];
  const csv = [keys.join(','), ...data.map(row => keys.map(k => `"${String(row[k] ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');

  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `datacart_${Date.now()}.csv`;
  a.click();
  showToast('? CSV downloaded!', 'success');
});

function renderWishlist() {
  const grid = document.getElementById('wishlist-grid');
  const empty = document.getElementById('wishlist-empty');
  updateBadge('wishlist-count', wishlist.length);

  if (!wishlist.length) {
    grid.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  grid.innerHTML = '';
  wishlist.forEach((p, i) => grid.appendChild(createProductCard(p, i)));
}

document.getElementById('clearWishlistBtn').addEventListener('click', () => {
  wishlist = [];
  localStorage.removeItem('dc_wishlist');
  updateBadge('wishlist-count', 0);
  renderWishlist();
  showToast('Wishlist cleared', '');
});

function renderCompare() {
  const cardsEl = document.getElementById('compare-cards');
  const empty = document.getElementById('compare-empty');
  const chartWrap = document.getElementById('compare-chart-wrap');

  if (!compareList.length) {
    cardsEl.innerHTML = '';
    empty.classList.remove('hidden');
    chartWrap.classList.add('hidden');
    return;
  }

  empty.classList.add('hidden');
  cardsEl.innerHTML = '';

  compareList.forEach(p => {
    const card = document.createElement('div');
    card.className = 'compare-card';
    card.innerHTML = `
      <button class="compare-card-remove" data-id="${p.id}">?</button>
      <div style="font-size:2rem;margin-bottom:8px">${(p.category||'').toLowerCase().includes('laptop')?'??':'??'}</div>
      <div style="font-family:Syne,sans-serif;font-weight:700;font-size:0.95rem;margin-bottom:4px">${p.name||p.model}</div>
      <div style="color:var(--accent);font-weight:800;font-size:1.2rem;margin-bottom:12px">?${formatPrice(p.price)}</div>
      ${buildModalSpecs(p)}
    `;
    card.querySelector('.compare-card-remove').addEventListener('click', () => {
      compareList = compareList.filter(c => c.id !== p.id);
      localStorage.setItem('dc_compare', JSON.stringify(compareList));
      updateBadge('compare-count', compareList.length);
      renderCompare();
    });
    cardsEl.appendChild(card);
  });

  renderCompareChart();
}

let compareChartInstance = null;

function renderCompareChart() {
  const wrap = document.getElementById('compare-chart-wrap');
  if (compareList.length < 2) { wrap.classList.add('hidden'); return; }
  wrap.classList.remove('hidden');

  const labels = ['Price (scaled)', 'RAM (GB)', 'Storage (GB)', 'Battery (mAh)', 'Rating'];
  const datasets = compareList.map((p, i) => {
    const colors = ['rgba(0,229,255,0.7)', 'rgba(124,92,252,0.7)', 'rgba(255,95,126,0.7)', 'rgba(0,230,118,0.7)'];
    return {
      label: p.name || p.model,
      data: [Math.round((parseInt(p.price) || 10000) / 1000), parseInt(p.ram) || 4, parseInt(p.storage) || 64, Math.round((parseInt(p.battery) || 4000) / 100), parseFloat(p.rating) || 4.0],
      backgroundColor: colors[i % colors.length],
      borderColor: colors[i % colors.length].replace('0.7', '1'),
      borderWidth: 2,
    };
  });

  if (compareChartInstance) compareChartInstance.destroy();
  const ctx = document.getElementById('compareChart').getContext('2d');
  compareChartInstance = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#8892aa', font: { family: 'Space Mono', size: 11 } } } },
      scales: {
        x: { ticks: { color: '#8892aa' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { ticks: { color: '#8892aa' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      },
    },
  });
}

document.getElementById('clearCompareBtn').addEventListener('click', () => {
  compareList = [];
  localStorage.removeItem('dc_compare');
  updateBadge('compare-count', 0);
  renderCompare();
  showToast('Compare list cleared', '');
});

function renderReminders() {
  const list = document.getElementById('reminders-list');
  const empty = document.getElementById('reminders-empty');
  updateBadge('reminder-count', reminders.length);

  if (!reminders.length) {
    list.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  list.innerHTML = reminders.map(r => `
    <div class="reminder-item" data-id="${r.id}">
      <div class="reminder-item-info">
        <div class="reminder-item-name">?? ${r.productName}</div>
        <div class="reminder-item-meta">Current: ?${formatPrice(r.currentPrice)} � Set on ${r.createdAt} � ${r.email !== 'N/A' ? r.email : 'No email'}</div>
      </div>
      <div class="reminder-target-price">Target: ?${formatPrice(r.targetPrice)}</div>
      <button class="reminder-delete" data-id="${r.id}">??</button>
    </div>
  `).join('');

  list.querySelectorAll('.reminder-delete').forEach(btn => {
    btn.addEventListener('click', () => {
      reminders = reminders.filter(r => r.id !== parseInt(btn.dataset.id));
      localStorage.setItem('dc_reminders', JSON.stringify(reminders));
      renderReminders();
      showToast('Reminder removed', '');
    });
  });
}

function formatPrice(n) { return parseInt(n).toLocaleString('en-IN'); }
function showLoading(msg = 'Loading�') { document.getElementById('loading-msg').textContent = msg; document.getElementById('loading-overlay').classList.remove('hidden'); }
function hideLoading() { document.getElementById('loading-overlay').classList.add('hidden'); }
function showToast(msg, type = '') { const t = document.createElement('div'); t.className = `toast ${type}`; t.textContent = msg; document.body.appendChild(t); setTimeout(() => t.remove(), 3100); }
function updateBadge(id, count) { const el = document.getElementById(id); if (el) { el.textContent = count; el.dataset.count = count; } }

updateBadge('wishlist-count', wishlist.length);
updateBadge('compare-count', compareList.length);
updateBadge('reminder-count', reminders.length);

function localSearch(query) {
  const q = query.toLowerCase();
  const budgetMatch = q.match(/(\d[\d,]*)\s*k?/);
  let budget = Infinity;
  if (budgetMatch) {
    budget = parseInt(budgetMatch[1].replace(',', ''));
    if (q.includes('k') && budget < 1000) budget *= 1000;
  }

  const isPhone = q.includes('phone') || q.includes('mobile') || q.includes('smartphone');
  const isLaptop = q.includes('laptop') || q.includes('notebook') || q.includes('computer');
  const isEarbud = q.includes('earbud') || q.includes('earphone') || q.includes('headphone') || q.includes('tws');
  const isWatch = q.includes('watch') || q.includes('smartwatch') || q.includes('wearable');

  let pool = [];
  if (isLaptop) pool = DEMO_LAPTOPS;
  else if (isEarbud) pool = DEMO_EARBUDS;
  else if (isWatch) pool = DEMO_WATCHES;
  else pool = DEMO_PHONES;

  return pool.filter(p => parseInt(p.price) <= budget);
}

const DEMO_PHONES = [
  { id:'p1', name:'Redmi 13C', brand:'Xiaomi', category:'Phone', price:'8999', ram:'4GB', storage:'128GB', battery:'5000 mAh', camera:'50MP', display:'6.74" IPS', processor:'Helio G85', os:'MIUI 14', rating:'4.1' },
  { id:'p2', name:'Realme C55', brand:'Realme', category:'Phone', price:'9999', ram:'6GB', storage:'128GB', battery:'5000 mAh', camera:'64MP', display:'6.72" IPS', processor:'Helio G88', os:'Realme UI', rating:'4.2' },
  { id:'p3', name:'Samsung Galaxy A04', brand:'Samsung', category:'Phone', price:'7999', ram:'4GB', storage:'64GB', battery:'5000 mAh', camera:'50MP', display:'6.5" PLS', processor:'Exynos 850', os:'Android 12', rating:'3.9' },
  { id:'p4', name:'Poco C65', brand:'Poco', category:'Phone', price:'8499', ram:'6GB', storage:'128GB', battery:'5000 mAh', camera:'50MP', display:'6.74" IPS', processor:'Helio G85', os:'MIUI', rating:'4.0' },
  { id:'p5', name:'Infinix Hot 30i', brand:'Infinix', category:'Phone', price:'6999', ram:'4GB', storage:'64GB', battery:'5000 mAh', camera:'13MP', display:'6.56" IPS', processor:'Helio G37', os:'XOS 12', rating:'3.8' },
  { id:'p6', name:'Tecno Spark 20', brand:'Tecno', category:'Phone', price:'9499', ram:'8GB', storage:'128GB', battery:'5000 mAh', camera:'50MP', display:'6.56" IPS', processor:'Helio G85', os:'HiOS', rating:'4.1' },
  { id:'p7', name:'Lava Blaze 2 5G', brand:'Lava', category:'Phone', price:'9999', ram:'4GB', storage:'128GB', battery:'4500 mAh', camera:'50MP', display:'6.5" IPS', processor:'T606', os:'Android 13', rating:'3.9' },
  { id:'p8', name:'Motorola Moto E13', brand:'Motorola', category:'Phone', price:'7499', ram:'4GB', storage:'64GB', battery:'5000 mAh', camera:'13MP', display:'6.5" IPS', processor:'Unisoc T606', os:'Android 13 Go', rating:'3.8' },
  { id:'p9', name:'Samsung Galaxy F04', brand:'Samsung', category:'Phone', price:'7499', ram:'4GB', storage:'64GB', battery:'5000 mAh', camera:'13MP', display:'6.5" TFT', processor:'Exynos 850', os:'Android 12', rating:'3.7' },
  { id:'p10', name:'Redmi A2+', brand:'Xiaomi', category:'Phone', price:'6499', ram:'2GB', storage:'32GB', battery:'5000 mAh', camera:'8MP', display:'6.52" IPS', processor:'Helio G36', os:'MIUI Go', rating:'3.6' },
  { id:'p11', name:'Realme Narzo N55', brand:'Realme', category:'Phone', price:'11999', ram:'4GB', storage:'64GB', battery:'5000 mAh', camera:'64MP', display:'6.72" IPS', processor:'Helio G88', os:'Realme UI', rating:'4.3' },
  { id:'p12', name:'OnePlus Nord CE 3 Lite', brand:'OnePlus', category:'Phone', price:'19999', ram:'8GB', storage:'128GB', battery:'5000 mAh', camera:'108MP', display:'6.72" IPS 120Hz', processor:'Snapdragon 695', os:'OxygenOS', rating:'4.3' },
  { id:'p13', name:'iQOO Z7 5G', brand:'iQOO', category:'Phone', price:'18999', ram:'6GB', storage:'128GB', battery:'4400 mAh', camera:'64MP', display:'6.38" AMOLED 90Hz', processor:'Dimensity 920', os:'FunTouchOS', rating:'4.4' },
  { id:'p14', name:'Poco X5 Pro 5G', brand:'Poco', category:'Phone', price:'22999', ram:'6GB', storage:'128GB', battery:'5000 mAh', camera:'108MP', display:'6.67" AMOLED 120Hz', processor:'Snapdragon 778G', os:'MIUI', rating:'4.4' },
  { id:'p15', name:'Redmi Note 12 5G', brand:'Xiaomi', category:'Phone', price:'14999', ram:'4GB', storage:'128GB', battery:'5000 mAh', camera:'48MP', display:'6.67" AMOLED 120Hz', processor:'Snapdragon 4 Gen 1', os:'MIUI 13', rating:'4.3' },
];

const DEMO_LAPTOPS = [
  { id:'l1', name:'Lenovo IdeaPad Slim 3', brand:'Lenovo', category:'Laptop', price:'29990', ram:'8GB', storage:'512GB SSD', display:'15.6" FHD', processor:'Ryzen 5 5500U', os:'Windows 11', rating:'4.2' },
  { id:'l2', name:'HP 15s-eq2000', brand:'HP', category:'Laptop', price:'33000', ram:'8GB', storage:'512GB SSD', display:'15.6" FHD', processor:'Ryzen 5 5500U', os:'Windows 11', rating:'4.1' },
  { id:'l3', name:'ASUS VivoBook 15', brand:'ASUS', category:'Laptop', price:'35990', ram:'16GB', storage:'512GB SSD', display:'15.6" FHD', processor:'Ryzen 5 5600H', os:'Windows 11', rating:'4.3' },
  { id:'l4', name:'Acer Aspire Lite', brand:'Acer', category:'Laptop', price:'27990', ram:'8GB', storage:'512GB SSD', display:'15.6" FHD', processor:'Core i3-1215U', os:'Windows 11', rating:'4.0' },
  { id:'l5', name:'Dell Inspiron 15 3511', brand:'Dell', category:'Laptop', price:'39990', ram:'8GB', storage:'512GB SSD', display:'15.6" FHD', processor:'Core i5-1135G7', os:'Windows 11', rating:'4.2' },
];

const DEMO_EARBUDS = [
  { id:'e1', name:'boAt Airdopes 141', brand:'boAt', category:'Earbuds', price:'999', battery:'42H total', display:'N/A', processor:'N/A', rating:'4.1' },
  { id:'e2', name:'Noise Air Buds Pro 2', brand:'Noise', category:'Earbuds', price:'1599', battery:'36H total', display:'N/A', processor:'N/A', rating:'4.0' },
  { id:'e3', name:'JBL Wave Flex', brand:'JBL', category:'Earbuds', price:'2999', battery:'32H total', display:'N/A', processor:'N/A', rating:'4.3' },
  { id:'e4', name:'OnePlus Nord Buds 2', brand:'OnePlus', category:'Earbuds', price:'2499', battery:'38H total', display:'N/A', processor:'N/A', rating:'4.2' },
];

const DEMO_WATCHES = [
  { id:'w1', name:'Noise ColorFit Ultra 3', brand:'Noise', category:'Watch', price:'2999', battery:'7 days', display:'1.96" AMOLED', processor:'N/A', rating:'4.1' },
  { id:'w2', name:'boAt Lunar Prime', brand:'boAt', category:'Watch', price:'3499', battery:'7 days', display:'1.78" AMOLED', processor:'N/A', rating:'4.0' },
  { id:'w3', name:'Fastrack Limitless FS1', brand:'Fastrack', category:'Watch', price:'4499', battery:'10 days', display:'1.96" AMOLED', processor:'N/A', rating:'4.2' },
];
