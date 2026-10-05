// Run with Playwright installed outside the product. No production fixture mode.
const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const {once} = require('node:events');
const assert = require('node:assert/strict');
(async () => {
  const fixture = spawn('python3', ['tests/serve_help_fixture.py'], {env:{...process.env, PYTHONPATH:'.'}, stdio:['ignore','pipe','pipe']});
  let browser;
  try {
    const url = await Promise.race([
      once(fixture.stdout, 'data').then(([data]) => data.toString().trim()),
      once(fixture, 'exit').then(() => { throw Error('Fixture exited before readiness'); })
    ]);
    browser = await chromium.launch({headless:true});
    const page = await browser.newPage({viewport:{width:1272,height:846}});
    const shot = async name => {
      if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-' + name + '.png',fullPage:true});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true, name + ': no horizontal overflow');
    };
    // WCAG text contrast for the shared tokens, including muted copy and focus ring.
    const luminance = hex => {
      const rgb = hex.match(/\w\w/g).map(v => parseInt(v,16)/255).map(v => v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4);
      return rgb[0]*.2126 + rgb[1]*.7152 + rgb[2]*.0722;
    };
    for (const [foreground,background] of [['1c2420','ffffff'],['5c6a62','eef1ea'],['2c4d3c','eef1ea'],['ffffff','1c2420'],['8a2f3f','fbeaec'],['8a5a2b','ffffff']]) {
      const values = [luminance(foreground),luminance(background)].sort((a,b) => b-a);
      assert((values[0]+.05)/(values[1]+.05) >= 4.5, 'Token contrast: ' + foreground);
    }
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(url);
    await page.locator('#runtime').filter({hasText:'Private pilot'}).waitFor();
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-desktop.png',fullPage:true});
    await page.locator('#admission > summary').click();
    await shot('consent-' + page.viewportSize().width);
    const consentText = await page.locator('.privacy').innerText();
    assert.doesNotMatch(consentText, /OpenAI|Anthropic|Z\.AI|forensic/i, 'Consent notice stays brief; detail lives on the safety page');
    await page.locator('.privacy a[href="/safety"]').waitFor();
    await page.locator('#pilot').fill('synthetic-pilot-code-at-least-24');
    await page.locator('#consent').check();
    await page.locator('#admission-form button').click();
    await page.locator('#conversation').waitFor({state:'visible'});
    const token = await page.locator('#session-key').inputValue();
    assert.equal(token.length,43);
    await shot('empty');
    assert.equal(await page.locator('#turns .bubble:last-child').evaluate(el => el === document.activeElement),true);
    // Delay and fail only this local synthetic request; protect the draft while waiting.
    let release;
    const pending = new Promise(resolve => { release = resolve; });
    await page.route('**/api/turn', async route => {
      await pending;
      await route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({error:'The reply could not be completed.'})});
    });
    await page.locator('#message').fill('Synthetic: I hesitate to ask again.');
    await page.locator('#send').click();
    await page.locator('#activity').waitFor({state:'visible'});
    assert.equal(await page.locator('#message').evaluate(el => el.readOnly),true);
    assert.equal(await page.locator('#send').isDisabled(),true);
    await shot('waiting');
    release();
    await page.locator('#error').filter({hasText:'draft is still here'}).waitFor();
    assert.equal(await page.locator('#message').inputValue(),'Synthetic: I hesitate to ask again.');
    assert.equal(await page.locator('#error').evaluate(el => el === document.activeElement),true);
    await shot('error');
    await page.unroute('**/api/turn');
    const attack = '<img src=x onerror="window.injectionRan=true"> synthetic observation';
    await page.locator('#message').fill(attack);
    await page.locator('#send').click();
    await page.locator('#phase').filter({hasText:'1 of 12'}).waitFor();
    assert.equal(await page.locator('#turns img').count(),0);
    assert.equal(await page.evaluate(() => window.injectionRan),undefined);
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-thread.png',fullPage:true});
    await page.reload();
    await page.locator('#resume-panel summary').click();
    await shot('resume');
    await page.locator('#resume-key').fill(token);
    await page.locator('#resume button').click();
    await page.locator('#phase').filter({hasText:'1 of 12'}).waitFor();
    await page.locator('#message').fill('Synthetic: let’s stop here. No next step needed.');
    await page.locator('#finish').click();
    await page.locator('#completed').waitFor({state:'visible'});
    await shot('completed-' + page.viewportSize().width);
    assert.equal(await page.locator('#turn').isVisible(),false);
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#delete').click();
    await page.locator('#onboarding').waitFor({state:'visible'});
    assert.notEqual(await page.locator('#admission > summary').getAttribute('tabindex'),'-1');
    await page.setViewportSize({width:390,height:844});
    await page.reload();
    await page.locator('#runtime').filter({hasText:'Private pilot'}).waitFor();
    const entry = await page.locator('#admission > summary').boundingBox();
    assert(entry.y + entry.height < 740, 'Mobile primary entry near top');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-mobile.png',fullPage:true});
    await page.locator('#admission > summary').click();
    await page.locator('#pilot').fill('synthetic-pilot-code-at-least-24');
    await page.locator('#consent').check();
    await page.locator('#admission-form button').click();
    await page.locator('#message').fill('Synthetic: I hesitate to ask for clarification.');
    await page.locator('#send').click();
    await page.locator('#phase').filter({hasText:'1 of 12'}).waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-mobile-thread.png',fullPage:true});
    for (let version = 2; version <= 11; version++) {
      await page.locator('#message').fill('Synthetic observation ' + version);
      await page.locator('#send').click();
      await page.locator('#phase').filter({hasText:version + ' of 12'}).waitFor();
    }
    assert.equal(await page.locator('#send').textContent(),'Send final message');
    await page.locator('#turn').scrollIntoViewIfNeeded();
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-final-exchange-mobile.png'});
    await page.locator('#message').fill('Synthetic: let’s stop here.');
    await page.locator('#send').click();
    await page.locator('#completed').waitFor({state:'visible'});
    await shot('completed-' + page.viewportSize().width);
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#delete').click();
    await page.locator('#onboarding').waitFor({state:'visible'});
    assert.notEqual(await page.locator('#admission > summary').getAttribute('tabindex'),'-1');
    // Narrow mobile onboarding, keyboard focus, API/privacy and read-only state.
    await page.setViewportSize({width:320,height:740});
    await shot('narrow-entry');
    await page.locator('#admission > summary').focus();
    await page.keyboard.press('Enter');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('#pilot').evaluate(el => el === document.activeElement),true);
    assert.notEqual(await page.locator('#pilot').evaluate(el => getComputedStyle(el).outlineStyle),'none');
    await shot('narrow-consent-focus');
    await page.goto(url + '/api-docs');
    await shot('api-mobile');
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-api-mobile-viewport.png'});
    await page.setViewportSize({width:1272,height:846});
    await shot('api-desktop');
    await page.locator('a[href="/safety"]').first().click();
    await page.locator('h1').filter({hasText:'Safety'}).waitFor();
    await shot('safety-desktop');
    const safetyText = await page.locator('main').innerText();
    assert.match(safetyText, /OpenAI|Anthropic|Z\.AI/, 'Safety page carries the full provider disclosure');
    await page.locator('a[href="/"]').last().click();
    await page.locator('#runtime').filter({hasText:'Private pilot'}).waitFor();
    await page.goto(url);
    await page.route('**/api/session', route => route.fulfill({contentType:'application/json',body:JSON.stringify({session:{schema_version:1,consent_version:'old',version:0,max_exchanges:12,phase:'conversation',intake:{context:'Synthetic earlier context'},turns:[],expires_at:1791800000}})}));
    await page.locator('#resume-panel summary').click();
    await page.locator('#resume-key').fill('synthetic-read-only-key');
    await page.locator('#resume button').click();
    await page.locator('#legacy').waitFor({state:'visible'});
    assert.equal(await page.locator('#turn').isVisible(),false);
    await shot('legacy');
    await page.unroute('**/api/session');
    await page.route('**/healthz', route => route.fulfill({contentType:'application/json',body:'{"inference_configured":false}'}));
    await page.goto(url);
    await page.locator('#runtime').filter({hasText:'unavailable'}).waitFor();
    await shot('unavailable');
    assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length),0);
    assert.equal((await page.context().cookies()).length,0);
    assert.deepEqual(errors,[]);
    console.log('Browser passed: consent, empty, pending/error draft preservation, refresh/resume, early finish, 12-exchange completion, deletion, legacy, unavailable, API/privacy, keyboard focus, 320/390/1272px overflow, token contrast, inert text, no browser storage.');
  } finally {
    if(browser) await browser.close();
    fixture.kill();
  }
})().catch(error => { console.error(error.message); process.exitCode=1; });
