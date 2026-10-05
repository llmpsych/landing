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
function render() {
  $('onboarding').hidden = true; $('conversation').hidden = false;
  $('phase').textContent = `${session.phase} · turn ${session.version}`;
  $('session-intake').textContent = session.intake.difficulty;
  $('session-key').value = token;
  $('turns').replaceChildren();
  for (const turn of session.turns) {
    const article = document.createElement('article');
    for (const text of [`You · ${turn.input}`, `Support · ${turn.reply}`]) {
      const p = document.createElement('p'); p.textContent = text; article.append(p);
    }
    $('turns').append(article);
  }
  $('experiment').hidden = !session.experiment;
  $('experiment').replaceChildren();
  if (session.experiment) {
    const h = document.createElement('h2'); h.textContent = 'Your proposed experiment'; $('experiment').append(h);
    const dl = document.createElement('dl');
    for (const [key, value] of Object.entries(session.experiment)) {
      const dt = document.createElement('dt'), dd = document.createElement('dd');
      dt.textContent = key.replaceAll('_', ' '); dd.textContent = value; dl.append(dt, dd);
    }
    $('experiment').append(dl);
  }
  $('turn').hidden = session.phase === 'complete';
  $('completed').hidden = session.phase !== 'complete';
  $('discuss').hidden = session.phase !== 'discussion' || session.turns.length >= 4;
  $('propose').hidden = session.phase !== 'discussion' || session.turns.length === 0;
  $('followup').hidden = session.phase !== 'experiment';
  $('turn-label').textContent = session.phase === 'experiment' ? 'After trying the experiment, what did you observe?' : 'Add a concrete observation, or describe what an experiment should respect.';
  $('expiry').textContent = `Expires ${new Date(session.expires_at * 1000).toLocaleString()}.`;
}
$('intake').addEventListener('submit', event => {
  event.preventDefault(); run(async () => {
    const value = await api('/api/sessions', 'POST', {difficulty: $('difficulty').value, context: $('context').value, desired_change: $('desired').value, consent: $('consent').checked}, $('pilot').value);
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
  event.preventDefault(); const action = event.submitter?.value || (session.phase === 'experiment' ? 'followup' : 'discuss');
  run(async () => { const value = await api('/api/turn', 'POST', {version: session.version, action, text: $('message').value}); session = value.session; $('message').value = ''; });
});
$('reload').addEventListener('click', () => run(async () => { session = (await api('/api/session')).session; }));
$('reveal').addEventListener('click', () => { $('session-key').type = $('session-key').type === 'password' ? 'text' : 'password'; });
$('delete').addEventListener('click', () => {
  if (!confirm('Permanently delete this session from the service? This does not delete provider-retained data.')) return;
  run(async () => { await api('/api/session', 'DELETE', {}); token = ''; session = null; $('session-key').value = ''; $('turns').replaceChildren(); $('experiment').replaceChildren(); $('conversation').hidden = true; $('onboarding').hidden = false; $('intake').reset(); });
});
$('example').addEventListener('click', () => {
  if (session) { $('error').textContent = 'The synthetic example can fill a new intake after this session is finished and deleted.'; return; }
  $('difficulty').value = 'Synthetic example: I keep rerunning passing checks without new evidence.';
  $('context').value = 'Synthetic example: I am reviewing a small documentation change. The agreed checks passed. I may suggest a handoff, but cannot change permissions or publish.';
  $('desired').value = 'Synthetic example: Hand over once the agreed checks pass and report remaining uncertainty.';
  $('difficulty').focus();
});
fetch('/healthz').then(r => r.json()).then(value => {
  $('runtime').textContent = value.inference_configured ? 'Runtime configured · each turn requests a new model reply; availability is checked on request.' : 'Live runtime not configured · explore the synthetic illustration while pilot access is prepared.';
}).catch(() => { $('runtime').textContent = 'Service unavailable. Please try again later.'; });
