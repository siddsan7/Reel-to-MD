// DOM simulation only: no browser, network, or filesystem writes.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const script = fs.readFileSync(process.argv[2], 'utf8');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.events = {}; this.value = ''; }
  append(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  addEventListener(name, action) { this.events[name] = action; }
  remove() {}
  click() { if (this.events.click) this.events.click({target: this}); }
}
const nodes = new Map();
let downloaded;
let sequence = 0;
const context = vm.createContext({
  document: {body: new Element('body'), createElement: tag => new Element(tag),
    getElementById: id => { if (!nodes.has(id)) nodes.set(id, new Element(id)); return nodes.get(id); }},
  TextDecoder, Uint8Array, atob, structuredClone,
  crypto: {randomUUID: () => String(++sequence).padStart(8,'0')+'-0000-0000-0000-000000000000'},
  Blob: class { constructor(parts) { this.content = parts.join(''); } },
  URL: {createObjectURL: blob => {downloaded = blob.content; return 'blob:test';}, revokeObjectURL() {}},
  setTimeout: callback => callback(),
});
(async () => {
  vm.runInContext(script, context, {timeout: 2000});
  assert.ok(nodes.get('units').children.length > 0);
  const firstCard=nodes.get('units').children[0];
  const span=firstCard.children[1].children[0];
  span.selectionStart=3;span.selectionEnd=4;firstCard.children[2].click();
  assert.equal(vm.runInContext("review.units.find(u=>u.path==='/title'&&u.text==='A').start",context),2);
  assert.equal(vm.runInContext("review.units.find(u=>u.path==='/title'&&u.text==='A').end",context),3);
  const reviewer = nodes.get('metadata').children[0].children[0];
  reviewer.value = 'Offline test reviewer'; reviewer.events.input();
  nodes.get('addFact').click();
  assert.equal(nodes.get('facts').children.length, 1);
  assert.equal(vm.runInContext('review.reviewer', context), 'Offline test reviewer');
  const target = nodes.get('target');
  target.value = '{ incomplete draft'; target.events.input();
  nodes.get('addGap').click();
  assert.equal(nodes.get('target').value, '{ incomplete draft');
  nodes.get('download').click(); // Accept/pending decisions do not export a correction.
  const saved = JSON.parse(downloaded);
  assert.equal(saved.reviewer, 'Offline test reviewer');
  assert.equal(saved.facts.length, 1);
  assert.equal(saved.gaps.length, 1);
  assert.equal(saved.corrected_target, null);
  const resume = nodes.get('resume');
  saved.reviewer = 'Resumed reviewer';
  await resume.events.change({target: {files: [{size: 1000, text: async () => JSON.stringify(saved)}]}});
  assert.equal(vm.runInContext('review.reviewer', context), 'Resumed reviewer');
  saved.source_digest = 'wrong-source';
  await resume.events.change({target: {files: [{size: 1000, text: async () => JSON.stringify(saved)}]}});
  assert.match(nodes.get('message').textContent, /Different review/);
  console.log('Offline page DOM simulation passed; no browser/network access used.');
})().catch(error => {console.error(error);process.exitCode = 1;});
