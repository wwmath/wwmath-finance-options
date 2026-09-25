// End-to-end: serve harness/web, open it in headless Chromium, run the conformance,
// and assert every compiled engine is bit-identical to the Rust reference.
import { chromium } from "playwright-core";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const web = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "web");
const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json",
  ".wasm": "application/wasm" };
const server = createServer(async (req, res) => {
  const p = path.join(web, decodeURIComponent(new URL(req.url, "http://x").pathname).replace(/\/$/, "/index.html"));
  let body;
  try { body = await readFile(p); } catch { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "content-type": types[path.extname(p)] ?? "text/plain; charset=utf-8" });
  res.end(body);
}).listen(0);
const port = server.address().port;

function chromiumPath() {
  // Use a preinstalled Chromium when present (no browser download needed).
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH ?? "/opt/pw-browsers";
  if (!existsSync(base)) return undefined;
  for (const d of readdirSync(base).filter((d) => d.startsWith("chromium-"))) {
    for (const rel of ["chrome-linux/chrome", "chrome-linux64/chrome"]) {
      const p = path.join(base, d, rel);
      if (existsSync(p)) return p;
    }
  }
  return undefined;
}

const browser = await chromium.launch({ executablePath: chromiumPath() });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(`http://localhost:${port}/`);
await page.waitForFunction(() => window.__conformance, null, { timeout: 120000 });
const status = await page.textContent("#status");
const result = await page.evaluate(() => window.__conformance.res);
await page.screenshot({ path: path.join(web, "..", "test", "screenshot.png"), fullPage: true });
const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
await mobile.goto(`http://localhost:${port}/`);
await mobile.waitForFunction(() => window.__conformance, null, { timeout: 120000 });
const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
await browser.close();
server.close();

console.log(status.trim());
for (const e of result.engines) console.log(`${e.name.padEnd(8)} ${e.elapsed_ms.toFixed(1).padStart(7)} ms  ${e.bit_identical ? "bit-identical" : "DIFF " + e.max_abs_path_diff}`);
const ok = !errors.length && result.engines.every((e) => e.bit_identical) && !overflow;
if (errors.length) console.log("page errors:", errors);
if (overflow) console.log("FAIL: horizontal page scroll at 390px");
console.log(ok ? "OK (browser)" : "FAIL (browser)");
process.exit(ok ? 0 : 1);
