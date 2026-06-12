let state = { articles: [], keywords: [] };

const $ = (id) => document.getElementById(id);

async function loadToday(filter = '') {
  const res = await fetch('/api/today');
  state = await res.json();
  renderKeywords();
  renderArticles(filter);
}

function renderKeywords() {
  const box = $('keywords');
  if (!state.keywords.length) {
    box.innerHTML = '<p>ยังไม่มี keyword วันนี้</p>';
    return;
  }
  box.innerHTML = state.keywords.map(k => `
    <span class="keyword" data-keyword="${escapeHtml(k.keyword)}">
      ${escapeHtml(k.keyword)} <strong>${k.count}</strong>
    </span>
  `).join('');
  box.querySelectorAll('.keyword').forEach(el => {
    el.addEventListener('click', () => {
      $('search').value = el.dataset.keyword;
      renderArticles(el.dataset.keyword);
    });
  });
}

function renderArticles(filter = '') {
  const needle = filter.trim().toLowerCase();
  const articles = state.articles.filter(a => {
    const hay = `${a.title} ${a.title_th || ''} ${a.source} ${a.journalist} ${a.keywords.join(' ')}`.toLowerCase();
    return !needle || hay.includes(needle);
  });
  const box = $('articles');
  if (!articles.length) {
    box.innerHTML = '<p>ยังไม่มีข่าว หรือไม่พบคำค้น</p>';
    return;
  }
  box.innerHTML = articles.map(a => `
    <article class="article">
      <h3><a href="${escapeAttr(a.url)}" target="_blank" rel="noreferrer">${escapeHtml(a.title)}</a></h3>
      <div class="meta">${escapeHtml(a.source)} · นักข่าว: ${escapeHtml(a.journalist)} · ${escapeHtml(a.created_at)}</div>
      <div class="tags">${a.keywords.map(k => `<span class="tag">${escapeHtml(k)}</span>`).join('')}</div>
    </article>
  `).join('');
}

async function submitLinks() {
  const journalist = $('journalist').value.trim() || 'ไม่ระบุชื่อ';
  const links = $('links').value.split('\n').map(x => x.trim()).filter(Boolean);
  if (!links.length) {
    $('result').textContent = 'กรุณาวางลิงก์ก่อน';
    return;
  }
  $('submitBtn').disabled = true;
  $('result').textContent = 'กำลังตรวจ...';
  try {
    const res = await fetch('/api/links', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ journalist, links })
    });
    const payload = await res.json();
    $('result').innerHTML = formatResult(payload);
    $('links').value = '';
    await loadToday($('search').value);
  } catch (err) {
    $('result').textContent = `Error: ${err.message}`;
  } finally {
    $('submitBtn').disabled = false;
  }
}

function formatResult(payload) {
  const ok = `<div class="ok">✅ เพิ่มแล้ว ${payload.created} ข่าว</div>`;
  const dup = payload.duplicates.length ? `\n<div class="warn">⚠️ เจอข่าวน่าซ้ำ ${payload.duplicates.length} ข่าว</div>` + payload.duplicates.map(d => `
    <div class="dup">
      <b>${escapeHtml(d.title)}</b><br>
      keyword: ${d.keywords.map(escapeHtml).join(', ')}<br>
      เหตุผล: ${escapeHtml(d.type)} ซ้ำกับ ${escapeHtml(d.matches[0].article.title)}<br>
      overlap: ${(d.matches[0].overlap || []).map(escapeHtml).join(', ') || '-'}
    </div>
  `).join('') : '';
  return ok + dup;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
}
function escapeAttr(value) { return escapeHtml(value); }

$('submitBtn').addEventListener('click', submitLinks);
$('search').addEventListener('input', e => renderArticles(e.target.value));
loadToday();
