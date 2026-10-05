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
    const page = await browser.newPage({viewport:{width:1280,height:1000}});
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(url);
    await page.locator('#runtime').filter({hasText:'Runtime configured'}).waitFor();
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-desktop.png',fullPage:true});
    await page.locator('#admission summary').click();
    await page.locator('#pilot').fill('synthetic-pilot-code-at-least-24');
    await page.locator('#consent').check();
    await page.locator('#admission-form button').click();
    await page.locator('#conversation').waitFor({state:'visible'});
    const token = await page.locator('#session-key').inputValue();
    assert.equal(token.length,43);
    const attack = '<img src=x onerror="window.injectionRan=true"> synthetic observation';
    await page.locator('#message').fill(attack);
    await page.locator('#send').click();
    await page.locator('#phase').filter({hasText:'1 of 12'}).waitFor();
    assert.equal(await page.locator('#turns img').count(),0);
    assert.equal(await page.evaluate(() => window.injectionRan),undefined);
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-thread.png',fullPage:true});
    await page.reload();
    await page.locator('#resume-panel summary').click();
    await page.locator('#resume-key').fill(token);
    await page.locator('#resume button').click();
    await page.locator('#phase').filter({hasText:'1 of 12'}).waitFor();
    await page.locator('#message').fill('Synthetic: let’s stop here. No next step needed.');
    await page.locator('#finish').click();
    await page.locator('#completed').waitFor({state:'visible'});
    assert.equal(await page.locator('#turn').isVisible(),false);
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#delete').click();
    await page.locator('#onboarding').waitFor({state:'visible'});
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-mobile.png',fullPage:true});
    await page.locator('#admission summary').click();
    await page.locator('#pilot').fill('synthetic-pilot-code-at-least-24');
    await page.locator('#consent').check();
    await page.locator('#admission-form button').click();
    await page.locator('#message').fill('Synthetic: I hesitate to ask for clarification.');
    await page.locator('#send').click();
    await page.locator('#phase').filter({hasText:'1 of 12'}).waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
    if (process.env.HELP_SCREENSHOT) await page.screenshot({path:process.env.HELP_SCREENSHOT + '-mobile-thread.png',fullPage:true});
    await page.locator('#message').fill('Synthetic: let’s stop here.');
    await page.locator('#finish').click();
    await page.locator('#completed').waitFor({state:'visible'});
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#delete').click();
    await page.locator('#onboarding').waitFor({state:'visible'});
    assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length),0);
    assert.equal((await page.context().cookies()).length,0);
    assert.deepEqual(errors,[]);
    console.log('Browser passed: consent → conversation → refresh/resume → early closure → deletion; text-only rendering; mobile width; no browser storage.');
  } finally {
    if(browser) await browser.close();
    fixture.kill();
  }
})().catch(error => { console.error(error.message); process.exitCode=1; });
