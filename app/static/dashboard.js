const tokenKey = "fantaf1_token";
const token = localStorage.getItem(tokenKey);
if (!token) location.href = "/";

const el = (id) => document.getElementById(id);
const log = (msg) => (el("logBox").textContent = `${new Date().toISOString()} - ${msg}\n` + el("logBox").textContent);

async function api(path, method = "GET", body = null) {
  const res = await fetch(path, {
    method,
    headers: {
      "Authorization": `Bearer ${token}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

let currentUser = null;

async function refreshBase() {
  const [me, teams, weekends, leaderboard, stats] = await Promise.all([
    api('/me'), api('/fantasy-teams'), api('/weekends'), api('/leaderboard'), api('/me/stats')
  ]);
  currentUser = me;
  el("userBadge").textContent = `${me.email} (${me.is_admin ? 'admin' : 'user'})`;
  el("adminPanel").hidden = !me.is_admin;
  el("meBox").textContent = JSON.stringify(me, null, 2);
  el("statsBox").textContent = JSON.stringify(stats, null, 2);
  el("leaderboardBox").textContent = JSON.stringify(leaderboard, null, 2);
  el("teamSelect").innerHTML = teams.map(t => `<option value="${t.id}">${t.name} (${t.drivers_count}/5) ${t.is_claimed ? '🔒' : ''}</option>`).join('');
  el("weekendSelect").innerHTML = weekends.map(w => `<option value="${w.id}">${w.season} R${w.round} - ${w.name} [${w.status}]</option>`).join('');
  el("captainDriverSelect").innerHTML = (me.team_drivers || []).map(d => `<option value="${d.id}">${d.code} - ${d.name}</option>`).join('');
}

el("logoutBtn").onclick = () => {
  localStorage.removeItem(tokenKey);
  location.href = "/";
};

el("refreshLeaderboardBtn").onclick = async () => {
  try { el("leaderboardBox").textContent = JSON.stringify(await api('/leaderboard'), null, 2); }
  catch (e) { log(e.message); }
};

el("refreshStatsBtn").onclick = async () => {
  try { el("statsBox").textContent = JSON.stringify(await api('/me/stats'), null, 2); }
  catch (e) { log(e.message); }
};

el("claimBtn").onclick = async () => {
  try { await api(`/claim/${el("teamSelect").value}`, 'POST'); log('Team claimato'); await refreshBase(); }
  catch (e) { log(e.message); }
};

el("setCaptainBtn").onclick = async () => {
  try { await api(`/weekends/${el("weekendSelect").value}/captain`, 'PUT', { driver_id: el("captainDriverSelect").value }); log('Capitano aggiornato'); }
  catch (e) { log(e.message); }
};

el("savePredBtn").onclick = async () => {
  const payload = {
    red_flag: el("pred_red_flag").checked,
    safety_car_or_vsc: el("pred_safety").checked,
    wet_tyres: el("pred_wet").checked,
    top2_same_constructor: el("pred_top2").checked,
    poleman_wins: el("pred_pole").checked,
    over_2_dnf_dns: el("pred_dnf").checked,
    constructors_2_top10: Number(el("pred_top10").value),
  };
  try { await api(`/weekends/${el("weekendSelect").value}/predictions`, 'PUT', payload); log('Predizione salvata'); }
  catch (e) { log(e.message); }
};

el("delPredBtn").onclick = async () => {
  try { await api(`/weekends/${el("weekendSelect").value}/predictions`, 'DELETE'); log('Predizione eliminata'); }
  catch (e) { log(e.message); }
};

el("setPoopBtn").onclick = async () => {
  try { await api(`/weekends/${el("weekendSelect").value}/poop-prediction`, 'PUT', { bucket: el("poopBucket").value }); log('Minigioco salvato'); }
  catch (e) { log(e.message); }
};

el("runAdminBtn").onclick = async () => {
  let payload;
  try { payload = JSON.parse(el("adminPayload").value || '{}'); }
  catch { log('JSON non valido'); return; }

  const map = {
    constructor: ['/admin/constructors', 'POST'],
    driver: ['/admin/drivers', 'POST'],
    team: ['/admin/fantasy-teams', 'POST'],
    weekend: ['/admin/weekends', 'POST'],
  };

  try {
    const [path, method] = map[el("adminAction").value];
    const out = await api(path, method, payload);
    log(`Admin OK: ${JSON.stringify(out)}`);
    await refreshBase();
  } catch (e) {
    log(e.message);
  }
};

refreshBase().catch((e) => {
  log(e.message);
  if (String(e.message).toLowerCase().includes('invalid token')) {
    localStorage.removeItem(tokenKey);
    location.href = '/';
  }
});
