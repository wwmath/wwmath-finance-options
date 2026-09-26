// Headless check of the time machine: renders, no page errors, no sideways scroll on a
// phone, formulas typeset, and the as-of replay shows the right record at three dates.
import { chromium } from "playwright-core";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const types = { ".html": "text/html", ".js": "text/javascript" };
const server = createServer(async (req, res) => {
  const p = path.join(root, decodeURIComponent(new URL(req.url, "http://x").pathname).replace(/\/$/, "/index.html"));
  let body;
  try { body = await readFile(p); } catch { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "content-type": types[path.extname(p)] ?? "application/octet-stream" });
  res.end(body);
}).listen(0);
const port = server.address().port;
const base = process.env.PLAYWRIGHT_BROWSERS_PATH ?? "/opt/pw-browsers";
const exe = readdirSync(base).filter((d) => d.startsWith("chromium-"))
  .map((d) => path.join(base, d, "chrome-linux", "chrome")).find(existsSync);

const browser = await chromium.launch({ executablePath: exe });
const failures = [];
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
// external fonts are unreachable from this sandbox; only local resources must load
const external = (u) => /fonts\.googleapis|fonts\.gstatic|google\.com|favicon\.ico/.test(u);
page.on("requestfailed", (r) => !external(r.url()) && errors.push(`request failed: ${r.url()}`));
page.on("response", (r) => r.status() >= 400 && !external(r.url()) && errors.push(`HTTP ${r.status()}: ${r.url()}`));
await page.goto(`http://localhost:${port}/#heston1993`);
await page.waitForSelector(".vis-item.vis-box");
await page.waitForFunction(() => document.querySelectorAll("#detail mjx-container svg").length > 5, null, { timeout: 30000 });
await page.click("#zoom-all");
await page.waitForTimeout(700);
const boxes = await page.locator(".vis-item.vis-box").count();
const svgs = await page.locator("#detail mjx-container svg").count();
console.log(`timeline boxes rendered: ${boxes}; Heston formulas typeset: ${svgs}`);

async function asOf(year) {
  await page.fill("#asof-year", String(year));
  await page.dispatchEvent("#asof-year", "change");
  await page.waitForTimeout(150);
  const works = await page.locator("#record ol.known li").count();
  const head = await page.textContent("#record h2");
  const notes = await page.locator("#record .note").allTextContents();
  return { works, head, notes };
}
for (const [y, expect] of [[-300, 1], [1993, 5], [2026, 13]]) {
  const r = await asOf(y);
  console.log(`as of ${String(y).padStart(5)}: ${r.head.padEnd(14)} ${r.works} works known` + (r.notes.length ? `; notes: ${r.notes.length}` : ""));
  if (r.works !== expect) failures.push(`as of ${y}: expected ${expect} works, saw ${r.works}`);
}
const r1996 = await asOf(1996);
if (!r1996.notes.some((n) => /Bates/.test(n) && /Albrecher/.test(n))) failures.push("1996: missing the Bates/Albrecher as-of note");
else console.log("as of  1996: Bates note present:", r1996.notes.find((n) => /Bates/.test(n)).slice(0, 90) + "…");
await asOf(2026);
await page.screenshot({ path: path.join(root, "test", "desktop.png"), fullPage: true });

const phone = await browser.newPage({ viewport: { width: 390, height: 844 } });
await phone.goto(`http://localhost:${port}/`);
await phone.waitForSelector(".vis-item.vis-box");
const overflow = await phone.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
await phone.screenshot({ path: path.join(root, "test", "phone.png"), fullPage: false });
await browser.close(); server.close();
if (overflow) failures.push("horizontal page scroll at 390px");
if (errors.length) failures.push(...errors.map((e) => "page error: " + e));
if (boxes < 13) failures.push(`only ${boxes} works rendered`);
console.log(failures.length ? "FAIL\n" + failures.join("\n") : "OK (browser)");
process.exit(failures.length ? 1 : 0);
