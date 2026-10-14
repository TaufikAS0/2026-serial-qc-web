'use strict';
const $ = id => document.getElementById(id);
$('server-address').textContent=location.host;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let token = '', profiles = [], selectedProfile, state, maps, tags = [], busy = false, historySignature = '', currentTab = 'connection', initialized = false;
const showError = error => { $('notice').textContent = error.message || String(error); };
async function api(url, data) {
  const response = await fetch(url, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-Serial-Token':token},body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  return result;
}
async function act(name, data={}) {
  $('notice').textContent = '';
  try { return await api('/api/action/'+name,data); } catch(error) {showError(error); throw error;}
}
function bind(id, fn) { $(id).addEventListener('click', async () => {try {await fn();} catch(error) {showError(error);} }); }
function table(headers, rows) {return `<div class="table-scroll"><table><thead><tr>${headers.map(x=>`<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(value=>`<td>${value}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;}
function download(name, object) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(object,null,2)],{type:'application/json'}));
  const a=document.createElement('a'); a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function raw() {return {format:$('raw-format').value,payload:$('payload').value,encoding:$('encoding').value,ending:$('ending').value,interval:Number($('period').value)};}
function tag() {return {name:$('tag-name').value,unit:Number($('unit').value),function:Number($('function').value),address:Number($('address').value),count:Number($('count').value),type:$('datatype').value,byte_order:$('byte-order').value,word_order:$('word-order').value,scale:Number($('scale').value),offset:Number($('offset').value),timeout:Number($('timeout').value)};}
function tagList() {
  $('tag-list').innerHTML=table(['Nama','Unit / FC','Alamat / count','Tipe',''],tags.map((t,i)=>[esc(t.name),`${t.unit} / ${t.function}`,`${t.address} / ${t.count}`,esc(t.type),`<button data-remove="${i}">Hapus</button>`]));
  document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{tags.splice(Number(b.dataset.remove),1);tagList();});
}
function mapTable() {
  if (!maps) return;
  const fc=$('map-function').value;
  $('map-table').innerHTML=table(['Alamat zero-based','Nilai'],Object.entries(maps.maps[fc]).map(([a,v])=>[esc(a),esc(v)]));
}
const mockPanel=document.createElement('details');
mockPanel.innerHTML='<summary>Master sintetis untuk menguji slave MOCK</summary><label>Request RTU HEX<input id="mock-frame" value="01 03 00 00 00 01 84 0a"></label><button id="mock-inject">Inject request SIMULASI</button><p>Lihat request/response pada Terminal. Tidak mengakses COM.</p>';
$('map-table').after(mockPanel);
async function loadProfiles() {
  profiles=await api('/api/profiles');
  $('profile-select').innerHTML=profiles.map((p,i)=>`<option value="${i}">${esc(p.name)}</option>`).join('');
  selectProfile();
}
function selectProfile() {
  selectedProfile=profiles[Number($('profile-select').value)];
  if (!selectedProfile) return;
  $('profile-editor').value=JSON.stringify(selectedProfile,null,2);
  $('profile-summary').innerHTML=`<b>${esc(selectedProfile.name)}</b> · ${esc(selectedProfile.protocol.toUpperCase())} · ${esc(selectedProfile.fixture || 'MOCK')}<br>${selectedProfile.steps.length} langkah × ${selectedProfile.repeats || 1} pengulangan. Semua assertions wajib terpenuhi.`+table(['Langkah','TX / alamat','Assertions'],selectedProfile.steps.map((s,i)=>[i+1,esc(selectedProfile.protocol==='raw'?s.payload:`Unit ${s.unit} FC${s.function} offset ${s.address}`),esc(s.assertions.map(a=>a.kind + ': ' + (a.hex ?? a.value ?? `${a.min ?? a.target} / ${a.max ?? a.tolerance}`)).join(', '))]));
}
async function refreshPorts() {
  const ports=await api('/api/ports'), old=$('port').value;
  $('port').innerHTML='<option value="">Pilih secara eksplisit</option>'+ports.map(p=>`<option value="${esc(p.port)}">${esc(p.port)} — ${esc(p.description)}</option>`).join('');
  if (ports.some(p=>p.port===old)) $('port').value=old;
  $('adapter').innerHTML=ports.length?ports.map(p=>`${esc(p.port)} · ${esc(p.description)} · ${esc(p.hwid)} · serial ${esc(p.serial_number || 'unknown')}`).join('<br>'):'Tidak ada COM ditemukan. Mode SIMULASI tetap tersedia.';
}
async function service() {
  const info=await api('/api/service');
  $('service-state').innerHTML=`Backend: <b>${info.active?'AKTIF':'MATI'}</b><br>Autostart login: <b>${info.autostart?'TERPASANG':'BELUM TERPASANG'}</b><br>Supervisor PID: ${esc(info.supervisor?.pid || 'unknown')}<br>Data lokal: ${esc(info.data_directory)}<br>Retention: ${esc(info.retention)}`;
  if(info.lan_url) $('service-state').innerHTML += `<br><b>Akses laptop lain: <a href="${esc(info.lan_url)}">${esc(info.lan_url)}</a></b><br>COM berada pada laptop server. Client LAN berbagi koneksi dan hasil yang sama.`;
  const remote=!['127.0.0.1','localhost'].includes(location.hostname);
  ['autostart','uninstall','service-restart','service-stop'].forEach(id=>$(id).disabled=remote);
}
async function history() {
  const rows=await api('/api/history'), signature=JSON.stringify(rows);
  if (signature===historySignature) return; historySignature=signature;
  $('history-list').innerHTML=rows.length?table(['Waktu Jakarta','Profil / fixture','Status / alasan','Detail / export'],rows.map(r=>[esc(new Date(r.started).toLocaleString('id-ID',{timeZone:'Asia/Jakarta'})),`${esc(r.profile_name)}<br>${r.fixture==='MOCK'?'SIMULASI':esc(r.fixture)}`,`<b>${esc(r.status)}</b><br>${esc(r.reason)}`,`<a href="/api/export/${encodeURIComponent(r.id)}/csv">CSV Excel</a> · <a href="/api/export/${encodeURIComponent(r.id)}/json">JSON detail</a>`])):'Belum ada pengujian.';
}
function render(s) {
  state=s; $('backend').textContent='Backend AKTIF';
  if (s.connected || !initialized) {
    const c=s.connected?s.serial:s.preferences;
    if(c) for(const [id,key] of [['fixture','fixture'],['port','port'],['interface','interface'],['baud','baud'],['bits','bits'],['parity','parity'],['stopbits','stop'],['flow','flow']]) $(id).value=c[key];
    if(!initialized && s.tags.length) {tags=s.tags.map(t=>t.config);tagList();}
    initialized=true;
  }
  if(!s.owner) $('mock-fault').value=s.mock_fault;
  $('fixture-badge').textContent=!s.connected?'BELUM TERHUBUNG':s.serial.fixture==='MOCK'?'SIMULASI · BUKAN HARDWARE':s.owner==='slave'?'REAL SERIAL + SYNTHETIC VALUES':s.serial.fixture+' · '+s.serial.port;
  $('owner-badge').textContent=s.owner?'Pemilik: '+s.owner:'Port bebas';
  $('port-status').textContent=s.connected?'Terhubung':'Terputus';$('tx-count').textContent=s.tx_bytes;$('rx-count').textContent=s.rx_bytes;$('drop-count').textContent=s.dropped;
  if (s.error) $('notice').textContent=s.error;
  const locked=Boolean(s.owner), disconnected=!s.connected;
  ['connect','fixture','port','interface','baud','bits','parity','stopbits','flow'].forEach(id=>$(id).disabled=s.connected || locked);
  ['send','periodic','read-tags','poll-tags','slave-start','run'].forEach(id=>$(id).disabled=locked || disconnected);
  ['add-tag','map-set','map-delete','slave-unit','slave-import','save-profile','profile-import','mock-fault'].forEach(id=>$(id).disabled=locked);
  $('disconnect').disabled=disconnected;
  $('mock-inject').disabled=s.owner!=='slave' || s.serial.fixture!=='MOCK';
  document.querySelectorAll('[data-stop]').forEach(b=>b.disabled=!locked);
  if (!$('freeze').checked) {
    $('terminal-log').innerHTML=s.logs.slice(-100).map(l=>`<div class="log-row ${esc(l.direction)}">${esc(new Date(l.time).toLocaleTimeString('id-ID',{timeZone:'Asia/Jakarta'}))} ${esc(l.direction)}  ${esc(l.hex)}${l.text?'\n'+esc(l.text):''}${l.message?'\n'+esc(l.message):''}</div>`).join('');
    $('terminal-log').scrollTop=$('terminal-log').scrollHeight;
  }
  if (!maps) {maps=s.slave;$('slave-unit').value=maps.unit;mapTable();}
  $('tag-results').innerHTML=s.tags.length?table(['Tag','Raw registers / value','Age / status','TX / RX / latency'],s.tags.map(t=>[esc(t.config.name),`${esc(JSON.stringify(t.registers || []))}<br><b>${esc(JSON.stringify(t.value ?? '—'))}</b>`,`${t.age_seconds ?? '—'}s · ${t.stale?'STALE':'AKTUAL'}<br>${esc(t.error)}`,`${esc(t.tx)}<br>${esc(t.rx)}<br>${t.latency_ms ?? '—'} ms`])):'';
  const r=s.active;
  if (r) {
    $('result').className='card result '+r.status;
    const elapsed=r.duration_ms !== undefined?r.duration_ms/1000:(Date.now()-new Date(r.started).getTime())/1000;
    $('result').innerHTML=`<span class="eyebrow">${r.fixture==='MOCK'?'SIMULASI · BUKAN BUKTI HARDWARE':esc(r.fixture)} · ${esc(r.id)}</span><h2>${esc(r.status)}</h2><b>Profil run: ${esc(r.profile.name)}</b><progress value="${r.completed}" max="${r.target}"></progress><p>${r.completed}/${r.target} langkah · valid ${r.completed-r.errors} · error ${r.errors} · ${elapsed.toFixed(2)} detik<br>${esc(r.reason)}</p>`;
    $('step-results').innerHTML=table(['Repeat / step','TX / RX','Latency','Hasil / alasan'],r.results.slice(-30).map(e=>[`${e.repeat} / ${e.step}`,`${esc(e.tx)}<br>${esc(e.rx)}`,`${e.latency_ms ?? '—'} ms`,esc(e.error || 'Assertions valid')]));
  }
}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{
  currentTab=b.dataset.tab;document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('hidden',p.id!==currentTab));document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('selected',x===b));$('page-title').textContent=b.textContent.replace(/^\d+\s*/, '').trim();
  if(currentTab==='service') service().catch(showError);if(currentTab==='history') history().catch(showError);
});
bind('refresh',refreshPorts);
bind('connect',()=>act('connect',{fixture:$('fixture').value,port:$('port').value,interface:$('interface').value,baud:Number($('baud').value),bits:Number($('bits').value),parity:$('parity').value,stop:Number($('stopbits').value),flow:$('flow').value}));
bind('disconnect',()=>act('disconnect'));
bind('send',()=>act('terminal',raw()));bind('periodic',()=>act('periodic',raw()));
document.querySelectorAll('[data-stop]').forEach(b=>b.onclick=()=>act('stop').catch(showError));
bind('clear-log',()=>act('clear-log'));bind('clear-history',async()=>{if(confirm('Hapus semua riwayat lokal? Export dahulu bila perlu.')) {await act('clear-history');historySignature='';await history();}});
bind('add-tag',()=>{tags.push(tag());tagList();});
bind('read-tags',()=>act('master',{tags:tags.length?tags:[tag()],poll:false,interval:Number($('poll-interval').value)}));
bind('poll-tags',()=>act('master',{tags:tags.length?tags:[tag()],poll:true,interval:Number($('poll-interval').value)}));
$('map-function').onchange=mapTable;
async function saveMap(remove=false) {const next=structuredClone(maps);next.unit=Number($('slave-unit').value);if(remove) delete next.maps[$('map-function').value][$('map-address').value];else next.maps[$('map-function').value][$('map-address').value]=Number($('map-value').value);await act('slave-config',next);maps=next;mapTable();}
bind('map-set',()=>saveMap());bind('map-delete',()=>saveMap(true));
bind('slave-start',async()=>{maps.unit=Number($('slave-unit').value);await act('slave-config',maps);await act('slave-start');});
bind('slave-export',()=>download('slave-preset.json',maps));
bind('mock-inject',()=>act('mock-inject',{hex:$('mock-frame').value}));
$('slave-import').onchange=async event=>{try {const next=JSON.parse(await event.target.files[0].text());await act('slave-config',next);maps=next;$('slave-unit').value=maps.unit;mapTable();} catch(e){showError(e);} event.target.value='';};
$('profile-select').onchange=selectProfile;
bind('profile-export',()=>download('serial-profile.json',selectedProfile));
bind('save-profile',async()=>{const profile=JSON.parse($('profile-editor').value);await act('profile',profile);await loadProfiles();const i=profiles.findIndex(p=>p.name===profile.name);$('profile-select').value=i;selectProfile();});
$('profile-import').onchange=async event=>{try {const profile=JSON.parse(await event.target.files[0].text());await act('profile',profile);await loadProfiles();$('profile-select').value=profiles.findIndex(p=>p.name===profile.name);selectProfile();}catch(e){showError(e);}event.target.value='';};
$('mock-fault').onchange=()=>act('mock-fault',{fault:$('mock-fault').value}).catch(showError);
bind('run',async()=>{if(busy)return;busy=true;$('run').disabled=true;try{await act('run',{profile:selectedProfile,identity:$('identity').value || 'unknown'});}catch(e){throw new Error('ERROR SETUP: '+e.message);}finally{busy=false;}});
bind('service-refresh',service);bind('autostart',async()=>{await act('install-autostart');await service();});bind('uninstall',async()=>{await act('uninstall-autostart');await service();});
bind('service-restart',()=>act('service-restart'));bind('service-stop',()=>act('service-stop'));
async function tick() {try{render(await api('/api/state'));if(currentTab==='history') await history();}catch(e){$('backend').textContent='Backend tidak tersedia';showError(e);}setTimeout(tick,500);}
(async()=>{try{token=(await api('/api/session')).token;await refreshPorts();await loadProfiles();await history();await tick();}catch(e){showError(e);}})();
