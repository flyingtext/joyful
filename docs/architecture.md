# Joyful 시스템 아키텍처 및 도메인 설계

## 전체 개요
- **목표**: 사진 업로드, 자동 한국어 캡션·태깅, 검색, 앨범 관리, 공유 기능을 제공하는 풀스택 웹앱.
- **백엔드**: FastAPI (Python)
- **DB**: PostgreSQL
- **오브젝트 스토리지**: S3 호환(MinIO)
- **벡터 검색**: Qdrant
- **프론트엔드**: Next.js + React + TypeScript + Tailwind CSS
- **AI 계층**: 초기에는 더미 캡션/태깅 함수, 이후 LLaVA/GPT-4o API로 교체 예정.

## 아키텍처 흐름
1. **업로드**: 사용자는 Next.js 프론트엔드에서 사진을 업로드 → 프리사인 URL 생성 → MinIO에 저장.
2. **메타데이터 처리**: 백엔드가 업로드 이벤트를 받아 이미지 해시/리사이즈/썸네일 처리 후 DB에 메타데이터 저장.
3. **캡션·태그 생성**: AI 서비스가 비동기 작업으로 캡션(ko)과 태그를 생성 → DB 업데이트 및 Qdrant에 벡터 업서트.
4. **검색**: 키워드 검색(캡션/태그/앨범명) + 벡터 검색(이미지/텍스트) 결합한 하이브리드 쿼리.
5. **앨범/공유**: 앨범 단위의 접근 제어, 공유 링크 발급(만료/비밀번호 옵션) 제공.

## 디렉터리 구조(제안)
```
joyful/
├─ backend/
│  ├─ app/
│  │  ├─ api/              # FastAPI 라우터
│  │  ├─ core/             # 설정, 보안, 로깅
│  │  ├─ db/               # SQLAlchemy 세션/마이그레이션
│  │  ├─ models/           # ORM 모델
│  │  ├─ schemas/          # Pydantic 스키마
│  │  ├─ services/         # 도메인 서비스 (upload, captioning, search 등)
│  │  ├─ workers/          # 백그라운드 작업(큐/스케줄러)
│  │  └─ main.py           # FastAPI 엔트리포인트
│  └─ tests/               # 백엔드 단위/통합 테스트
├─ frontend/
│  ├─ src/
│  │  ├─ app/              # Next.js 앱 라우트
│  │  ├─ components/       # UI 컴포넌트
│  │  ├─ lib/              # API 클라이언트, hooks, utils
│  │  ├─ store/            # 상태 관리 (예: Zustand)
│  │  └─ types/            # 타입 정의
│  └─ tests/               # 프론트엔드 테스트 (Jest/Playwright)
├─ infra/
│  ├─ docker/              # Dockerfile, compose, MinIO/Qdrant/Postgres 로컬 스택
│  └─ terraform/           # (옵션) 클라우드 IaC
├─ docs/                   # 설계/결정 기록
└─ README.md
```

## 핵심 도메인 모델
- **User**: 계정, 권한, 소셜 로그인 정보(옵션).
- **Photo**: 원본 경로, 썸네일 경로, 해시, 촬영/업로드 시각, EXIF.
- **Caption**: 사진별 다국어 캡션(초기에는 ko 1개), 생성 상태/출처(모델명), 신뢰도.
- **Tag**: 단일 태그 엔티티. Photo-Tag 다대다 관계로 연결.
- **Album**: 사용자 소유의 사진 컬렉션, 커버 이미지, 설명.
- **AlbumPhoto**: 앨범-사진 매핑 및 순서 정보.
- **ShareLink**: 앨범/사진 공유 링크, 만료/비밀번호/권한 범위.
- **VectorEmbedding**: Qdrant에 저장되는 임베딩 메타데이터(사진 ID, 모델, 버전, 공간).
- **TaskQueueJob**: 비동기 작업 상태(예: 캡션 생성, 리사이즈, 임베딩 추출).

## 백엔드 모듈 설계(초안)
- `core.config`: 설정 로드(환경변수), S3/Qdrant/DB 연결 정보.
- `core.security`: JWT/세션, 공유 링크 토큰 처리.
- `db.session`: SQLAlchemy 세션 및 Alembic 마이그레이션 훅.
- `models`: ORM 정의 (위 도메인 모델 매핑).
- `schemas`: 요청/응답용 Pydantic 스키마.
- `services.storage`: 업로드 프리사인 URL, 오브젝트 메타 관리.
- `services.captioning`: 더미 캡션/태깅 → 향후 모델 연동.
- `services.search`: 키워드 + Qdrant 하이브리드 검색.
- `services.album`: 앨범/공유 관리.
- `workers`: 백그라운드 큐(예: RQ/Celery/FastAPI BackgroundTasks) 실행.

## 프론트엔드 모듈 설계(초안)
- `lib/api-client`: 백엔드 OpenAPI 기반 클라이언트 래퍼.
- `lib/hooks`: 데이터 훅(SWR/React Query), 업로드 진행 상태 관리.
- `components/ui`: Tailwind 기반 재사용 UI.
- `components/photo`: 사진 카드/그리드, 업로드 드롭존, 상세 뷰.
- `components/album`: 앨범 생성/편집/공유 모달.
- `app/(routes)`: 페이지 라우트, 레이아웃, 메타데이터 설정.

## 데이터 흐름 요약
- 업로드 → 스토리지 저장 → DB 메타데이터 → 큐 작업(캡션/태그/임베딩) → 검색 인덱싱 → UI 조회/필터.
- 검색 요청 시 텍스트 검색 + 벡터 검색 결과를 통합하여 정렬/필터링.

## 향후 단계
1. 백엔드 스켈레톤(FastAPI + SQLAlchemy + Pydantic) 생성.
2. 스토리지/DB/Qdrant 설정 모듈 작성.
3. 도메인 모델/스키마/라우터 순차 구현.
4. 프론트엔드 Next.js 초기 세팅 및 API 클라이언트 연결.
5. e2e 플로우(업로드 → 캡션/태그 → 검색) 최소 기능 달성 후 개선.
