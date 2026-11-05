"use strict";
const $ = id => document.getElementById(id);
const state = {token: null, jobs: [], selected: null, resultKey: null, uploading: false, file: null};
const labels = {queued:"Queued", starting:"Starting", running:"Processing", cancelling:"Cancelling", complete:"Draft ready", partial:"Draft ready · partial", failed:"Failed", cancelled:"Cancelled", interrupted:"Interrupted", needs_attention:"Recovery needs a choice"};
const stages = [["probe","Inspect video"],["frames","Select frames"],["audio","Transcribe"],["ocr","Read screen"],["vision","Describe visuals"],["target","Draft notes"],["validation","Validate"]];
function node(tag, text, className) { const el=document.createElement(tag); if(text!==undefined)el.textContent=text; if(className)el.className=className; return el; }
function showError(message) {$('error').textContent=message;$('error').hidden=false;}
async function api(path, body) {
  const options=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Reel-Token':state.token},body:JSON.stringify(body)};
  const response=await fetch(path,options);const data=await response.json();if(response.status===403)state.token=null;if(!response.ok)throw Error(data.error||'Local request failed.');return data;
}
function newVideo() {state.selected=null;state.resultKey=null;location.hash='';$('upload-view').hidden=false;$('job-view').hidden=true;renderJobs();}
function select(id) {if(state.selected!==id){state.resultKey=null; $('notes').replaceChildren(node('p','Notes appear here after synthesis and validation. Completed evidence is available even when drafting fails.','placeholder'));$('frames').replaceChildren();$('evidence').replaceChildren();$('frame-count').textContent='';$('evidence-count').textContent='';$('review-label').textContent='Awaiting processing';$('source-video').src=`/api/jobs/${id}/video`;}
  state.selected=id;location.hash=id;$('upload-view').hidden=true;$('job-view').hidden=false;renderJobs();renderSelected();}
function renderJobs(){ const key=JSON.stringify([state.selected,state.jobs.map(j=>[j.id,j.name,j.status])]);if(state.jobsKey===key)return;state.jobsKey=key; $('job-count').textContent=state.jobs.length;const list=$('jobs');list.replaceChildren();if(!state.jobs.length)list.append(node('p','Your videos will appear here.','quiet'));
  for(const job of state.jobs){const button=node('button',undefined,'job-row'+(state.selected===job.id?' selected':''));button.type='button';button.setAttribute('aria-current',state.selected===job.id?'true':'false');button.append(node('strong',job.name),node('small',labels[job.status]||job.status));button.onclick=()=>select(job.id);list.append(button);}}
function formatTime(seconds){seconds=Math.max(0,Math.floor(seconds));return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;}
async function renderSelected(){const job=state.jobs.find(j=>j.id===state.selected);if(!job)return;
  $('job-title').textContent=job.name;$('status').textContent=labels[job.status]||job.status;$('job-message').textContent=job.message;
  const active=stages.find(([key])=>job.stage&&(job.stage===key||job.stage.startsWith(key+'-')));
  $('stage-title').textContent=job.status==='running'?(active?active[1]:'Checking local configuration'):labels[job.status]||job.status;
  const activeJob=['running','starting','cancelling'].includes(job.status);$('cancel-button').hidden=!['running','starting','queued'].includes(job.status);$('resume-button').hidden=!job.can_resume;$('export-button').hidden=!job.can_export;$('export-button').href=`/api/jobs/${job.id}/markdown`;
  const elapsed=job.started_utc?(Date.parse(activeJob?new Date().toISOString():job.updated_utc)-Date.parse(job.started_utc))/1000:0;
  $('elapsed').textContent=job.started_utc?formatTime(elapsed)+(activeJob?' elapsed':' processing time'):'';
  $('stages').replaceChildren();for(const [key,label] of stages){const row=job.stages.find(r=>r.name===key||r.name.startsWith(key+'-'));const current=active&&active[0]===key;
    const item=node('li',label,row?(row.status==='success'?'done':'failed'):current?'active':'');if(row)item.append(node('small',row.cache_hit?'Reused':row.status==='success'?'Done':'Unavailable'));if(key==='validation'&&job.validation!=='not_run'){item.className=job.validation==='passed'?'done':'failed';item.append(node('small',job.validation==='passed'?'Passed':'Rejected'));}$('stages').append(item);}
  const key=job.id+':'+job.attempt_count+':'+job.status;if(state.resultKey!==key&&!['queued','starting','running','cancelling'].includes(job.status)){
    state.resultKey=key;try{const value=await api(`/api/jobs/${job.id}/result`);if(state.selected===job.id)renderResult(job,value);}catch(error){if(state.selected===job.id&&job.can_export)showError(error.message);}}
}
function seek(seconds){const video=$('source-video');video.currentTime=seconds;video.focus();}
function refs(ids){const list=node('div',undefined,'citations');for(const id of ids){const button=node('button',id,'citation');button.type='button';button.onclick=()=>{const item=document.getElementById('evidence-'+id);if(item){$('evidence-details').open=true;document.querySelectorAll('.highlight').forEach(e=>e.classList.remove('highlight'));item.classList.add('highlight');item.scrollIntoView({behavior:'auto',block:'nearest'});}};list.append(button);}return list;}
function renderResult(job,value){$('review-label').textContent='Unreviewed draft';const notes=$('notes');notes.replaceChildren();const target=value.target;const bound=value.draft_mode==='bound_excerpts_v1';
  if(target){notes.append(node('div',bound?'Unreviewed source excerpts · Quoted extraction text with bound citations. Recognition, relevance and source fidelity still need review.':'Unreviewed · Check each claim against the video and its evidence. Uncertain extractions remain visible.','draft-notice'),node('h2',target.title,'notes-title'));
    for(const [key,title] of [['claims',bound?'Source excerpts':'Key points'],['steps','Procedure'],['conflicts','Conflicts'],['unknowns','Unknowns'],['omissions','Omissions']]){if(!target[key].length)continue;const section=node('section',undefined,'note-section');section.append(node('h3',title));for(const item of target[key]){const article=node('article',undefined,'note-item');article.append(node('p',(key==='steps'?item.order+'. ':'')+(item.text||item.reason),'note-text'));if(item.attribution)article.append(node('p',item.attribution.replaceAll('_',' '),'attribution'));if(item.command!==undefined&&item.command!==null)article.append(node('pre',item.command));article.append(refs(item.evidence_ids));section.append(article);}notes.append(section);}}
  else{notes.append(node('p','This attempt has no validated draft to export. You can inspect its extracted evidence and recover unfinished work when available.','placeholder'));$('review-label').textContent='No validated draft';}
  $('evidence-count').textContent=value.evidence.evidence.length;$('evidence').replaceChildren();for(const e of value.evidence.evidence){const item=node('article',undefined,'evidence-item');item.id='evidence-'+e.id;item.append(node('b',e.id+' · '+e.kind.replaceAll('_',' ')+(e.review_flag==='uncertain'?' · uncertain':'')));const time=node('button',formatTime(e.start_seconds),'time-button');time.onclick=()=>seek(e.start_seconds);item.append(time,node('p',e.text));$('evidence').append(item);}
  $('frame-count').textContent=value.frames.length;$('frames').replaceChildren();for(const frame of value.frames){const card=node('div',undefined,'frame');const img=node('img');img.src=`/api/jobs/${job.id}/frames/${frame.index}`;img.alt='Selected video frame at '+formatTime(frame.seconds);img.loading='lazy';const time=node('button',formatTime(frame.seconds),'time-button');time.onclick=()=>seek(frame.seconds);card.append(img,time);$('frames').append(card);}
}
async function poll(){try{if(!state.token){const session=await api('/api/session');state.token=session.token;$('mode').textContent=session.mode;$('profile').textContent=session.text_model?`${session.text_model} · local CPU profile`:'Extractive mode · configure local models for transcription and synthesis';}
  state.jobs=await api('/api/jobs');$('connection').hidden=true;renderJobs();if(state.selected){const job=state.jobs.find(j=>j.id===state.selected);if(job)await renderSelected();else newVideo();}}
  catch(error){$('connection').hidden=false;state.token=null;}finally{setTimeout(poll,1200);}}
function chosen(file){if(!file)return;if(file.size>100*1024*1024){state.file=null;$('video-file').value='';$('file-label').textContent='Choose a video or drop it here';showError('Choose a video no larger than 100 MiB.');return;}state.file=file;$('file-label').textContent=file.name;$('error').hidden=true;}
$('video-file').onchange=()=>chosen($('video-file').files[0]);$('new-video').onclick=newVideo;
for(const name of ['dragenter','dragover'])$('drop-zone').addEventListener(name,event=>{event.preventDefault();$('drop-zone').classList.add('dragging');});
for(const name of ['dragleave','drop'])$('drop-zone').addEventListener(name,event=>{event.preventDefault();$('drop-zone').classList.remove('dragging');});
$('drop-zone').addEventListener('drop',event=>{const file=event.dataTransfer.files[0];if(file){const transfer=new DataTransfer();transfer.items.add(file);$('video-file').files=transfer.files;chosen(file);}});
$('upload-form').onsubmit=event=>{event.preventDefault();if(state.uploading||!state.file||!state.token)return;state.uploading=true;$('upload-button').disabled=true;$('upload-progress').hidden=false;$('error').hidden=true;
  const xhr=new XMLHttpRequest();xhr.open('POST','/api/jobs?name='+encodeURIComponent(state.file.name));xhr.setRequestHeader('Content-Type','application/octet-stream');xhr.setRequestHeader('X-Reel-Token',state.token);
  xhr.upload.onprogress=event=>{if(event.lengthComputable){$('upload-meter').value=event.loaded/event.total*100;$('upload-label').textContent=`Uploading to this device · ${Math.round(event.loaded/event.total*100)}%`;}};
  const finish=()=>{state.uploading=false;$('upload-button').disabled=false;$('upload-progress').hidden=true;};
  xhr.onload=()=>{finish();try{const data=JSON.parse(xhr.responseText);if(xhr.status===403)state.token=null;if(xhr.status!==201)throw Error(data.error);state.jobs.unshift(data);select(data.id);$('video-file').value='';state.file=null;$('file-label').textContent='Choose a video or drop it here';}catch(error){showError(error.message||'Upload failed.');}};
  xhr.onerror=()=>{finish();showError('Upload interrupted. Reconnect to the local app and select the video again.');};xhr.send(state.file);};
$('cancel-button').onclick=async()=>{try{await api(`/api/jobs/${state.selected}/cancel`,{});}catch(error){showError(error.message);}};
$('resume-button').onclick=()=>{$('retry-ack').checked=false;$('recovery-dialog').showModal();};
$('recovery-dialog').addEventListener('close',async()=>{if($('recovery-dialog').returnValue!=='resume')return;try{await api(`/api/jobs/${state.selected}/resume`,{acknowledge_model_retry:$('retry-ack').checked});state.resultKey=null;}catch(error){showError(error.message);}});
state.selected=/^[0-9a-f]{32}$/.test(location.hash.slice(1))?location.hash.slice(1):null;
if(state.selected){$('upload-view').hidden=true;$('job-view').hidden=false;$('source-video').src=`/api/jobs/${state.selected}/video`;}
window.addEventListener('hashchange',()=>{const id=location.hash.slice(1);if(/^[0-9a-f]{32}$/.test(id)){if(state.selected!==id)select(id);}else if(state.selected)newVideo();});
poll();
