/* TelePanel — main.js */

const API_BASE = 'http://127.0.0.1:8001';

/* ── Sidebar toggle ─────────────────────────────────── */
const sidebar   = document.getElementById('sidebar');
const hamburger = document.getElementById('hamburger');
const overlay   = document.getElementById('overlay');

hamburger?.addEventListener('click', () => {
  const open = sidebar.classList.toggle('open');
  hamburger.classList.toggle('open', open);
  overlay.classList.toggle('show', open);
});

overlay?.addEventListener('click', () => {
  sidebar.classList.remove('open');
  hamburger.classList.remove('open');
  overlay.classList.remove('show');
});

/* ── Progress bar ───────────────────────────────────── */
function showProgress() {
  const bar = document.getElementById('progress-bar');
  if (!bar) return;
  bar.style.width = '60%';
  setTimeout(() => { bar.style.width = '100%'; }, 300);
  setTimeout(() => { bar.style.opacity = '0'; }, 800);
  setTimeout(() => { bar.style.width = '0'; bar.style.opacity = '1'; }, 1000);
}

document.querySelectorAll('.nav-link').forEach(a =>
  a.addEventListener('click', showProgress)
);

/* ── Toast ──────────────────────────────────────────── */
function toast(msg, type = 'success') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

/* ── Bot status check ───────────────────────────────── */
async function checkBotStatus() {
  const dot   = document.getElementById('statusDot');
  const label = document.getElementById('statusLabel');
  if (!dot || !label) return;
  try {
    const r = await fetch(`${API_BASE}/api/stats`, { signal: AbortSignal.timeout(3000) });
    if (r.ok) {
      dot.classList.add('online');
      label.textContent = 'API online';
    } else { throw new Error(); }
  } catch {
    dot.classList.remove('online');
    label.textContent = 'API offline';
    dot.classList.add('offline');
  }
}

checkBotStatus();
setInterval(checkBotStatus, 15000);

/* ── Ban/unban utente ───────────────────────────────── */
async function toggleBan(utenteId, btn) {
  try {
    const r = await fetch(`${API_BASE}/api/utenti/${utenteId}/ban`, { method: 'PATCH' });
    const data = await r.json();
    const active = data.attivo;
    btn.textContent = active ? 'Ban' : 'Unban';
    btn.className   = active ? 'btn btn-danger' : 'btn btn-ghost';
    const badge = btn.closest('tr')?.querySelector('.status-badge');
    if (badge) {
      badge.className = `badge ${active ? 'badge-green' : 'badge-red'}`;
      badge.textContent = active ? 'attivo' : 'bannato';
    }
    toast(active ? 'Utente riattivato' : 'Utente bannato', active ? 'success' : 'error');
  } catch {
    toast('Errore di rete', 'error');
  }
}

/* ── Remove canale ──────────────────────────────────── */
async function rimuoviCanale(chatId, btn) {
  if (!confirm('Rimuovere questo canale?')) return;
  try {
    const r = await fetch(`${API_BASE}/api/canali/${chatId}`, { method: 'DELETE' });
    if (r.ok) {
      btn.closest('tr')?.remove();
      toast('Canale rimosso');
    }
  } catch {
    toast('Errore di rete', 'error');
  }
}

/* ── Broadcast ──────────────────────────────────────── */
async function sendBroadcast(textarea, btn) {
  const testo = textarea.value.trim();
  if (!testo) { toast('Scrivi un messaggio', 'error'); return; }
  btn.disabled = true;
  btn.textContent = 'Invio…';
  try {
    const r = await fetch(`${API_BASE}/api/broadcast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ testo }),
    });
    const data = await r.json();
    toast(`Inviato a ${data.inviato_a} canali ✓`);
    textarea.value = '';
  } catch {
    toast('Errore broadcast', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Invia';
  }
}

/* ── Staggered table row animation ─────────────────── */
document.querySelectorAll('tbody tr').forEach((tr, i) => {
  tr.style.animationDelay = `${i * 30}ms`;
});

/* ── Add progress bar element ───────────────────────── */
const pb = document.createElement('div');
pb.id = 'progress-bar';
document.body.prepend(pb);
