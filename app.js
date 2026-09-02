let policies=[];
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function card(p){
 const cls=p.review_required?'policy review':'policy';
 const statusCls=p.status==='변경됨'?'tag changed':'tag status';
 const checked=(p.checked_at||'').slice(0,10);
 return `<article class="${cls}">
  <div class="tags"><span class="tag">${esc(p.region)}</span><span class="tag">${esc(p.category)}</span><span class="${statusCls}">${esc(p.review_required?'검토 필요':p.status)}</span></div>
  <h3>${esc(p.title)}</h3>
  <p>${esc(p.summary)}</p>
  <div class="meta">
   <b>대상</b><span>${esc(p.eligibility||'확인 필요')}</span>
   <b>혜택</b><span>${esc(p.benefit||'확인 필요')}</span>
   <b>기간</b><span>${esc(p.period||'공식 공고 확인')}</span>
   <b>신청</b><span>${esc(p.apply_method||'공식 신청처 확인')}</span>
   <b>출처</b><span>${esc(p.source_name)}</span>
   ${checked?`<b>확인일</b><span>${esc(checked)}</span>`:''}
  </div>
  <div class="actions"><a href="${esc(p.url)}" target="_blank" rel="noopener">공식 신청·출처</a>${p.review_required?'<span class="secondary">자동 추출 검토 필요</span>':''}</div>
 </article>`;
}
function render(){
 const q=$('#q').value.trim().toLowerCase(),r=$('#region').value,c=$('#category').value,s=$('#status').value;
 const rows=policies.filter(p=>(r==='all'||p.region===r)&&(c==='all'||p.category===c)&&(s==='all'||p.status===s)&&(!q||JSON.stringify(p).toLowerCase().includes(q)));
 $('#policyList').innerHTML=rows.map(card).join('');
 $('#empty').hidden=rows.length>0;
}
async function init(){
 const data=await fetch('data/policies.json?'+Date.now()).then(r=>r.json());
 policies=data.policies||[];
 $('#count').textContent=policies.length;
 $('#updated').textContent=(data.updated_at||'-').slice(0,10);
 const regionCounts={}; for(const p of policies) regionCounts[p.region]=(regionCounts[p.region]||0)+1;
 const rc=$('#regionCounts'); if(rc) rc.textContent=['중앙정부','서울','경기','전남광주통합특별시'].map(x=>`${x} ${regionCounts[x]||0}`).join(' · ');
 ['region','category','status','q'].forEach(id=>$('#'+id).addEventListener('input',render));
 $('#reset').onclick=()=>{ $('#region').value=$('#category').value=$('#status').value='all'; $('#q').value=''; render(); };
 document.querySelector('#dataset-jsonld').textContent=JSON.stringify({"@context":"https://schema.org","@type":"Dataset","name":"혜택레이더 정책 데이터","dateModified":data.updated_at,"distribution":{"@type":"DataDownload","contentUrl":"data/policies.json","encodingFormat":"application/json"}});
 render();
}
init().catch(()=>{$('#empty').hidden=false;$('#empty').textContent='정책 데이터를 불러오지 못했습니다.'});
