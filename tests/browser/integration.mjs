import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {root, extension, launchExtension, readCsv} from './helpers.mjs';
import path from 'node:path';
const base = 'https://ezpost.post.gov.tw';
const reports = [];
const session = await launchExtension('integration-');
const {context} = session;
const errors = [];
context.on('page', p => p.on('pageerror', error => errors.push(error.message)));
const fixture = `<!doctype html><meta charset="utf-8"><form id="form-login">
<input id="inputEmail" name="MEMBER_ID"><input id="inputPd" type="password" name="MEMBER_PW">
<input id="inputCaptcha" name="Code" value=""><img id="imgCode" src="/fixture/captcha_0158.jpg">
<button>登入</button></form><script>window.events=[];window.submitted=false;
document.querySelector('form').onsubmit=e=>{e.preventDefault();window.submitted=true};
for(const name of ['input','change']) document.querySelector('#inputCaptcha').addEventListener(name,e=>window.events.push(name));</script>`;

try {
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.pathname.startsWith('/fixture/')) {
      const filename = path.basename(url.pathname);
      if (filename === 'bad.jpg') return route.fulfill({status: 200, contentType:'image/jpeg', body:'broken'});
      return route.fulfill({contentType:'image/jpeg', body: await fs.readFile(path.join(root,'dataset',filename))});
    }
    return route.fulfill({contentType:'text/html', body: fixture});
  });
  const page = await context.newPage();
  await page.goto(base+'/Account/Login');
  await page.waitForFunction(() => document.querySelector('#inputCaptcha').value === '01493');
  assert.deepEqual(await page.evaluate(() => events), ['input','change']);
  assert.equal(await page.locator('#inputEmail').inputValue(), '');
  assert.equal(await page.locator('#inputPd').inputValue(), '');
  assert.equal(await page.evaluate(() => submitted), false);
  reports.push('Installed extension injects and fills leading-zero result; input/change events dispatched; other fields and submit unaffected.');
  await page.locator('#inputCaptcha').fill('12345');
  await page.evaluate(() => document.body.appendChild(document.createElement('div')));
  await page.waitForTimeout(150);
  assert.equal(await page.locator('#inputCaptcha').inputValue(),'12345');
  reports.push('Unrelated DOM updates preserve manually edited result.');
  await page.evaluate(() => document.querySelector('#imgCode').src='/fixture/captcha_0003.jpg');
  await page.waitForFunction(() => document.querySelector('#inputCaptcha').value==='32364');
  reports.push('Image source refresh automatically fills new result.');
  await page.evaluate(() => {document.querySelector('#imgCode').src='/fixture/captcha_0001.jpg';document.querySelector('#imgCode').src='/fixture/captcha_0158.jpg';});
  await page.waitForFunction(() => document.querySelector('#inputCaptcha').value==='01493');
  reports.push('Rapid consecutive image refreshes use the final loaded image.');
  await page.evaluate(() => { const old=document.querySelector('#imgCode');const next=old.cloneNode();next.src='/fixture/captcha_0003.jpg';old.replaceWith(next); });
  await page.waitForFunction(() => document.querySelector('#inputCaptcha').value==='32364');
  reports.push('Replacement image element is detected.');
  await page.evaluate(() => document.querySelector('#imgCode').src='/fixture/bad.jpg');
  await page.waitForFunction(() => document.querySelector('#ezpost-ocr-status')?.dataset.state==='error');
  reports.push('Broken image shows a manual-entry message.');
  const allowed = ['/Account/Login?ReturnUrl=%2FHome','/Account/Login#test'];
  for (const url of allowed) {
    await page.goto(base+url);
    await page.waitForFunction(() => document.querySelector('#inputCaptcha').value==='01493');
  }
  reports.push('Login query strings and fragments are supported.');
  const blocked = [base+'/Account/LoginExtra',base+'/Account/Login/',base+'/Account/ForgotPd',
    base+'/account/login','http://ezpost.post.gov.tw/Account/Login','https://example.com/Account/Login'];
  for (const url of blocked) {
    await page.goto(url);
    await page.waitForTimeout(200);
    assert.equal(await page.locator('#inputCaptcha').inputValue(),'',url);
    assert.equal(await page.locator('#ezpost-ocr-status').count(),0,url);
  }
  reports.push('Six disallowed path, scheme and host cases do not activate.');

  // Browser canvas decoding + JS inference, compared with every Python result.
  await page.goto(base+'/Account/ForgotPd');
  await page.addScriptTag({path:path.join(extension,'model.js')});
  await page.addScriptTag({path:path.join(extension,'ocr.js')});
  const names = (await fs.readdir(path.join(root,'dataset'))).filter(n=>n.endsWith('.jpg')).sort();
  const predictions = await page.evaluate(async names => {
    const model=EZPostOCR.loadModel(EZPostModel), canvas=document.createElement('canvas');
    canvas.width=100;canvas.height=40;
    const ctx=canvas.getContext('2d',{willReadFrequently:true}), predictions=[];
    for(const name of names){
      const img=new Image();img.src='/fixture/'+name;await img.decode();ctx.drawImage(img,0,0);
      const result=EZPostOCR.recognize(ctx.getImageData(0,0,100,40),model);
      predictions.push({filename:name,...result});
    }
    return predictions;
  },names);
  await fs.writeFile(path.join(root,'.local/browser_predictions.json'),JSON.stringify(predictions,null,2));
  assert.equal(predictions.length,1000);
  reports.push('Browser decoded and recognized all 1,000 dataset images.');
  const expected = readCsv(await fs.readFile(path.join(root,'reports/predictions.csv'),'utf8'));
  const byName = new Map(predictions.map(row=>[row.filename,row]));
  assert.equal(expected.length,predictions.length);
  for(const row of expected) assert.equal(byName.get(row['檔名'])?.text,row['辨識結果'],row['檔名']);
  const labels = readCsv(await fs.readFile(path.join(root,'data/labels.csv'),'utf8'))
    .filter(row=>row.split.startsWith('holdout'));
  const correct = labels.filter(row=>byName.get(row.filename)?.text===row.label).length;
  assert.equal(correct,80);
  const metrics = {images:predictions.length,pythonDisagreements:0,holdoutImages:labels.length,
    holdoutCorrect:correct,reviewImages:predictions.filter(row=>row.review).length};
  reports.push('All predictions match Python; 80/80 held-out labels match.');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({checks:reports,metrics,pageErrors:errors},null,2));
  await fs.writeFile(path.join(root,'reports/integration_results.json'),JSON.stringify({checks:reports,metrics,pageErrors:errors},null,2));
} finally { await session.close(); }
