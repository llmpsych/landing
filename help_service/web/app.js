'use strict';
const $ = id => document.getElementById(id);
let token = '', session = null, busy = false;
async function api(path, method = 'GET', data, auth = token) {
  const response = await fetch(path, {method, headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${auth}`}, ...(data === undefined ? {} : {body: JSON.stringify(data)})});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Request failed. Reload before retrying.');
  return value;
}
async function run(work) {
  if (busy) return;
  busy = true; $('error').textContent = '';
  document.querySelectorAll('button').forEach(b => { b.disabled = true; });
  try { await work(); } catch (error) { $('error').textContent = error.message; $('error').focus(); }
  finally { busy = false; document.querySelectorAll('button').forEach(b => { b.disabled = false; }); if (session) render(); }
}
function bubble(who, text) {
  const div = document.createElement('div'); div.className = 'bubble' + (who === 'You' ? ' participant' : '');
  const label = document.createElement('span'); label.className = 'speaker'; label.textContent = who;
  const p = document.createElement('p'); p.textContent = text; div.append(label, p); $('turns').append(div);
}
function render() {
  $('onboarding').hidden = true; $('conversation').hidden = false;
  const legacy = session.schema_version !== 2 || session.consent_version !== '2026-10-05-native-providers';
  const ended = legacy || session.phase === 'complete';
  $('phase').textContent = legacy ? 'Earlier session · read-only' : `${session.version} of ${session.max_exchanges} exchanges · ${ended ? 'ended' : 'you can pause or finish sooner'}`;
  $('session-key').value = token;
  $('turns').replaceChildren();
  if (session.intake) bubble('Earlier context', JSON.stringify(session.intake, null, 2));
  else bubble('Help · opening question', session.opening);
  for (const turn of session.turns) { bubble('You', turn.input); bubble('Help', turn.reply); }
  if (legacy && session.experiment) bubble('Earlier proposal', JSON.stringify(session.experiment, null, 2));
  $('legacy').hidden = !legacy;
  $('turn').hidden = ended;
  $('completed').hidden = !ended || legacy;
  $('send').textContent = session.version === session.max_exchanges - 1 ? 'Send final message →' : 'Send →';
  $('expiry').textContent = `Access expires ${new Date(session.expires_at * 1000).toLocaleString()}.`;
}
$('admission-form').addEventListener('submit', event => {
  event.preventDefault(); run(async () => {
    const value = await api('/api/sessions', 'POST', {consent: $('consent').checked}, $('pilot').value);
    token = value.token; session = value.session; $('pilot').value = ''; render();
  });
});
$('resume').addEventListener('submit', event => {
  event.preventDefault(); run(async () => {
    const candidate = $('resume-key').value.trim();
    const value = await api('/api/session', 'GET', undefined, candidate);
    token = candidate; session = value.session; $('resume-key').value = ''; render();
  });
});
$('turn').addEventListener('submit', event => {
  event.preventDefault(); const action = event.submitter?.value || 'message';
  run(async () => { const value = await api('/api/turn', 'POST', {version: session.version, action, text: $('message').value}); session = value.session; $('message').value = ''; });
});
$('reload').addEventListener('click', () => run(async () => { session = (await api('/api/session')).session; }));
$('reveal').addEventListener('click', () => { $('session-key').type = $('session-key').type === 'password' ? 'text' : 'password'; });
$('delete').addEventListener('click', () => {
  if (!confirm('Permanently delete this session from the service? This does not delete provider-retained data.')) return;
  run(async () => { await api('/api/session', 'DELETE', {}); token = ''; session = null; $('session-key').value = ''; $('turns').replaceChildren();  $('conversation').hidden = true; $('onboarding').hidden = false; $('admission-form').reset(); $('turn').reset(); });
});
fetch('/healthz').then(r => r.json()).then(value => {
  $('runtime').textContent = value.inference_configured ? 'Runtime configured · each turn requests a new model reply; availability is checked on request.' : 'Live runtime not configured · you can read the written sample below. No live replies are available.';
}).catch(() => { $('runtime').textContent = 'Service unavailable. Please try again later.'; });
