#!/usr/bin/env python3
import concurrent.futures
import hashlib, html, json, os, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta, date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urljoin

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'policies.json'
KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).date()

RSS_SOURCES = [
    ('서울', '복지', '서울 열린데이터광장', 'https://data.seoul.go.kr/rss/rssView.do?searchType=1006'),
    ('서울', '주거', '서울 열린데이터광장', 'https://data.seoul.go.kr/rss/rssView.do?searchType=10326'),
    ('서울', '일자리', '서울 열린데이터광장', 'https://data.seoul.go.kr/rss/rssView.do?searchType=1005'),
    ('서울', '교육', '서울 열린데이터광장', 'https://data.seoul.go.kr/rss/rssView.do?searchType=1004'),
    ('서울', '복지', '내 손안에 서울', 'https://mediahub.seoul.go.kr/news/rss/07'),
    ('서울', '주거', '내 손안에 서울', 'https://mediahub.seoul.go.kr/news/rss/03'),
    ('서울', '일자리', '내 손안에 서울', 'https://mediahub.seoul.go.kr/news/rss/04'),
]

# 공식 목록 페이지에서 상세 링크를 찾아 따라가는 수집원.
LIST_SOURCES = [
    {
        'region':'경기','category':'복지','source':'경기민원24',
        'url':'https://gg24.gg.go.kr/svcreqst/selectPageListSvcReqst.do',
        'allow':r'/svcreqst/selectSvcReqst\.do\?svc_seq=\d+'
    },
    {
        'region':'전남광주통합특별시','category':'복지','source':'광주청년통합플랫폼',
        'url':'https://youth.gwangju.go.kr/www/dream/policyList',
        'allow':r'(?:policy|Policy|dream|youth).*(?:view|View|detail|Detail)|/www/dream/'
    },
    {
        'region':'전남광주통합특별시','category':'일자리','source':'전남·광주 통합 일자리정보망',
        'url':'https://job.jeonnam.go.kr/www/59',
        'allow':r'(?:bizmap|detailView|workprojectId=\d+)'
    },
]

POSITIVE = ['지원금','지원','청년','주거','월세','전세','주택','일자리','취업','근로','채용','생활비','바우처','급여','저소득','금융','대출','장려금','수당','감면','할인','보조','융자','교육비','교통비','에너지','공공임대','신청','모집','자격증','출산','돌봄','창업']
HIGH_VALUE = ['지원금','월세','전세','급여','수당','장려금','바우처','감면','대출','융자','공공임대','채용','교육비','교통비','지원사업','이주비','보증료','임대료']
LOW_VALUE = ['조사 자료','연구 자료','통계','위원회','회의록','성과보고','실태조사','설문조사','참여자 조사','보도자료','토론회','간담회','기념식','선정 결과','협약식']
SOURCE_RANK = {'정부24 공공서비스 Open API':6,'경기민원24':6,'광주청년통합플랫폼':6,'전남·광주 통합 일자리정보망':6,'온통청년 오픈 API':5,'서울 열린데이터광장':4,'내 손안에 서울':3}

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.links=[]; self.skip=0; self._href=None; self._anchor=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag in ('script','style','noscript','svg'): self.skip += 1
        if tag == 'a' and not self.skip:
            self._href=attrs.get('href'); self._anchor=[]
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript','svg') and self.skip: self.skip -= 1
        if tag == 'a' and self._href is not None:
            txt=clean(' '.join(self._anchor)); self.links.append((self._href,txt)); self._href=None; self._anchor=[]
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self._href is not None: self._anchor.append(data)

def get(url, timeout=25):
    req=urllib.request.Request(url,headers={
        'User-Agent':'BenefitRadar/0.5 (+https://kimjunnem.github.io/)',
        'Accept':'application/xml,text/xml,text/html,application/json,*/*'
    })
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def clean(s):
    return re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',html.unescape(s or ''))).strip()

def parse_page(raw):
    p=PageParser(); p.feed(raw.decode('utf-8','ignore')); return clean(' '.join(p.parts)), p.links

def stable_id(prefix,text): return prefix+'-'+hashlib.sha256(text.encode('utf-8','ignore')).hexdigest()[:18]

def value_score(text):
    score=sum(1 for k in POSITIVE if k in text)+sum(2 for k in HIGH_VALUE if k in text)
    score-=sum(3 for k in LOW_VALUE if k in text)
    return score

def category_from(text,fallback='복지'):
    t=text.lower()
    if any(x in t for x in ['월세','전세','주택','주거','임대','보증금','이주비','주택도시']): return '주거'
    if any(x in t for x in ['취업','일자리','근로','채용','창업','구직','자격증','직무']): return '일자리'
    if any(x in t for x in ['대출','융자','금융','이자','신용','자산','채무','보증료']): return '금융'
    if any(x in t for x in ['생활비','바우처','요금','교통비','에너지','급여','수당','과일','돌봄']): return '생활비'
    if any(x in t for x in ['교육','훈련','학비','교복']): return '교육'
    return fallback

def region_from(text,fallback='중앙정부'):
    if any(x in text for x in ['전남광주통합특별시','전라남도','전남도','광주광역시','광주시','광산구','북구','남구','서구']): return '전남광주통합특별시'
    if any(x in text for x in ['경기도','경기 도민','경기도민']): return '경기'
    if any(x in text for x in ['서울특별시','서울시','서울 청년']): return '서울'
    return fallback

def normalize_title(title):
    t=clean(title)
    t=re.sub(r'^[\[【(][^\]】)]{1,24}[\]】)]\s*','',t)
    t=re.sub(r'^["\'‘’“”]?\d+[년월일간 최대~부터까지\s,\.억만원천백]+["\'‘’“”]?\s*[-·:]?\s*','',t)
    t=re.sub(r'^(서울시|서울특별시|경기도|전남도|전라남도|광주광역시|정부)[,\s]+','',t)
    t=re.sub(r'\s*(신청 방법은\?|신청하세요|모집 시작|모집한다|지원한다|확대한다|본격 추진|어떻게\?|받으세요!).*?$','',t)
    t=re.sub(r'^[!?.·\-\s]+|[!?.·\-\s]+$','',t)
    return t[:92] or clean(title)[:92]

def label_extract(text, labels, stop_labels, max_len=220):
    label_group='|'.join(map(re.escape,labels)); stop_group='|'.join(map(re.escape,stop_labels))
    m=re.search(r'(?:'+label_group+r')\s*[:：]?\s*(.{5,'+str(max_len)+r'}?)(?=(?:'+stop_group+r')\s*[:：]?|$)',text,re.S)
    return clean(m.group(1))[:max_len] if m else ''

def extract_benefit(text):
    labeled=label_extract(text,['지원 내용','지원내용','혜택','지원금액','지원 금액'],['신청대상자','지원대상','신청 대상','신청기간','신청 기간','신청방법','신청 방법','문의','담당자'],320)
    if labeled:
        # 금액만 떼지 않고 문맥을 보존한다.
        return labeled[:220]
    sentences=re.split(r'(?<=[.!?。])\s+|\s*[○ㅇ▪✔]\s*',text)
    candidates=[clean(s) for s in sentences if any(k in s for k in ['지원','지급','감면','할인','대출','융자','제공']) and re.search(r'\d|만원|억원|원|%',s)]
    return candidates[0][:220] if candidates else '공식 공고에서 지원내용 확인'

def extract_eligibility(text):
    labeled=label_extract(text,['신청대상자','지원대상','신청 대상','지원 대상','사업대상','사업 대상'],['지원 내용','지원내용','신청기간','신청 기간','신청방법','신청 방법','문의','담당자'],320)
    if labeled: return labeled[:220]
    for pat in [r'(?:지원|신청|모집)\s*대상\s*[:：]?\s*([^.!?]{8,220})',r'(?:대상은|대상으로)\s*([^.!?]{8,220})']:
        m=re.search(pat,text)
        if m:return clean(m.group(1))[:220]
    return '공식 공고에서 자격 확인'

def extract_apply_method(text):
    labeled=label_extract(text,['신청은 어디서 하나요','신청방법','신청 방법','접수방법','접수 방법'],['신청기간','신청 기간','지원 내용','지원내용','문의','담당자','FAQ'],240)
    if labeled:return labeled[:180]
    for pat in [r'(?:온라인|방문|우편|이메일)\s*(?:신청|접수)[^.!?]{0,120}',r'(?:신청|접수)\s*(?:처|방법)\s*[:：]?\s*([^.!?]{6,150})']:
        m=re.search(pat,text)
        if m:return clean(m.group(0))[:180]
    return '공식 신청처 확인'

def find_dates(text):
    out=[]
    for y,m,d in re.findall(r'(20\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})\s*일?',text):
        try:out.append(date(int(y),int(m),int(d)))
        except:pass
    return out

def extract_period(text):
    labeled=label_extract(text,['신청기간','신청 기간','접수기간','접수 기간','모집기간','모집 기간'],['신청방법','신청 방법','지원 내용','지원내용','문의','담당자','FAQ'],220)
    if labeled:return labeled[:160]
    pats=[
        r'20\d{2}[.\-/년]\s*\d{1,2}[.\-/월]\s*\d{1,2}일?\s*(?:\([^)]*\))?\s*[~～\-]\s*(?:20\d{2}[.\-/년]\s*)?\d{1,2}[.\-/월]\s*\d{1,2}일?',
        r'\d{1,2}월\s*\d{1,2}일\s*(?:부터|~|～|-)\s*\d{1,2}월\s*\d{1,2}일(?:까지)?',
        r'(?:상시|모집마감시|예산 소진시|사업 소진시)[^.!?]{0,50}'
    ]
    for pat in pats:
        m=re.search(pat,text,re.I)
        if m:return clean(m.group(0))[:160]
    return '공식 공고 확인'

def infer_status(text, period=''):
    blob=(text+' '+period)[:12000]
    if any(x in blob for x in ['접수중','접수 중','신청중','신청 중','모집중','상시 접수']): return '신청가능'
    if any(x in blob for x in ['접수예정','접수 예정','신청 예정','모집 예정']): return '예정'
    if any(x in blob for x in ['접수마감','접수 마감','신청 마감','모집 마감','마감되었습니다']): return '마감'
    ds=find_dates(period)
    if len(ds)>=2:
        start,end=ds[0],ds[-1]
        if TODAY < start:return '예정'
        if TODAY > end:return '마감'
        if 0 <= (end-TODAY).days <= 7:return '마감임박'
        return '신청가능'
    if any(x in blob for x in ['모집마감시','예산 소진시','사업 소진시','상시']): return '신청가능'
    return '확인필요'

def make_policy(title,url,source,region,category,text,seed_summary=''):
    benefit=extract_benefit(text); eligibility=extract_eligibility(text); period=extract_period(text); apply_method=extract_apply_method(text)
    status=infer_status(text,period)
    extracted=sum('확인' not in str(v) for v in (benefit,eligibility,period,apply_method))
    summary=seed_summary or (('혜택: '+benefit) if '확인' not in benefit else clean(text)[:260])
    return {
        'id':stable_id('auto',url or title), 'title':normalize_title(title), 'region':region_from(text,region),
        'category':category_from(text,category), 'status':status, 'summary':summary[:260],
        'eligibility':eligibility, 'benefit':benefit, 'period':period, 'apply_method':apply_method,
        'source_name':source, 'url':url, 'review_required':extracted < 3 or status=='확인필요',
        'value_score':value_score(text), 'checked_at':datetime.now(KST).isoformat(timespec='seconds')
    }

def rss_candidates(region,fallback,source_name,url):
    out=[]
    try:root=ET.fromstring(get(url))
    except Exception as e:print('RSS failed',url,e);return out
    for item in root.findall('.//item')[:100]:
        title=clean(item.findtext('title')); link=clean(item.findtext('link')); desc=clean(item.findtext('description'))
        blob=f'{title} {desc}'; score=value_score(blob)
        if not title or score < 2:continue
        out.append({'title':title,'url':link or url,'source':source_name,'region':region,'category':fallback,'seed':desc,'score':score})
    return out

def list_candidates(cfg):
    out=[]
    try:raw=get(cfg['url']); text,links=parse_page(raw)
    except Exception as e:print('LIST failed',cfg['url'],e);return out
    seen=set()
    for href,anchor in links:
        if not href or not re.search(cfg['allow'],href,re.I):continue
        u=urljoin(cfg['url'],href)
        if u in seen:continue
        seen.add(u)
        # 제목이 비어도 상세 페이지에서 다시 찾는다.
        if anchor and value_score(anchor) < 1 and not any(k in anchor for k in ['지원','사업','청년','가정','전세','교복','수당','금융']):continue
        out.append({'title':anchor or '정책 상세','url':u,'source':cfg['source'],'region':cfg['region'],'category':cfg['category'],'seed':'','score':value_score(anchor)})
    # 광주 정책 목록은 상세 링크가 JS라 누락될 수 있어 목록 페이지 자체도 후보로 넣는다.
    if cfg['source']=='광주청년통합플랫폼':
        out += split_gwangju_list(cfg['url'],text,cfg)
    return out[:120]

def split_gwangju_list(url,text,cfg):
    out=[]
    # '접수중 ... 정책명 ... 신청기간 ... 지원내용' 블록을 목록 페이지에서 직접 구조화.
    blocks=re.split(r'(?=접수중\s)',text)
    for b in blocks[1:]:
        b=clean(b)[:1800]
        if value_score(b)<2:continue
        # 상태 다음 지역명 뒤 첫 문장을 정책명으로 추정
        m=re.match(r'접수중\s+(?:광주광역시|전남광주통합특별시|[^\s]{1,12}구)?\s*(.{5,100}?)(?=\s+20\d{2}-\d{2}-\d{2}|\s+관심정책|\s+연령\s*:)',b)
        title=clean(m.group(1)) if m else clean(b[:90])
        out.append({'title':title,'url':url,'source':cfg['source'],'region':cfg['region'],'category':category_from(b,cfg['category']),'seed':b[:260],'score':value_score(b),'inline_text':b})
    return out[:50]

def enrich_candidate(c):
    if c.get('inline_text'):
        text=c['inline_text']
    else:
        try:
            raw=get(c['url'],timeout=16); text,links=parse_page(raw)
        except Exception as e:
            print('enrich failed',c.get('url'),e); text=(c.get('title','')+' '+c.get('seed',''))
    title=c.get('title') or ''
    # 상세페이지 h1/h2를 못 읽은 경우, 본문에서 '접수중' 뒤 정책명 추정
    if title in ('정책 상세','상세보기',''):
        m=re.search(r'(?:접수중|접수 중|모집중)?\s*([가-힣0-9「」\[\]()·\-\s]{8,100}(?:지원사업|지원|수당|사업|모집))',text)
        if m:title=clean(m.group(1))
    return make_policy(title,c['url'],c['source'],c['region'],c['category'],text,c.get('seed',''))

def youth_api_candidates():
    key=os.getenv('YOUTH_API_KEY','').strip()
    if not key:return []
    qs=urlencode({'openApiVlak':key,'pageIndex':1,'display':100,'query':''})
    url='https://www.youthcenter.go.kr/opi/youthPlcyList.do?'+qs
    try:obj=json.loads(get(url).decode('utf-8','ignore'))
    except Exception as e:print('Youth API failed',e);return []
    rows=obj.get('youthPolicyList') or obj.get('result') or obj.get('data') or []
    if isinstance(rows,dict):rows=rows.get('list') or rows.get('items') or []
    out=[]
    for x in rows if isinstance(rows,list) else []:
        title=x.get('polyBizSjnm') or x.get('plcyNm') or x.get('title')
        if not title:continue
        raw=json.dumps(x,ensure_ascii=False)
        if value_score(raw)<1:continue
        p=make_policy(title,x.get('rqutUrla') or x.get('url') or 'https://www.youthcenter.go.kr/','온통청년 오픈 API','중앙정부','복지',raw,clean(x.get('polyItcnCn') or x.get('plcyExplnCn') or ''))
        out.append(p)
    return out

def _gov24_get(path, key, params=None, timeout=35):
    params = dict(params or {})
    params.setdefault('returnType', 'JSON')
    params['serviceKey'] = key
    url = 'https://api.odcloud.kr/api/gov24/v3/' + path + '?' + urlencode(params, doseq=True, safe='[]:%')
    try:
        return json.loads(get(url, timeout).decode('utf-8', 'ignore'))
    except Exception as e:
        print('Gov24 API failed', path, e)
        return {}

def _truthy_code(v):
    return str(v or '').strip().upper() in ('Y','YES','TRUE','1','O','○','대상')

def _gov24_condition_text(row):
    if not isinstance(row, dict):
        return ''
    parts=[]
    age_start=row.get('JA0110')
    age_end=row.get('JA0111')
    if age_start not in (None,'') or age_end not in (None,''):
        if age_start not in (None,'') and age_end not in (None,''):
            parts.append(f"연령 {age_start}~{age_end}세")
        elif age_start not in (None,''):
            parts.append(f"연령 {age_start}세 이상")
        else:
            parts.append(f"연령 {age_end}세 이하")

    code_labels = {
        'JA0201':'중위소득 50% 이하','JA0202':'중위소득 51~75%',
        'JA0203':'중위소득 76~100%','JA0204':'중위소득 101~200%',
        'JA0205':'중위소득 200% 초과','JA0301':'예비부모·난임',
        'JA0302':'임산부','JA0303':'출산·입양','JA0320':'대학생·대학원생',
        'JA0326':'근로자·직장인','JA0327':'구직자·실업자',
        'JA0328':'장애인','JA0329':'국가보훈대상자','JA0330':'질병·질환자',
        'JA0401':'다문화가족','JA0402':'북한이탈주민',
        'JA0403':'한부모·조손가정','JA0404':'1인가구',
        'JA0411':'다자녀가구','JA0412':'무주택세대','JA0413':'신규전입',
        'JA1101':'예비창업자','JA1102':'영업중 사업자',
        'JA1103':'생계곤란·폐업예정자','JA2101':'중소기업',
        'JA2102':'사회복지시설','JA2103':'기관·단체'
    }
    for code,label in code_labels.items():
        if _truthy_code(row.get(code)):
            parts.append(label)
    return ' · '.join(parts[:8])

def _gov24_region(row):
    raw=json.dumps(row, ensure_ascii=False)
    org_type=str(row.get('소관기관유형') or '')
    org=str(row.get('소관기관명') or '')
    if any(x in raw for x in ['서울특별시','서울시']):
        return '서울'
    if any(x in raw for x in ['경기도','경기 도민','경기도민']):
        return '경기'
    if any(x in raw for x in ['전라남도','전남도','광주광역시','전남광주통합특별시']):
        return '전남광주통합특별시'
    if any(x in org_type for x in ['중앙','국가']) or any(x in org for x in [
        '고용노동부','보건복지부','국토교통부','중소벤처기업부','여성가족부',
        '교육부','농림축산식품부','해양수산부','문화체육관광부','산업통상자원부',
        '행정안전부','기획재정부','환경부','국가보훈부','금융위원회'
    ]):
        return '중앙정부'
    # 다른 시·도의 지방서비스는 현재 혜택레이더 범위에서 제외
    local_markers=['부산광역시','대구광역시','인천광역시','대전광역시','울산광역시',
                   '세종특별자치시','강원특별자치도','충청북도','충청남도','전북특별자치도',
                   '경상북도','경상남도','제주특별자치도']
    if any(x in raw for x in local_markers):
        return ''
    return '중앙정부'

def public_service_api_candidates():
    # 정부24 대한민국 공공서비스 정보 v3
    # 공식 엔드포인트:
    #   /serviceList, /serviceDetail, /supportConditions
    # 인증키는 GitHub Secret PUBLIC_DATA_API_KEY -> workflow에서 PUBLIC_SERVICE_API_KEY로 전달.
    key=(os.getenv('PUBLIC_SERVICE_API_KEY','') or os.getenv('PUBLIC_DATA_API_KEY','')).strip()
    if not key:
        return []

    rows=[]
    page=1
    per_page=100
    max_pages=30  # 최대 3,000건. 실행시간 폭주 방지.
    while page <= max_pages:
        obj=_gov24_get('serviceList', key, {'page':page,'perPage':per_page})
        data=obj.get('data') if isinstance(obj,dict) else None
        if not isinstance(data,list) or not data:
            break
        rows.extend(data)
        total=int(obj.get('totalCount') or obj.get('matchCount') or len(rows))
        if len(rows) >= total or len(data) < per_page:
            break
        page += 1

    # 사이트 범위 + 가치 필터
    selected=[]
    for x in rows:
        if not isinstance(x,dict):
            continue
        region=_gov24_region(x)
        if not region:
            continue
        raw=json.dumps(x,ensure_ascii=False)
        if value_score(raw) < 1:
            continue
        selected.append((x,region))

    # 지원조건은 사이트에 실제로 올릴 후보만 조회.
    # 과도한 API 호출을 막기 위해 가치점수/수정일 기준 최대 350개.
    selected.sort(
        key=lambda pair: (
            value_score(json.dumps(pair[0],ensure_ascii=False)),
            str(pair[0].get('수정일시') or '')
        ),
        reverse=True
    )
    selected=selected[:350]

    condition_map={}
    def fetch_condition(item):
        x,_=item
        sid=str(x.get('서비스ID') or '').strip()
        if not sid:
            return sid, {}
        obj=_gov24_get('supportConditions', key, {
            'page':1,'perPage':10,'cond[서비스ID::EQ]':sid
        }, timeout=25)
        data=obj.get('data') if isinstance(obj,dict) else None
        return sid, (data[0] if isinstance(data,list) and data else {})

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for sid,cond in ex.map(fetch_condition, selected):
            if sid:
                condition_map[sid]=cond

    out=[]
    for x,region in selected:
        title=clean(x.get('서비스명') or '')
        if not title:
            continue
        sid=str(x.get('서비스ID') or '')
        condition_text=_gov24_condition_text(condition_map.get(sid,{}))
        eligibility=clean(x.get('지원대상') or x.get('선정기준') or '')
        if condition_text:
            eligibility=(condition_text + (' · ' + eligibility if eligibility else ''))[:260]
        benefit=clean(x.get('지원내용') or '') or '공식 공고에서 지원내용 확인'
        period=clean(x.get('신청기한') or '') or '공식 공고 확인'
        apply_method=clean(x.get('신청방법') or '') or '공식 신청처 확인'
        summary=clean(x.get('서비스목적요약') or '') or benefit[:180]
        url=clean(x.get('상세조회URL') or '') or 'https://www.gov.kr/portal/rcvfvrSvc/main'
        category=category_from(
            ' '.join([title, str(x.get('서비스분야') or ''), benefit, eligibility]),
            '복지'
        )
        status=infer_status(period, period)

        p={
            'id': stable_id('gov24', sid or title),
            'title': normalize_title(title),
            'summary': summary[:220],
            'region': region,
            'category': category,
            'status': status,
            'eligibility': eligibility[:260] or '공식 공고에서 자격 확인',
            'benefit': benefit[:260],
            'period': period[:180],
            'apply_method': apply_method[:220],
            'source_name': '정부24 공공서비스 Open API',
            'url': url,
            'review_required': False if benefit and eligibility and period else True,
            'value_score': value_score(json.dumps(x,ensure_ascii=False)),
            'source_updated_at': clean(x.get('수정일시') or ''),
            'service_id': sid,
        }
        out.append(p)

    print('Gov24 API:', len(rows), 'fetched /', len(selected), 'selected /', len(out), 'published')
    return out

def dedupe_key(p):
    t=re.sub(r'[^0-9가-힣a-z]','',p.get('title','').lower())
    t=re.sub(r'20\d{2}|\d{1,4}(?:만원|억원|원|%)?','',t)
    for w in ['서울시','서울특별시','경기도','전남도','전라남도','광주광역시','지원사업','신청','모집','지원','사업']:
        t=t.replace(w,'')
    return t[:60] or p.get('id','')

def rank(p):
    completeness=sum('확인' not in str(p.get(k,'')) for k in ('benefit','eligibility','period','apply_method'))
    return (SOURCE_RANK.get(p.get('source_name',''),1), completeness, 0 if p.get('review_required') else 1, p.get('value_score',0))

def main():
    old=json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else {'policies':[]}
    # 사람이 넣은 seed/검증 정책과 API 정책은 보존. 기존 rss/auto 수집분은 새로 생성해 오염 누적 방지.
    keep={p['id']:p for p in old.get('policies',[]) if not p.get('id','').startswith(('rss-','auto-'))}

    raw=[]
    for src in RSS_SOURCES:raw += rss_candidates(*src)
    for cfg in LIST_SOURCES:raw += list_candidates(cfg)
    # 가치 높은 후보만 상세 페이지를 조회해 Actions 실행시간을 제한.
    raw=sorted(raw,key=lambda x:x.get('score',0),reverse=True)[:150]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        auto=list(ex.map(enrich_candidate,raw))
    api_rows=youth_api_candidates()+public_service_api_candidates()

    by={}
    for p in list(keep.values())+auto+api_rows:
        if p.get('value_score',0)<1 and p.get('id','').startswith('auto-'):continue
        key=dedupe_key(p)
        cur=by.get(key)
        if cur is None or rank(p)>rank(cur):by[key]=p

    status_order={'신청가능':5,'마감임박':4,'예정':3,'확인필요':2,'마감':1}
    rows=sorted(by.values(),key=lambda p:(status_order.get(p.get('status'),0),rank(p),p.get('title','')),reverse=True)[:700]
    now=datetime.now(KST).isoformat(timespec='seconds')
    sources=sorted(set([x[2] for x in RSS_SOURCES]+[x['source'] for x in LIST_SOURCES]+(['온통청년 오픈 API'] if os.getenv('YOUTH_API_KEY','').strip() else [])+(['정부24 공공서비스 Open API'] if (os.getenv('PUBLIC_SERVICE_API_KEY','').strip() or os.getenv('PUBLIC_DATA_API_KEY','').strip()) else [])))
    obj={'updated_at':now,'policy_count':len(rows),'sources':sources,'central_api_ready':bool(os.getenv('PUBLIC_SERVICE_API_KEY','').strip() or os.getenv('PUBLIC_DATA_API_KEY','').strip()),'policies':rows}
    DATA.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    print('policies:',len(rows),'structured:',sum(not p.get('review_required') for p in rows),'sources:',', '.join(sources))
    print('regions:',{r:sum(1 for p in rows if p.get('region')==r) for r in ['중앙정부','서울','경기','전남광주통합특별시']})

if __name__=='__main__':main()
