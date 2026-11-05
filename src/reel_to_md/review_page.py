"""Self-contained offline review page. Source content is text, never markup."""
import base64
import hashlib
import json


def render_page(source, review):
    encode = lambda value: base64.b64encode(json.dumps(value, ensure_ascii=False, allow_nan=False).encode()).decode()
    script = SCRIPT.replace("SOURCE_BASE64", encode(source)).replace("REVIEW_BASE64", encode(review))
    checksum = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    return """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-CHECKSUM'; style-src 'unsafe-inline'; img-src 'self' file:; media-src 'self' file:; connect-src 'none'; base-uri 'none'; form-action 'none'; object-src 'none'">
<title>Local source review</title><style>
body{font:16px/1.5 system-ui,sans-serif;margin:auto;max-width:1400px;padding:24px;color:#15202b;background:#f5f6f8}h1,h2{line-height:1.2}main{display:grid;grid-template-columns:minmax(280px,1fr) minmax(360px,1.3fr);gap:24px}section,.card{background:white;border:1px solid #ccd3dc;border-radius:10px;padding:16px;margin-bottom:16px}label{display:block;margin:12px 0 4px}input:not([type=checkbox]),select,textarea{box-sizing:border-box;width:100%;padding:9px;border:1px solid #8a97a5;border-radius:5px;font:inherit}textarea{min-height:100px;font:13px/1.5 ui-monospace,monospace}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f2f5;padding:12px}button{padding:10px 16px;margin:8px 8px 8px 0;cursor:pointer}img,video{max-width:100%}.muted{color:#465465}.status{padding:12px;border:2px solid #356b42}summary{cursor:pointer}a{color:#174fad}@media(max-width:900px){main{display:block}}:focus-visible{outline:3px solid #2770d7;outline-offset:2px}
</style><h1>Local source review</h1><p>No network requests or model calls. Changes stay in this page until you download the annotation file. Downloading does not finalize or approve an export.</p>
<p id="identity" class="status"></p><p id="message" role="status" aria-live="polite"></p>
<button id="download" type="button">Download annotations</button><label>Resume annotations from this review<input id="resume" type="file" accept=".json,application/json"></label>
<main><div><section><h2>Original source and evidence</h2><div id="source"></div></section><section><h2>Original output</h2><div id="original"></div></section></div>
<div><section><h2>Reviewer and source identity</h2><div id="metadata"></div></section><section><h2>Atomic output judgments</h2><p>Split multi-fact fields in the advanced editor. Include title assertions, steps, commands, conflicts, and factual uncertainty text. Every original field must be covered; mark nonfactual text explicitly.</p><div id="units"></div>
<details><summary>Advanced atomic-unit JSON editor</summary><textarea id="advanced" aria-label="Atomic units JSON"></textarea><button id="applyUnits" type="button">Apply atomic units</button></details></section>
<section><h2>Source fact inventory</h2><p>Watch the video first. Add each reference fact once. Match recovered facts to output unit IDs. Leave unmatched facts with no IDs. Exact technical values preserve case, punctuation, spaces, flags, numbers, and units.</p><div id="facts"></div><button id="addFact" type="button">Add source fact</button></section>
<section><h2>Reference conflicts</h2><div id="conflicts"></div><button id="addConflict" type="button">Add conflict</button></section>
<section><h2>Material gaps and uncertainty</h2><div id="gaps"></div><button id="addGap" type="button">Add material gap</button></section>
<section><h2>Decision and corrected draft</h2><p>Original scores always use the original output. An edit produces a separate target and Markdown export, validated against the original evidence. To score that edited target, create a separate reviewed-variant review.</p><div id="decision"></div><label>Corrected structured target (edit decision only)<textarea id="target" rows="18"></textarea></label></section></div></main>
<script>SCRIPT</script></html>""".replace("CHECKSUM", checksum).replace("SCRIPT", script)


SCRIPT = r"""
'use strict';
const decode=s=>JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(s),c=>c.charCodeAt(0))));
const source=decode('SOURCE_BASE64'); let review=decode('REVIEW_BASE64');
let targetDraft=JSON.stringify(review.corrected_target??source.target,null,2);
const el=(tag,text,parent)=>{const e=document.createElement(tag);if(text!==null)e.textContent=text;if(parent)parent.append(e);return e;};
const clear=id=>{const e=document.getElementById(id);e.replaceChildren();return e;};
const message=text=>{document.getElementById('message').textContent=text;};
function field(parent,title,obj,key,type='text'){
 const label=el('label',title,parent),input=el(type==='textarea'?'textarea':'input',null,label);
 if(type!=='textarea')input.type=type;
 if(type==='checkbox')input.checked=obj[key];else input.value=obj[key]??'';
 input.addEventListener('input',()=>{obj[key]=type==='checkbox'?input.checked:type==='number'?Number(input.value):input.value;});return input;
}
function select(parent,title,obj,key,choices){
 const label=el('label',title,parent),input=el('select',null,label);
 for(const [value,text]of choices){const option=el('option',text,input);option.value=JSON.stringify(value);}
 input.value=JSON.stringify(obj[key]);input.addEventListener('change',()=>{obj[key]=JSON.parse(input.value);});return input;
}
const boolean=[[null,'Pending'],[true,'Yes'],[false,'No']];
function listField(parent,title,obj,key){const input=field(parent,title,{value:obj[key].join(', ')},'value');input.addEventListener('input',()=>{obj[key]=input.value.split(',').map(s=>s.trim()).filter(Boolean);});}
function sourceView(){
 document.getElementById('identity').textContent=`${source.synthetic?'SYNTHETIC CHALLENGE':'NATURAL OR UNCLASSIFIED CLIP'} · ${source.variant} · schema ${source.validity.schema?'valid':'invalid/missing'} · semantic ${source.validity.semantic?'valid':'invalid/missing'}`;
 const box=clear('source');
 el('p',source.video_matches_run?'Video hash matches pipeline input.':source.video?'Legacy attempt: manually confirm this video belongs to the run.':'No original video supplied. Natural-clip finalization requires one.',box);
 if(source.video){const video=el('video',null,box);video.controls=true;video.preload='none';video.src=source.video.file;}
 for(const item of source.assets.filter(a=>'seconds'in a)){const d=el('details',null,box);el('summary',`Selected frame at ${item.seconds}s`,d);const image=el('img',null,d);image.loading='lazy';image.alt=`Selected original frame at ${item.seconds} seconds`;image.src=item.file;}
 el('pre',JSON.stringify(source.evidence.channels,null,2),box);
 for(const item of source.evidence.evidence){el('h3',`${item.id} · ${item.kind} · ${item.start_seconds}–${item.end_seconds}s · ${item.review_flag}`,box);el('pre',item.text,box);}
 el('pre',JSON.stringify(source.target,null,2),clear('original'));
 if(source.raw_response){const d=el('details',null,document.getElementById('original'));el('summary','Original model response',d);el('pre',source.raw_response,d);}
}
function render(){
 const metadata=clear('metadata');
 for(const [key,title]of [['reviewer','Reviewer name'],['clip_key','Clip key (same original clip across conditions)'],['source_group','Creator/source group'],['condition','Condition (B0/B1/T0/A1/A2 or a documented label)']])field(metadata,title,review,key);
 select(metadata,'Evaluation partition',review,'split',[['development','Development'],['challenge','Challenge (required for synthetic fixtures)']]);
 field(metadata,'Review minutes',review,'review_minutes','number');
 for(const [key,title]of [['source_reviewed','I watched the original source (not only these extracts).'],['source_matches_attempt','I confirmed this is the source video for this attempt.'],['unit_coverage_confirmed','I checked every output field and split factual assertions into atomic units.'],['reference_inventory_complete','I completed the fact, conflict, and material-gap inventory, including omissions.']])field(metadata,title,review,key,'checkbox');
 const units=clear('units');
 for(const unit of review.units){const card=el('div',null,units);card.className='card';el('h3',`${unit.id} · ${unit.path} · span ${unit.start}:${unit.end}`,card);
 const spanLabel=el('label','Original span (select text to split an assertion)',card),spanBox=el('textarea',null,spanLabel);spanBox.value=unit.text;spanBox.readOnly=true;
 const split=el('button','Split selected assertion',card);split.type='button';split.addEventListener('click',()=>{
 const selectionA=spanBox.selectionStart,selectionB=spanBox.selectionEnd;if(!Number.isInteger(selectionA)||!Number.isInteger(selectionB)){message('Select part of the original span first.');return;}
 const chars=Array.from(unit.text),a=Array.from(unit.text.slice(0,selectionA)).length,b=Array.from(unit.text.slice(0,selectionB)).length;
 if(a===b||(a===0&&b===chars.length)){message('Select part of the original span first.');return;}
 const pieces=[[0,a],[a,b],[b,chars.length]].filter(([lo,hi])=>chars.slice(lo,hi).join('').trim()).map(([lo,hi])=>({...structuredClone(unit),id:'u'+crypto.randomUUID(),start:unit.start+lo,end:unit.start+hi,text:chars.slice(lo,hi).join(''),factual:null,input_support:null,source_consistent:null,exclusion_reason:'',citations:unit.citations.map(c=>({evidence_id:c.evidence_id,supports:null}))}));
 review.units.splice(review.units.indexOf(unit),1,...pieces);for(const f of review.facts)f.recovered_by=f.recovered_by.filter(id=>id!==unit.id);review.unit_coverage_confirmed=false;review.reference_inventory_complete=false;render();message('Split saved. Judge the new units and remap any reference facts that used the old unit ID.');});
 select(card,'Is this an atomic factual assertion?',unit,'factual',boolean);
 select(card,'Input support (separate from video correctness)',unit,'input_support',[[null,'Pending'],['full','Full'],['partial','Partial'],['none','None']]);
 select(card,'Consistent with original video?',unit,'source_consistent',boolean);field(card,'Reason if excluded as nonfactual',unit,'exclusion_reason');
 for(const citation of unit.citations)select(card,`Does evidence ID ${JSON.stringify(citation.evidence_id)} support this unit? (invalid IDs must be No)`,citation,'supports',boolean);
 }
 document.getElementById('advanced').value=JSON.stringify(review.units,null,2);
 const facts=clear('facts');
 for(const fact of review.facts){const card=el('div',null,facts);card.className='card';field(card,'Reference fact ID',fact,'id');field(card,'Source fact',fact,'text','textarea');
 for(const [key,title]of [['important','Important fact'],['source_supported','Supported by original video'],['input_available','Recoverable from extracted model input']])field(card,title,fact,key,'checkbox');
 listField(card,'Recovered by output unit IDs (comma-separated)',fact,'recovered_by');
 const technical=field(card,'Expected exact technical value (leave empty for nontechnical facts)',fact,'technical_value');technical.addEventListener('input',()=>{fact.technical_value=technical.value||null;});
 select(card,'Was an answerable fact incorrectly marked unknown?',fact,'incorrectly_unknown',boolean);const remove=el('button','Remove fact',card);remove.type='button';remove.addEventListener('click',()=>{review.facts=review.facts.filter(f=>f!==fact);render();});}
 for(const name of ['conflicts','gaps']){const box=clear(name);for(const item of review[name]){const card=el('div',null,box);card.className='card';field(card,'Reference item ID',item,'id');field(card,'Reference description',item,'text','textarea');select(card,'Correctly represented in the original output?',item,'represented',boolean);listField(card,'Supporting output paths (e.g. /unknowns/0/text)',item,'output_paths');const remove=el('button','Remove item',card);remove.type='button';remove.addEventListener('click',()=>{review[name]=review[name].filter(i=>i!==item);render();});}}
 const decision=clear('decision');select(decision,'Review decision',review,'decision',[['pending','Pending'],['accept','Accept'],['edit','Edit'],['reject','Reject']]);field(decision,'Review notes',review,'notes','textarea');
 document.getElementById('target').value=targetDraft;
}
document.getElementById('applyUnits').addEventListener('click',()=>{try{const units=JSON.parse(document.getElementById('advanced').value);if(!Array.isArray(units))throw Error('Expected an array');review.units=units;render();message('Atomic units applied. Finalization will validate coverage and labels.');}catch(e){message('Cannot apply units: '+e.message);}});
document.getElementById('addFact').addEventListener('click',()=>{review.facts.push({id:'f'+crypto.randomUUID().slice(0,8),text:'',important:true,source_supported:true,input_available:true,recovered_by:[],technical_value:null,incorrectly_unknown:null});render();});
for(const [id,name,prefix]of [['addConflict','conflicts','c'],['addGap','gaps','g']])document.getElementById(id).addEventListener('click',()=>{review[name].push({id:prefix+crypto.randomUUID().slice(0,8),text:'',represented:null,output_paths:[]});render();});
document.getElementById('target').addEventListener('input',()=>{targetDraft=document.getElementById('target').value;});
document.getElementById('download').addEventListener('click',()=>{try{const saved=structuredClone(review);saved.corrected_target=saved.decision==='edit'?JSON.parse(document.getElementById('target').value):null;const url=URL.createObjectURL(new Blob([JSON.stringify(saved,null,2)+'\n'],{type:'application/json'}));const anchor=el('a',null,document.body);anchor.href=url;anchor.download='review-'+saved.review_id+'.json';anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);message('Annotations downloaded. Put the file next to source.json, then run review-finalize. Original files are unchanged.');}catch(e){message('Cannot download: '+e.message);}});
document.getElementById('resume').addEventListener('change',async event=>{try{const file=event.target.files[0];if(!file)return;if(file.size>8*1024*1024)throw Error('File too large');const loaded=JSON.parse(await file.text());if(loaded.review_id!==review.review_id||loaded.source_digest!==review.source_digest)throw Error('Different review/source identity');review=loaded;targetDraft=JSON.stringify(review.corrected_target??source.target,null,2);render();message('Annotations resumed. Finalization checks all labels.');}catch(e){message('Cannot resume: '+e.message);}});
sourceView();render();
"""
