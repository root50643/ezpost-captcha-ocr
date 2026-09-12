import fs from 'node:fs/promises';
import path from 'node:path';
import {root, launchExtension} from './helpers.mjs';
const session=await launchExtension('live-');
const {context}=session;
const outputs=[];
try{
 const page=await context.newPage();
 await page.goto('https://ezpost.post.gov.tw/Account/Login',{waitUntil:'domcontentloaded'});
 for(let i=0;i<3;i++){
  if(i){
   const old=await page.locator('#imgCode').getAttribute('src');
   await page.locator('#SetImgCodeLink').click();
   await page.waitForFunction(old=>document.querySelector('#imgCode').getAttribute('src')!==old,old);
  }
  await page.waitForFunction(()=>document.querySelector('#ezpost-ocr-status')?.dataset.state.match(/filled|review/));
  // Wait for the new image's load and the extension's debounced decode.
  await page.locator('#imgCode').evaluate(img=>img.decode());
  await page.waitForTimeout(200);
  await page.locator('#imgCode').screenshot({path:path.join(root,`docs/assets/live-captcha-${i+1}.png`)});
  outputs.push({result:await page.locator('#inputCaptcha').inputValue(),
    status:await page.locator('#ezpost-ocr-status').textContent(),
    size:await page.locator('#imgCode').evaluate(img=>[img.naturalWidth,img.naturalHeight])});
 }
 console.log(JSON.stringify(outputs,null,2));
 await fs.writeFile(path.join(root,'reports/live_results.json'),JSON.stringify(outputs,null,2));
 await page.locator('#form-login').screenshot({path:path.join(root,'docs/assets/live-form.png')});
}finally{await session.close();}
