혜택레이더 정적페이지 복구 패치

왜 필요한가
- 기존 sitemap.xml에는 category/region/policy URL이 있었지만 실제 HTML 파일이 저장소에 없었습니다.
- 그래서 Search Console에서 색인 요청이 거부될 수 있었습니다.

이 패치가 하는 일
1. data/policies.json을 읽어 policy/*.html 실제 상세페이지 생성
2. category/*.html 분야별 허브 생성
3. region/*.html 지역별 허브 생성
4. 실제 존재하는 페이지만 sitemap.xml에 기록
5. review_required 정책은 페이지는 만들되 noindex 처리하고 sitemap/AI index에서는 제외
6. data/ai-index.json, data/answers.json, llms.txt 갱신
7. 평일 자동 정책 업데이트 때마다 위 파일도 같이 자동 재생성

업로드할 파일
- scripts/generate_static_pages.py
- .github/workflows/update-and-deploy.yml

업로드 후
GitHub > Actions > Update policies > Run workflow 를 한 번 실행하세요.
성공 후 저장소에 policy / category / region 폴더가 생기면 복구 완료입니다.
