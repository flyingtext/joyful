# 프로젝트 아키텍처 설계

## 1) Django 프로젝트/앱 구조
- **프로젝트 루트**: `config/`
  - `settings.py`: 환경 분리(로컬/프로덕션), DB 및 스토리지 설정, DRF/스토리지 백엔드 등록.
  - `urls.py`: 전역 URL 설정 및 API 버전 네임스페이스.
  - `wsgi.py` / `asgi.py`: 배포 및 비동기 지원.
- **앱 구성**
  - `users`: 사용자 인증/프로필 관리, 소셜 로그인 확장 포인트.
  - `photos`: 사진 업로드, 메타데이터, 태깅, 앨범/공유 도메인 로직.
  - `ai`: Ollama API 연동, 캡션/태그 자동 생성 서비스.
  - `search`: 검색 인덱스 및 API(간단한 RDB 쿼리 → 추후 Elasticsearch 등으로 교체 가능하도록 추상화).
- **레이어드 구조 원칙** (각 앱 내 공통)
  - `models.py`: 순수 도메인 모델과 DB 매핑.
  - `serializers.py`: 입력/출력 변환, 검증.
  - `views.py`: DRF ViewSet/APIView. 비즈니스 로직 호출만 수행.
  - `services/`: 도메인 서비스. 트랜잭션, 권한 검사, 비즈니스 규칙 캡슐화.
  - `selectors/`: 조회 전용 쿼리 집합(예: 검색/리스트 필터용).
  - `tasks/`: 비동기 작업(Celery/RQ) 정의. AICaptionJob 처리 등.
  - `schemas.py`: OpenAPI/Pydantic 스타일의 내부 스키마(필요 시).

## 2) 핵심 도메인 모델
- **User (users.User)**
  - `id (PK)`, `email`, `password`, `name`, `profile_image`, `created_at`, `updated_at`, `is_active`.
  - Django 기본 AbstractUser 확장(이메일 기반 로그인).

- **Photo (photos.Photo)**
  - `id (PK)`, `owner (FK → User)`, `file_path`, `thumbnail_path`, `title`, `description`, `width`, `height`, `taken_at`, `location`, `visibility (public/private/shared)`, `storage_backend`(로컬/S3), `checksum`, `created_at`.
  - 업로드 후 비동기 처리: 썸네일 생성, AI 캡션/태그 요청.

- **Album (photos.Album)**
  - `id (PK)`, `owner (FK → User)`, `title`, `description`, `cover_photo (FK → Photo, nullable)`, `visibility`, `created_at`, `updated_at`.
  - 공유: `AlbumShare`를 통해 다른 사용자 또는 링크 기반 접근 제어.

- **AlbumShare (photos.AlbumShare)**
  - `id (PK)`, `album (FK → Album)`, `shared_with (FK → User, nullable)`, `share_link_token`, `permission (view/comment)`, `expires_at`, `created_at`.

- **Tag (photos.Tag)**
  - `id (PK)`, `name`(고유), `created_at`.
  - `PhotoTag` 중간 테이블로 사진-태그 다대다.

- **PhotoTag (photos.PhotoTag)**
  - `id (PK)`, `photo (FK → Photo)`, `tag (FK → Tag)`, `source (ai/manual)`, `created_at`.

- **AICaptionJob (ai.AICaptionJob)**
  - `id (PK)`, `photo (FK → Photo)`, `status (pending/running/success/failed)`, `model`(예: llava, llava-phi3, qwen2.5-vl), `caption_ko`, `raw_response`, `error_message`, `started_at`, `finished_at`, `created_at`.
  - Task 큐에서 실행. 성공 시 Photo.description/태그 업데이트.

## 3) MySQL 기준 ERD (핵심 필드)

```
User (id PK, email, password, name, profile_image, is_active, created_at, updated_at)
Photo (id PK, owner_id FK→User, file_path, thumbnail_path, title, description,
       width, height, taken_at, location, visibility, storage_backend, checksum, created_at)
Album (id PK, owner_id FK→User, title, description, cover_photo_id FK→Photo, visibility,
       created_at, updated_at)
AlbumShare (id PK, album_id FK→Album, shared_with_id FK→User NULL, share_link_token,
            permission, expires_at, created_at)
Tag (id PK, name UNIQUE, created_at)
PhotoTag (id PK, photo_id FK→Photo, tag_id FK→Tag, source, created_at)
AICaptionJob (id PK, photo_id FK→Photo, status, model, caption_ko, raw_response,
             error_message, started_at, finished_at, created_at)
```

### 관계 요약
- User 1:N Photo, Album.
- Album 1:N AlbumShare.
- Photo N:M Tag (PhotoTag 매개).
- Photo 1:N AICaptionJob.
- Album ↔ Photo: 커버(1:1), 추후 AlbumPhoto 중간 테이블로 다대다 확장 가능.

