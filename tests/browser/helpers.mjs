import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const extension = path.join(root, 'extension');

export async function launchExtension(prefix) {
  const profiles = path.join(root, '.local/browser-profiles');
  await fs.mkdir(profiles, {recursive:true});
  const directory = await fs.mkdtemp(path.join(profiles, prefix));
  const context = await chromium.launchPersistentContext(directory, {
    channel: process.env.EZPOST_CHROMIUM_EXECUTABLE ? undefined : 'chromium',
    executablePath: process.env.EZPOST_CHROMIUM_EXECUTABLE || undefined,
    headless: true,
    args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
  });
  return {
    context,
    async close() {
      await context.close();
      const relative = path.relative(profiles, path.resolve(directory));
      if (!relative || relative.startsWith('..') || path.isAbsolute(relative))
        throw new Error('Refusing to remove a profile outside the test profile directory');
      await fs.rm(directory, {recursive:true,force:true,maxRetries:5,retryDelay:200});
    },
  };
}

export function readCsv(text) {
  const rows=[];let row=[],field='',quoted=false;
  text=text.replace(/^\uFEFF/,'');
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(c==='"'){
      if(quoted&&text[i+1]==='"'){field+='"';i++;}else quoted=!quoted;
    }else if(!quoted&&(c===','||c==='\n')){
      row.push(field.replace(/\r$/,''));field='';
      if(c==='\n'){rows.push(row);row=[];}
    }else field+=c;
  }
  if(field||row.length){row.push(field.replace(/\r$/,''));rows.push(row);}
  const header=rows.shift();
  return rows.filter(r=>r.some(Boolean)).map(r=>Object.fromEntries(header.map((h,i)=>[h,r[i]])));
}
