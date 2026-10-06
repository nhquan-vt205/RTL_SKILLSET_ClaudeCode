import { JSDOM } from 'jsdom';
import fs from 'fs';
const dom = new JSDOM('<!DOCTYPE html><body></body>');
globalThis.window = dom.window; globalThis.document = dom.window.document;
try { globalThis.navigator = dom.window.navigator; } catch(e) {}
globalThis.DOMParser = dom.window.DOMParser; globalThis.Element = dom.window.Element;
const { default: mermaid } = await import('mermaid');
mermaid.initialize({ startOnLoad: false });
let bad = 0;
for (const f of process.argv.slice(2)) {
  const txt = fs.readFileSync(f, 'utf8');
  try { const r = await mermaid.parse(txt); console.log('PARSE OK  ', f, r?.diagramType ?? ''); }
  catch (e) { bad++; console.log('PARSE FAIL', f, '\n', String(e.message || e).slice(0, 600)); }
}
process.exit(bad ? 1 : 0);
