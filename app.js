let policies=[];
let budget2027=[];
let visibleCount=24;
let activeAudience='';
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const REGIONS=['중앙정부','서울','부산','대구','인천','대전','울산','세종','경기','강원','충북','충남','전북','전남광주통합특별시','경북','경남','제주'];
const REGION_LABEL={중앙정부:'중앙정부',서울:'서울특별시',부산:'부산광역시',대구:'대구광역시',인천:'인천광역시',대전:'대전광역시',울산:'울산광역시',세종:'세종특별자치시',경기:'경기도',강원:'강원특별자치도',충북:'충청북도',충남:'충청남도',전북:'전북특별자치도',전남광주통합특별시:'전남광주통합특별시',경북:'경상북도',경남:'경상남도',제주:'제주특별자치도'};
function safeUrl(url){try{const u=new URL(url,location.href);return ['http:','https:'].includes(u.protocol)?u.href:'#'}catch{return '#'}}
function statusClass(s){return s==='신청가능'?'open':s==='마감임박'?'urgent':s==='예정'?'upcoming':s==='마감'?'closed':'review'}
function searchable(p){return [p.title,p.summary,p.region,p.category,p.status,p.eligibility,p.benefit,p.period,p.apply_method,p.source_name].join(' ').toLowerCase()}
function completeness(p){return ['eligibility','benefit','period','apply_method'].reduce((n,k)=>n+(!String(p[k]||'').includes('확인')?1:0),0)}
function recommendation(p){const sw={마감임박:80,신청가능:70,예정:45,확인필요:20,마감:0}[p.status]||10;const money=/원|만원|억원|%|바우처|수당|장려금|감면|대출|융자|월세|교통비/.test(p.benefit||'')?18:0;return sw+Math.min(Number(p.value_score||0),30)+completeness(p)*4+money}
function ga(name,params={}){if(typeof window.gtag==='function')window.gtag('event',name,params)}

function budgetCard(b){
 const url=safeUrl(b.source_url); const detail=`budget/2027/${encodeURIComponent(b.id)}.html`;
 return `<article class="budget-card">
   <div class="budget-card-top"><span class="budget-badge">${esc(b.status)}</span><span class="budget-category">${esc(b.category)}</span></div>
   <h3>${esc(b.title)}</h3>
   <p class="budget-definition">${esc(b.definition)}</p>
   <dl class="budget-facts"><dt>내가 받는 혜택</dt><dd>${esc(b.benefit)}</dd><dt>개인 지급액</dt><dd>${esc(b.personal_amount)}</dd><dt>지급 방식</dt><dd>${esc(b.delivery)}</dd></dl>
   <div class="budget-bottom"><strong>${esc(b.budget)}</strong><span><a href="${detail}">쉽게 설명 보기</a> · <a href="${esc(url)}" target="_blank" rel="noopener">공식 근거</a></span></div>
  </article>`;
}
function renderBudgetPreview(){
 const box=$('#budgetPreviewList');if(!box)return;
 const featured=['budget27-all-ai','budget27-youth-future-savings','budget27-k-livelihood-loan','budget27-basic-livelihood'];
 const rows=featured.map(id=>budget2027.find(x=>x.id===id)).filter(Boolean);
 box.innerHTML=rows.length?rows.map(budgetCard).join(''):'<div class="budget-loading">2027 예산안 정보를 준비 중입니다.</div>';
}

function card(p){
 const checked=(p.checked_at||p.source_updated_at||'').slice(0,10);
 const url=safeUrl(p.url); const detail=`policy/${encodeURIComponent(p.id)}.html`;
 return `<article class="policy" data-id="${esc(p.id)}">
   <div class="policy-main">
    <div class="tags"><span class="tag region">${esc(REGION_LABEL[p.region]||p.region||'지역')}</span><span class="tag">${esc(p.category||'복지')}</span><span class="tag status ${statusClass(p.status)}">${esc(p.review_required?'확인 필요':p.status||'확인필요')}</span></div>
    <h3>${esc(p.title)}</h3>
    <p class="policy-summary">${esc(p.summary||'공식 공고의 주요 내용을 확인하세요.')}</p>
    <dl class="policy-facts"><dt>지원대상</dt><dd>${esc(p.eligibility||'공식 공고에서 자격 확인')}</dd><dt>지원내용</dt><dd>${esc(p.benefit||'공식 공고에서 지원내용 확인')}</dd><dt>신청기간</dt><dd>${esc(p.period||'공식 공고 확인')}</dd></dl>
   </div>
   <div class="policy-action"><span class="policy-links"><a class="detail-link" href="${detail}" data-title="${esc(p.title)}">대상·혜택 자세히</a><a class="official-link" href="${esc(url)}" target="_blank" rel="noopener" data-title="${esc(p.title)}" data-region="${esc(p.region)}">공식 신청·출처</a></span><span class="checked">${p.review_required?'<span class="review-note">자동 추출 확인 필요</span><br>':''}${checked?'확인 '+esc(checked):esc(p.source_name||'공식출처')}</span></div>
  </article>`;
}
function currentRows(){
 const q=$('#q').value.trim().toLowerCase(),r=$('#region').value,c=$('#category').value,s=$('#status').value,hide=$('#hideClosed').checked;
 let rows=policies.filter(p=>(r==='all'||p.region===r)&&(c==='all'||p.category===c)&&(s==='all'||p.status===s)&&(!hide||p.status!=='마감')&&(!q||searchable(p).includes(q))&&(!activeAudience||searchable(p).includes(activeAudience.toLowerCase())));
 const sort=$('#sort').value;
 if(sort==='title')rows.sort((a,b)=>String(a.title).localeCompare(String(b.title),'ko'));
 else if(sort==='value')rows.sort((a,b)=>(Number(b.value_score||0)-Number(a.value_score||0))||(recommendation(b)-recommendation(a)));
 else if(sort==='deadline')rows.sort((a,b)=>({마감임박:4,신청가능:3,예정:2,확인필요:1,마감:0}[b.status]||0)-({마감임박:4,신청가능:3,예정:2,확인필요:1,마감:0}[a.status]||0));
 else rows.sort((a,b)=>recommendation(b)-recommendation(a));
 return rows;
}
function renderFilters(){
 const labels=[];if($('#region').value!=='all')labels.push(REGION_LABEL[$('#region').value]||$('#region').value);if($('#category').value!=='all')labels.push($('#category').value);if($('#status').value!=='all')labels.push($('#status').value);if(activeAudience)labels.push(activeAudience);if($('#q').value.trim())labels.push('검색: '+$('#q').value.trim());
 const box=$('#activeFilters');box.hidden=!labels.length;box.innerHTML=labels.map(x=>`<span>${esc(x)}</span>`).join('');
}
function render(){
 const rows=currentRows();
 const shown=rows.slice(0,visibleCount);
 $('#policyList').innerHTML=shown.map(card).join('');
 $('#empty').hidden=rows.length>0;
 $('#loadMore').hidden=rows.length<=visibleCount;
 $('#resultSummary').textContent=`조건에 맞는 혜택 ${rows.length.toLocaleString()}건${rows.length>shown.length?` 중 ${shown.length}건 표시`:''}`;
 renderFilters();
 $$('.official-link').forEach(a=>a.addEventListener('click',()=>ga('official_link_click',{policy_title:a.dataset.title,policy_region:a.dataset.region})));
 $$('.detail-link').forEach(a=>a.addEventListener('click',()=>ga('policy_detail_click',{policy_title:a.dataset.title})));
}
function updateStats(data){
 const active=policies.filter(p=>p.status!=='마감');
 $('#count').textContent=policies.length.toLocaleString();
 $('#openCount').textContent=policies.filter(p=>p.status==='신청가능').length.toLocaleString();
 $('#urgentCount').textContent=policies.filter(p=>p.status==='마감임박').length.toLocaleString();
 $('#regionCount').textContent=new Set(policies.map(p=>p.region).filter(Boolean)).size.toLocaleString();
 const d=(data.updated_at||'-').slice(0,10);$('#updated').textContent=d;$('#topUpdated').textContent=`최종 갱신 ${d}`;
}
function setupRegions(){
 const counts={};for(const p of policies)counts[p.region]=(counts[p.region]||0)+1;
 const select=$('#region');select.innerHTML='<option value="all">전국 전체</option>'+REGIONS.map(r=>`<option value="${esc(r)}">${esc(REGION_LABEL[r]||r)} (${counts[r]||0})</option>`).join('');
 $('#regionGrid').innerHTML=REGIONS.map(r=>`<button class="region-button" type="button" data-region="${esc(r)}"><span>${esc(REGION_LABEL[r]||r)}</span><small>${(counts[r]||0).toLocaleString()}건</small></button>`).join('');
 $$('.region-button').forEach(b=>b.addEventListener('click',()=>{$('#region').value=b.dataset.region;visibleCount=24;render();document.querySelector('.portal-layout').scrollIntoView({behavior:'smooth',block:'start'});ga('region_filter',{region:b.dataset.region})}));
}
function setupUrgent(){
 const urgent=policies.filter(p=>p.status==='마감임박').sort((a,b)=>recommendation(b)-recommendation(a)).slice(0,6);
 $('#urgentList').innerHTML=urgent.length?urgent.map(p=>`<article class="urgent-card"><small>마감 임박</small><h3>${esc(p.title)}</h3><span>${esc(REGION_LABEL[p.region]||p.region)} · ${esc(p.period||'기간 확인')}</span><button type="button" data-id="${esc(p.id)}">이 혜택 보기 →</button></article>`).join(''):'<div class="urgent-card"><h3>현재 표시할 마감 임박 정책이 없습니다.</h3><span>다음 자동 갱신에서 다시 확인합니다.</span></div>';
 $$('#urgentList button[data-id]').forEach(b=>b.addEventListener('click',()=>{const p=policies.find(x=>x.id===b.dataset.id);if(!p)return;$('#q').value=p.title;visibleCount=24;render();document.querySelector('.portal-layout').scrollIntoView({behavior:'smooth'});}));
}
function resetAll(){activeAudience='';$$('#audienceChips button').forEach(b=>b.classList.remove('active'));$('#region').value=$('#category').value=$('#status').value='all';$('#sort').value='recommended';$('#hideClosed').checked=true;$('#q').value='';visibleCount=24;render()}
async function init(){
 const [data,budgetData]=await Promise.all([
  fetch('data/policies.json?'+Date.now()).then(r=>{if(!r.ok)throw new Error('data');return r.json()}),
  fetch('data/budget2027.json?'+Date.now()).then(r=>r.ok?r.json():({items:[]})).catch(()=>({items:[]}))
 ]);
 policies=data.policies||[];
 budget2027=budgetData.items||[];
 updateStats(data);setupRegions();setupUrgent();renderBudgetPreview();
 const params=new URLSearchParams(location.search); if(params.get('q')) $('#q').value=params.get('q'); if(params.get('region')&&REGIONS.includes(params.get('region'))) $('#region').value=params.get('region');
 ['region','category','status','sort','hideClosed'].forEach(id=>$('#'+id).addEventListener('change',()=>{visibleCount=24;render()}));
 $('#q').addEventListener('input',()=>{visibleCount=24;render()});
 $('#searchButton').addEventListener('click',()=>{visibleCount=24;render();const u=new URL(location.href);const q=$('#q').value.trim();q?u.searchParams.set('q',q):u.searchParams.delete('q');history.replaceState(null,'',u);document.querySelector('.portal-layout').scrollIntoView({behavior:'smooth'});ga('site_search',{search_term:q})});
 $('#q').addEventListener('keydown',e=>{if(e.key==='Enter')$('#searchButton').click()});
 $$('.popular-keywords button').forEach(b=>b.addEventListener('click',()=>{$('#q').value=b.dataset.query;$('#searchButton').click()}));
 $$('#audienceChips button').forEach(b=>b.addEventListener('click',()=>{const same=activeAudience===b.dataset.audience;activeAudience=same?'':b.dataset.audience;$$('#audienceChips button').forEach(x=>x.classList.toggle('active',x===b&&!same));visibleCount=24;render();ga('audience_filter',{audience:activeAudience||'off'})}));
 $('#reset').onclick=resetAll;
 $('#loadMore').onclick=()=>{visibleCount+=24;render()};
 $('#mobileFilter').onclick=()=>$('.filter-panel').classList.toggle('open');
 $('#showUrgent').onclick=()=>{$('#status').value='마감임박';$('#hideClosed').checked=true;visibleCount=24;render();document.querySelector('.portal-layout').scrollIntoView({behavior:'smooth'})};
 document.querySelector('#dataset-jsonld').textContent=JSON.stringify({"@context":"https://schema.org","@type":"Dataset","name":"혜택레이더 전국 지원정책 데이터","description":"중앙정부와 전국 시·도의 공식 지원정책을 구조화한 데이터","dateModified":data.updated_at,"url":"https://kimjunnem.github.io/","distribution":{"@type":"DataDownload","contentUrl":"https://kimjunnem.github.io/data/policies.json","encodingFormat":"application/json"}});
 render();
}
init().catch(()=>{$('#resultSummary').textContent='정책 데이터를 불러오지 못했습니다.';$('#empty').hidden=false;$('#empty').innerHTML='<b>정책 데이터를 불러오지 못했습니다.</b><span>잠시 후 다시 시도해 주세요.</span>'});
