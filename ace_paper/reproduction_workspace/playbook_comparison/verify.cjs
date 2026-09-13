const {chromium}=require('/Users/tom/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
  assert.equal(await page.locator('#initial .entry').count(),8);
  assert.equal(await page.locator('#offline .entry').count(),318);
  assert.equal(await page.locator('.section-nav button').count(),8);
  assert.equal(await page.evaluate(()=>/[\uac00-\ud7af]/.test(document.body.innerText)),false);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.getByRole('button',{name:'Verification',exact:true}).click();
  for(const key of ['initial','offline']){
   const offset=await page.evaluate(key=>document.getElementById(key+'-section-5').getBoundingClientRect().top-document.getElementById(key).getBoundingClientRect().top,key);
   assert.ok(Math.abs(offset-12)<3);
  }
  await page.getByRole('button',{name:'Strategies',exact:true}).click();
  await page.screenshot({path:path.join(__dirname,'desktop.png')});
  await page.locator('#offline').evaluate(n=>n.scrollTop=1500);
  const initialScroll=await page.locator('#initial').evaluate(n=>n.scrollTop);
  assert.ok(await page.locator('#offline').evaluate(n=>n.scrollTop)>0);
  assert.equal(await page.locator('#initial').evaluate(n=>n.scrollTop),initialScroll);
  await page.locator('#offline').evaluate(n=>n.scrollTop=0);
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(__dirname,'mobile.png')});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  const left=await page.locator('#initial').boundingBox(),right=await page.locator('#offline').boundingBox();
  assert.ok(left.x+left.width<=right.x+1);
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('PASS: two panels, all source entries, independent scrolling, mobile layout, no browser errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
