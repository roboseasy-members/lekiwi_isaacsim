'use strict';
const $ = id => document.getElementById(id);
const key = location.hash.slice(1) || sessionStorage.getItem('lekiwiKey') || '';
if (key) sessionStorage.setItem('lekiwiKey', key);
history.replaceState(null, '', '/');
let busy = false, previous = '', previewUrls = [];
const selected = () => [...document.querySelectorAll('.episode input:checked')].map(e => e.value);
async function api(path, data) {
  const response = await fetch(path, {method: data ? 'POST' : 'GET', headers: {'X-LeKiwi-Key': key, ...(data ? {'Content-Type': 'application/json'} : {})}, ...(data ? {body: JSON.stringify(data)} : {})});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || '요청 실패');
  return value;
}
function notice(text, error = false) { $('notice').textContent = text; $('notice').classList.toggle('error', error); }
function controls() {
  document.querySelectorAll('button,input,select').forEach(e => e.disabled = busy);
}
function resultText(operation, result) {
  if(operation==='export') return `변환 완료: ${result.name}\n${result.episodes}편 · ${result.frames}프레임\n로컬 데이터셋 목록에서 선택할 수 있습니다.`;
  if(operation==='inspect') return `검사 완료: ${result.name}\n${result.episodes}편 · ${result.frames}프레임\n저장 위치: ${result.path}\n이 데이터셋을 로컬 학습에 사용할 수 있습니다. 작업 성공률은 별도 평가가 필요합니다.`;
  return '완료되었습니다.';
}
async function job(operation, args = {}) {
  try { busy = true; controls(); await api('/api/job', {operation, ...args}); previous = ''; await poll(); }
  catch (e) { busy = false; controls(); notice(e.message, true); }
}
async function preview(id) {
  try {
    const blobs = await Promise.all(['front', 'wrist'].map(async camera => {
      const r = await fetch('/api/preview?' + new URLSearchParams({episode:id,camera}), {headers:{'X-LeKiwi-Key':key}});
      if (!r.ok) throw new Error('미리보기를 읽을 수 없습니다.');
      return r.blob();
    }));
    previewUrls.forEach(URL.revokeObjectURL); previewUrls = blobs.map(URL.createObjectURL);
    ['front','wrist'].forEach((camera,i) => { $(camera).src = previewUrls[i]; $(camera).hidden = false; });
  } catch(e) { notice(e.message,true); }
}
async function refresh() {
  const data = await api('/api/list'), checked = selected(), old = $('datasets').value;
  $('episodes').replaceChildren();
  if (!data.episodes.length) $('episodes').textContent = '완료된 시연이 없습니다. Isaac Sim에서 기록 후 Save episode를 눌러주세요.';
  for (const e of data.episodes) {
    const row = document.createElement('div'); row.className='episode';
    const check=document.createElement('input'); check.type='checkbox'; check.value=e.id; check.checked=checked.includes(e.id); check.setAttribute('aria-label',e.id);
    const text=document.createElement('span'); text.textContent=`${e.id} · ${e.frames} 프레임 · ${e.success ? '성공 표시' : '성공 미표시'}\n${e.task} · ${e.source}`;
    const button=document.createElement('button'); button.textContent='첫 화면'; button.className='secondary'; button.onclick=()=>preview(e.id);
    row.append(check,text,button); $('episodes').append(row);
  }
  $('datasets').replaceChildren();
  for (const d of data.datasets) { const o=document.createElement('option'); o.value=d.name; o.textContent=`${d.name} · ${d.episodes}편 / ${d.frames}프레임`; $('datasets').append(o); }
  if ([...$('datasets').options].some(o=>o.value===old)) $('datasets').value=old;
  controls();
}
const names={'export':'변환·검사','inspect':'데이터셋 검사'};
async function poll() {
  try {
    const state = await api('/api/state'); busy=state.busy; controls();
    if (busy) { notice(`${names[state.operation]} 진행 중… 완료될 때까지 기다려주세요.`); return; }
    const signature=JSON.stringify(state);
    if(signature===previous)return; previous=signature;
    if(state.error){notice(state.error,true);$('result').textContent=state.error;return;}
    if(!state.operation){notice('준비되었습니다. 시연 선택부터 시작하세요.');return;}
    notice(`${names[state.operation]} 완료`); $('result').textContent=resultText(state.operation,state.result);
    if(state.operation==='export') await refresh();
    controls();
  } catch(e){notice(e.message,true);}
}
$('refresh').onclick=()=>refresh().catch(e=>notice(e.message,true));
$('export').onclick=()=>job('export',{episodes:selected(),name:$('exportName').value.trim(),success_only:$('successOnly').checked});
$('inspect').onclick=()=>job('inspect',{name:$('datasets').value});
refresh().catch(e=>notice(e.message,true)); poll(); setInterval(poll,1500);
