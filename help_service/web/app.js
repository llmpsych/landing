'use strict';
const $ = id => document.getElementById(id);
let token = '', session = null, busy = false;
async function api(path, method = 'GET', data, auth = token) {
  const response = await fetch(path, {method, headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${auth}`}, ...(data === undefined ? {} : {body: JSON.stringify(data)})});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Request failed. Reload before retrying.');
  return value;
}
async function run(work, status = 'Updating conversation…', focusAfter = null) {
  if (busy) return;
  busy = true; $('error').textContent = '';
  const active = document.activeElement;
  const oldLabel = !session && active?.tagName === 'BUTTON' ? active.textContent : null;
  if (oldLabel) active.textContent = status;
  $('activity').textContent = status; $('activity').hidden = false;
  $('message').readOnly = true;
  document.querySelectorAll('button').forEach(b => { b.disabled = true; });
  let succeeded = false;
  try { await work(); succeeded = true; }
  catch (error) {
    $('error').textContent = `${error.message} ${session ? 'Your draft is still here. Reload the session before retrying if a reply may have been sent.' : 'Check your code or key, then try again.'}`;
  }
  finally {
    busy = false; $('activity').hidden = true; $('message').readOnly = false;
    if (oldLabel) active.textContent = oldLabel;
    document.querySelectorAll('button').forEach(b => { b.disabled = false; });
    if (session) render();
    if (!succeeded) $('error').focus();
    else if (focusAfter) {
      const target = document.querySelector(focusAfter);
      if (target) {
        if (!target.matches('button, input, textarea, summary, a[href]')) target.setAttribute('tabindex', '-1');
        target.focus({preventScroll:true}); target.scrollIntoView({block:'nearest'});
      }
    }
  }
}
function bubble(who, text, tag) {
  const div = document.createElement('div');
  const dataVoice = who.startsWith('Earlier');
  div.className = 'bubble' + (who === 'You' ? ' participant agent-voice' : dataVoice ? ' agent-voice' : '');
  if (tag) { const t = document.createElement('p'); t.className = 'bubble-tag'; t.textContent = tag; div.append(t); }
  const label = document.createElement('span'); label.className = 'speaker'; label.textContent = who;
  const p = document.createElement('p'); p.textContent = text; div.append(label, p); $('turns').append(div);
}
function render() {
  document.body.classList.add('in-session');
  $('onboarding').hidden = true; $('conversation').hidden = false;
  const legacy = session.schema_version !== 2 || session.consent_version !== '2026-10-05-native-providers';
  const ended = legacy || session.phase === 'complete';
  $('phase').replaceChildren();
  const count = document.createElement('span'); count.className = 'count';
  count.textContent = legacy ? 'Earlier session' : `${session.version} of ${session.max_exchanges} exchanges`;
  const status = document.createElement('span'); status.className = 'status';
  status.textContent = legacy ? 'Read-only' : (ended ? 'Ended' : 'You can pause or finish sooner');
  $('phase').append(count, status);
  $('session-key').value = token;
  $('turns').replaceChildren();
  if (session.intake) bubble('Earlier context', JSON.stringify(session.intake, null, 2));
  else bubble('Help', session.opening, 'Opening question');
  for (const turn of session.turns) { bubble('You', turn.input); bubble('Help', turn.reply); }
  if (legacy && session.experiment) bubble('Earlier proposal', JSON.stringify(session.experiment, null, 2));
  $('legacy').hidden = !legacy;
  $('turn').hidden = ended;
  $('completed').hidden = !ended || legacy;
  $('send').textContent = session.version === session.max_exchanges - 1 ? 'Send final message' : 'Send';
  $('expiry').textContent = `Access expires ${new Date(session.expires_at * 1000).toLocaleString()}.`;
}
$('admission-form').addEventListener('submit', event => {
  event.preventDefault(); run(async () => {
    const value = await api('/api/sessions', 'POST', {consent: $('consent').checked}, $('pilot').value);
    token = value.token; session = value.session; $('pilot').value = '';
  }, 'Opening conversation…', '#turns .bubble:last-child');
});
$('resume').addEventListener('submit', event => {
  event.preventDefault(); run(async () => {
    const candidate = $('resume-key').value.trim();
    const value = await api('/api/session', 'GET', undefined, candidate);
    token = candidate; session = value.session; $('resume-key').value = '';
  }, 'Resuming…', '#turns .bubble:last-child');
});
$('turn').addEventListener('submit', event => {
  event.preventDefault(); const action = event.submitter?.value || 'message';
  run(async () => { const value = await api('/api/turn', 'POST', {version: session.version, action, text: $('message').value}); session = value.session; $('message').value = ''; }, 'Waiting for a reply…', '#turns .bubble:last-child');
});
$('reload').addEventListener('click', () => run(async () => { session = (await api('/api/session')).session; }));
$('reveal').addEventListener('click', () => { $('session-key').type = $('session-key').type === 'password' ? 'text' : 'password'; });
$('delete').addEventListener('click', () => {
  if (!confirm('Permanently delete this session from the service? This does not delete provider-retained data.')) return;
  run(async () => { await api('/api/session', 'DELETE', {}); token = ''; session = null; document.body.classList.remove('in-session'); $('session-key').value = ''; $('turns').replaceChildren();  $('conversation').hidden = true; $('onboarding').hidden = false; $('admission-form').reset(); $('turn').reset(); $('session-key').type = 'password'; $('admission').open = false; $('resume-panel').open = false; $('key-panel').open = false; }, 'Deleting…', '#admission > summary');
});
fetch('/healthz').then(r => r.json()).then(value => {
  $('runtime').textContent = value.inference_configured ? 'Private pilot' : 'Conversations are unavailable right now. You can read the written example below.';
}).catch(() => { $('runtime').textContent = 'Service unavailable. Please try again later.'; });
