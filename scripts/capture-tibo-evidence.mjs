import { chromium } from 'playwright';
import fs from 'node:fs';

const POST_ID = '2098685367058612394';
const OUT = 'assets/tibo/' + POST_ID + '.png';
fs.mkdirSync('assets/tibo', { recursive: true });

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1200, height: 300 },
    deviceScaleFactor: 1,
    colorScheme: 'light'
  });
  const url = 'https://platform.twitter.com/embed/Tweet.html?id=' + POST_ID + '&dnt=true&theme=light';
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const body = await page.locator('body').innerText({ timeout: 20000 });
  if (!body.includes('Reset all propagated. Sweet dreams.') || !body.includes('thsottiaux')) {
    throw new Error('X embed did not contain the expected Tibo post. Capturing is aborted.');
  }
  await page.addStyleTag({ content: `
    html,body{margin:0!important;padding:0!important;background:#fff!important;overflow:hidden!important}
    body{width:1200px!important;min-width:1200px!important}
  `});
  await page.screenshot({ path: OUT, fullPage: false });
  console.log('captured', OUT);
} finally {
  await browser.close();
}
