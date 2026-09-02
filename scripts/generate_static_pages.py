#!/usr/bin/env python3
import html
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "policies.json"
BASE = "https://kimjunnem.github.io/"
KST = timezone(timedelta(hours=9))

POLICY_DIR = ROOT / "policy"
CATEGORY_DIR = ROOT / "category"
REGION_DIR = ROOT / "region"

STATIC_CSS = """\
:root{--blue:#0b4da2;--ink:#1f2937;--sub:#5b6573;--line:#dbe1e8;--bg:#f6f8fb}
*{box-sizing:border-box}body{margin:0;font-family:Arial,"Noto Sans KR","Apple SD Gothic Neo",sans-serif;color:var(--ink);background:var(--bg);line-height:1.65}
a{color:#075da8;text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:980px;margin:auto;padding:0 20px}
.top{background:#fff;border-top:4px solid var(--blue);border-bottom:1px solid var(--line)}.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:68px}
.brand{font-size:22px;font-weight:800;color:#16324a}.nav{font-size:14px;color:var(--sub)}
main{padding:34px 0 60px}.crumb{font-size:13px;color:var(--sub);margin-bottom:12px}
h1{font-size:30px;line-height:1.35;margin:0 0 12px;letter-spacing:-.5px}h2{font-size:21px;margin:30px 0 10px}
.lead{font-size:17px;color:#344657;margin:0 0 20px}.meta{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 22px}
.badge{display:inline-block;border:1px solid #cfd8e3;background:#fff;border-radius:999px;padding:5px 10px;font-size:13px}
.answer{background:#fff;border:1px solid var(--line);border-left:4px solid var(--blue);padding:18px 20px;margin:18px 0}
.facts{border-top:2px solid #456d8b;background:#fff}.row{display:grid;grid-template-columns:150px 1fr;border-bottom:1px solid var(--line)}.row b{padding:14px;background:#f0f4f7}.row div{padding:14px}
.source{background:#fff;border:1px solid var(--line);padding:18px;margin-top:28px}.source p{margin:6px 0}
.list{display:grid;grid-template-columns:1fr 1fr;gap:12px}.card{display:block;background:#fff;border:1px solid var(--line);padding:16px}.card strong{display:block;color:#23384b;margin-bottom:6px}.card span{font-size:13px;color:var(--sub)}
.note{font-size:13px;color:var(--sub)}footer{background:#2f4657;color:#dfe7ec;font-size:13px}.foot{padding:22px 20px}
@media(max-width:700px){h1{font-size:26px}.row{grid-template-columns:110px 1fr}.list{grid-template-columns:1fr}.top .wrap{min-height:60px}}
"""

def text(v, fallback="확인 필요"):
    v = re.sub(r"\s+", " ", str(v or "")).strip()
    return v if v else fallback

def safe(v, fallback="확인 필요"):
    return html.escape(text(v, fallback), quote=True)

def url_for(path):
    return BASE.rstrip("/") + "/" + quote(path, safe="/:.?=&-%")

def shell(title, description, canonical, body, noindex=False):
    robots = "noindex,follow" if noindex else "index,follow,max-snippet:-1,max-image-preview:large"
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description[:155], quote=True)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{html.escape(canonical, quote=True)}">
<link rel="stylesheet" href="../static-pages.css">
<meta name="google-adsense-account" content="ca-pub-4192319901350402">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4192319901350402" crossorigin="anonymous"></script>
</head>
<body>
<header class="top"><div class="wrap"><a class="brand" href="../">혜택레이더</a><div class="nav">공식 출처 기반 민간 정보서비스</div></div></header>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap foot">혜택레이더 · 최종 신청 전 공식 공고를 확인하세요.</div></footer>
</body></html>"""

def policy_html(p, checked):
    pid = p["id"]
    title = text(p.get("title"), "지원정책")
    summary = text(p.get("summary"), text(p.get("benefit")))
    canonical = url_for(f"policy/{pid}.html")
    source_url = text(p.get("url"), "")
    noindex = bool(p.get("review_required"))
    rows = [
        ("지원 대상", p.get("eligibility")),
        ("지원 내용", p.get("benefit")),
        ("신청 기간", p.get("period")),
        ("신청 방법", p.get("apply_method")),
    ]
    fact_html = "".join(
        f'<div class="row"><b>{html.escape(k)}</b><div>{safe(v)}</div></div>'
        for k, v in rows
    )
    source_link = (
        f'<a href="{html.escape(source_url, quote=True)}" rel="noopener noreferrer">공식 원문 확인 →</a>'
        if source_url.startswith("http") else "공식 출처 링크 확인 필요"
    )
    category = text(p.get("category"), "기타")
    body = f"""
<div class="crumb"><a href="../">홈</a> › <a href="../category/{quote(category)}.html">{html.escape(category)}</a></div>
<h1>{html.escape(title)}</h1>
<p class="lead">{html.escape(summary)}</p>
<div class="meta">
<span class="badge">{safe(p.get("status"))}</span>
<span class="badge">{safe(p.get("region"))}</span>
<span class="badge">{safe(p.get("category"))}</span>
</div>
<div class="answer"><b>핵심 내용</b><div>{safe(p.get("benefit"))}</div></div>
<div class="facts">{fact_html}</div>
<div class="source">
<h2>공식 출처</h2>
<p>{safe(p.get("source_name"))}</p>
<p>{source_link}</p>
<p class="note">정보 확인일: {html.escape(checked)} · 실제 자격·금액·신청기간은 공식 공고가 최종 기준입니다.</p>
</div>"""
    return shell(f"{title} | 혜택레이더", summary, canonical, body, noindex=noindex)

def listing_html(kind, name, policies, checked):
    label = "지역" if kind == "region" else "분야"
    title = f"{name} 지원정책"
    canonical = url_for(f"{kind}/{quote(name)}.html")
    ordered = sorted(
        policies,
        key=lambda p: (
            {"마감임박": 5, "신청가능": 4, "예정": 3, "확인필요": 2, "마감": 1}.get(text(p.get("status")), 0),
            int(p.get("value_score") or 0),
        ),
        reverse=True,
    )
    cards = []
    for p in ordered:
        if p.get("review_required"):
            continue
        cards.append(
            f'<a class="card" href="../policy/{html.escape(p["id"])}.html">'
            f'<strong>{safe(p.get("title"))}</strong>'
            f'<span>{safe(p.get("status"))} · {safe(p.get("region"))} · {safe(p.get("category"))}</span>'
            f'</a>'
        )
    body = f"""
<div class="crumb"><a href="../">홈</a> › {html.escape(label)}별 혜택</div>
<h1>{html.escape(title)}</h1>
<p class="lead">{html.escape(name)}과 관련된 지원정책을 공식 출처 기준으로 정리했습니다.</p>
<p class="note">정보 확인일: {html.escape(checked)} · 총 {len(cards)}건</p>
<div class="list">{''.join(cards) if cards else '<div class="card">현재 표시할 정책이 없습니다.</div>'}</div>"""
    desc = f"{name} 지원금, 복지, 주거, 일자리 등 신청 가능한 정책의 대상·지원내용·신청기간·신청방법을 확인하세요."
    return shell(f"{title} | 혜택레이더", desc, canonical, body)

def sitemap_url(path, lastmod, changefreq="daily", priority="0.7"):
    return (
        "  <url>"
        f"<loc>{xml_escape(url_for(path))}</loc>"
        f"<lastmod>{lastmod}</lastmod>"
        f"<changefreq>{changefreq}</changefreq>"
        f"<priority>{priority}</priority>"
        "</url>"
    )

def main():
    if not DATA.exists():
        raise SystemExit("data/policies.json not found")

    obj = json.loads(DATA.read_text(encoding="utf-8"))
    policies = [p for p in obj.get("policies", []) if p.get("id")]
    updated = obj.get("updated_at") or datetime.now(KST).isoformat(timespec="seconds")
    checked = updated[:10]
    lastmod = checked

    for d in (POLICY_DIR, CATEGORY_DIR, REGION_DIR):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    (ROOT / "static-pages.css").write_text(STATIC_CSS, encoding="utf-8")

    real_policy_paths = []
    for p in policies:
        path = POLICY_DIR / f"{p['id']}.html"
        path.write_text(policy_html(p, checked), encoding="utf-8")
        if not p.get("review_required"):
            real_policy_paths.append(f"policy/{p['id']}.html")

    categories = sorted({text(p.get("category"), "기타") for p in policies})
    regions = sorted({text(p.get("region"), "중앙정부") for p in policies})

    for name in categories:
        subset = [p for p in policies if text(p.get("category"), "기타") == name]
        (CATEGORY_DIR / f"{name}.html").write_text(
            listing_html("category", name, subset, checked), encoding="utf-8"
        )

    for name in regions:
        subset = [p for p in policies if text(p.get("region"), "중앙정부") == name]
        (REGION_DIR / f"{name}.html").write_text(
            listing_html("region", name, subset, checked), encoding="utf-8"
        )

    high_conf = [p for p in policies if not p.get("review_required")]
    ai_rows = []
    for p in high_conf:
        ai_rows.append({
            "id": p["id"],
            "title": text(p.get("title")),
            "summary": text(p.get("summary"), text(p.get("benefit"))),
            "region": text(p.get("region")),
            "category": text(p.get("category")),
            "status": text(p.get("status")),
            "eligibility": text(p.get("eligibility")),
            "benefit": text(p.get("benefit")),
            "period": text(p.get("period")),
            "apply_method": text(p.get("apply_method")),
            "source_name": text(p.get("source_name")),
            "official_url": text(p.get("url"), ""),
            "page_url": url_for(f"policy/{p['id']}.html"),
            "checked_at": checked,
        })

    (ROOT / "data" / "ai-index.json").write_text(
        json.dumps({"updated_at": updated, "count": len(ai_rows), "policies": ai_rows},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (ROOT / "data" / "answers.json").write_text(
        json.dumps(ai_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    sitemap = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        sitemap_url("", lastmod, "daily", "1.0"),
        sitemap_url("budget-2027.html", lastmod, "weekly", "0.8"),
        sitemap_url("about.html", lastmod, "monthly", "0.4"),
        sitemap_url("privacy.html", lastmod, "monthly", "0.3"),
        sitemap_url("disclaimer.html", lastmod, "monthly", "0.3"),
        sitemap_url("contact.html", lastmod, "monthly", "0.3"),
    ]
    sitemap += [sitemap_url(f"category/{name}.html", lastmod, "daily", "0.8") for name in categories]
    sitemap += [sitemap_url(f"region/{name}.html", lastmod, "daily", "0.8") for name in regions]
    sitemap += [sitemap_url(path, lastmod, "daily", "0.9") for path in real_policy_paths]
    sitemap.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")

    llms = [
        "# 혜택레이더",
        "",
        "대한민국 지원금·복지·주거·일자리 정책을 공식 출처 기준으로 정리하는 민간 정보서비스입니다.",
        f"데이터 확인일: {checked}",
        "",
        "## 주요 페이지",
        f"- 메인: {BASE}",
        f"- 2027 예산안: {BASE}budget-2027.html",
        f"- AI 정책 인덱스: {BASE}data/ai-index.json",
        "",
        "## 분야별",
    ]
    llms += [f"- {name}: {url_for(f'category/{name}.html')}" for name in categories]
    llms += ["", "## 지역별"]
    llms += [f"- {name}: {url_for(f'region/{name}.html')}" for name in regions]
    llms += ["", "개별 정책 페이지에는 대상, 지원내용, 신청기간, 신청방법, 공식 출처가 포함됩니다."]
    (ROOT / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")

    counts = Counter(text(p.get("status")) for p in high_conf)
    print(f"generated policy pages: {len(policies)} / indexed: {len(real_policy_paths)}")
    print(f"category pages: {len(categories)} / region pages: {len(regions)}")
    print("status:", dict(counts))

if __name__ == "__main__":
    main()
