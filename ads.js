(function(){
  const cfg=window.BENEFIT_RADAR_CONFIG||{};
  const slots=document.querySelectorAll('[data-ad-slot]');
  if(!cfg.adsenseClient){
    slots.forEach(el=>{ el.innerHTML='<div class="ad-ready">광고 준비 영역</div>'; });
    return;
  }
  const s=document.createElement('script');
  s.async=true;
  s.crossOrigin='anonymous';
  s.src='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='+encodeURIComponent(cfg.adsenseClient);
  document.head.appendChild(s);
  s.onload=()=>slots.forEach(el=>{
    el.innerHTML='<ins class="adsbygoogle" style="display:block" data-ad-client="'+cfg.adsenseClient+'" data-ad-slot="" data-ad-format="auto" data-full-width-responsive="true"></ins>';
    try{(adsbygoogle=window.adsbygoogle||[]).push({});}catch(e){}
  });
})();
