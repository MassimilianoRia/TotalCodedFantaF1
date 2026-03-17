const tokenKey = "fantaf1_token";

const el = (id) => document.getElementById(id);
const log = (msg) => (el("logBox").textContent = `${new Date().toISOString()} - ${msg}\n` + el("logBox").textContent);

function token() { return localStorage.getItem(tokenKey); }
function headers(json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  if (token()) h["Authorization"] = `Bearer ${token()}`;
  return h;
}

async function api(path, method = "GET", body = null) {
  const res = await fetch(path, { method, headers: headers(body !== null), body: body ? JSON.stringify(body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

async function refreshBasics() {
  const [teams, weekends, lb] = await Promise.all([api('/fantasy-teams'), api('/weekends'), api('/leaderboard')]);
  el("teamSelect").innerHTML = teams.map(t => `<option value="${t.id}">${t.name} (${t.drivers_count}/5) ${t.is_claimed ? '🔒':''}</option>`).join('');
  el("weekendSelect").innerHTML = weekends.map(w => `<option value="${w.id}">${w.season} R${w.round} - ${w.name} [${w.status}]</option>`).join('');
  el("leaderboardBox").textContent = JSON.stringify(lb, null, 2);
}

async function refreshMe() {
  if (!token()) { el("meBox").textContent = "Non autenticato"; return; }
  try {
    const me = await api('/me');
    el("meBox").textContent = JSON.stringify(me, null, 2);
    el("authStatus").textContent = `Autenticato: ${me.email} (${me.is_admin ? 'admin' : 'user'})`;
    el("captainDriverSelect").innerHTML = (me.team_drivers || []).map(d => `<option value="${d.id}">${d.code} - ${d.name}</option>`).join('');
  } catch (e) {
    el("authStatus").textContent = "Token non valido";
    log(e.message);
  }
}

el("registerBtn").onclick = async () => {
  try {
    const out = await api('/auth/register', 'POST', { email: el("email").value, password: el("password").value });
    localStorage.setItem(tokenKey, out.access_token);
    log('Registrazione ok');
    await refreshMe();
  } catch (e) { log(e.message); }
};

el("loginBtn").onclick = async () => {
  try {
    const out = await api('/auth/login', 'POST', { email: el("email").value, password: el("password").value });
    localStorage.setItem(tokenKey, out.access_token);
    log('Login ok');
    await refreshMe();
  } catch (e) { log(e.message); }
};

el("logoutBtn").onclick = () => { localStorage.removeItem(tokenKey); el("authStatus").textContent = 'Non autenticato'; el("meBox").textContent = ''; };
el("refreshMeBtn").onclick = refreshMe;
el("refreshLeaderboardBtn").onclick = refreshBasics;

el("claimBtn").onclick = async () => {
  try { await api(`/claim/${el("teamSelect").value}`, 'POST'); log('Team claimato'); await refreshMe(); await refreshBasics(); }
  catch (e) { log(e.message); }
};

el("savePredBtn").onclick = async () => {
  const w = el("weekendSelect").value;
  const payload = {
    red_flag: el("pred_red_flag").checked,
    safety_car_or_vsc: el("pred_safety").checked,
    wet_tyres: el("pred_wet").checked,
    top2_same_constructor: el("pred_top2").checked,
    poleman_wins: el("pred_pole").checked,
    over_2_dnf_dns: el("pred_dnf").checked,
    constructors_2_top10: Number(el("pred_top10").value),
  };
  try { await api(`/weekends/${w}/predictions`, 'PUT', payload); log('Predizione salvata'); }
  catch (e) { log(e.message); }
};

el("delPredBtn").onclick = async () => {
  try { await api(`/weekends/${el("weekendSelect").value}/predictions`, 'DELETE'); log('Predizione eliminata'); }
  catch (e) { log(e.message); }
};

el("setCaptainBtn").onclick = async () => {
  try { await api(`/weekends/${el("weekendSelect").value}/captain`, 'PUT', { driver_id: el("captainDriverSelect").value }); log('Capitano impostato'); }
  catch (e) { log(e.message); }
};

el("setPoopBtn").onclick = async () => {
  try { await api(`/weekends/${el("weekendSelect").value}/poop-prediction`, 'PUT', { bucket: el("poopBucket").value }); log('Poop prediction salvata'); }
  catch (e) { log(e.message); }
};

el("runAdminBtn").onclick = async () => {
  let payload;
  try { payload = JSON.parse(el("adminPayload").value || '{}'); }
  catch { log('JSON payload non valido'); return; }
  const action = el("adminAction").value;
  const map = {
    constructor: ['/admin/constructors', 'POST'],
    driver: ['/admin/drivers', 'POST'],
    team: ['/admin/fantasy-teams', 'POST'],
    weekend: ['/admin/weekends', 'POST'],
  };
  try {
    const [path, method] = map[action];
    const out = await api(path, method, payload);
    log(`Admin action ok: ${JSON.stringify(out)}`);
    await refreshBasics();
  } catch (e) { log(e.message); }
};

refreshBasics().then(refreshMe);
