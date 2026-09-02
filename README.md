# 혜택레이더 v0.6 — 정부24 공공서비스 API 연결 패치

업로드할 파일은 2개입니다.

1. `scripts/update_policies.py`
2. `.github/workflows/update-and-deploy.yml`

GitHub에서 같은 경로의 기존 파일을 교체한 뒤 Commit하고,
Actions → **Update policies and deploy** → **Run workflow**를 실행하세요.

## 이번 버전
- 정부24 공식 v3 API 고정 연결
  - `/serviceList`
  - `/supportConditions`
- 기존에 등록한 GitHub Secret `PUBLIC_DATA_API_KEY`를 자동화에 연결
- 서비스명/지원대상/지원내용/신청방법/신청기한/상세조회URL을 구조화해서 사용
- 연령·중위소득·근로자/구직자·1인가구·무주택 등 지원조건을 추가 반영
- 중앙정부 + 서울 + 경기 + 광주/전남만 선별
- 다른 지역 지방서비스는 제외
- API 요청 폭주 방지를 위해 정부24 후보 최대 350개까지만 지원조건 상세조회


## GitHub Pages
이 저장소는 사용자 사이트 `https://kimjunnem.github.io/` 루트에서 배포하도록 구성되어 있습니다.
