# Conversation Log

이 파일은 Claude Code 대화 세션의 타임라인을 기록합니다.
세션이 바뀌어도 이전 논의 내용을 빠르게 파악할 수 있습니다.

**사용 방법**: `/log-session` 명령어로 현재 세션 내용 추가

---

## [2025-01-04 13:00] 데이터셋 관리 UI 통합 및 설계 논의

### 논의 주제
- 데이터셋 UI 레이아웃 통합 문제
- 하드코딩 데이터 제거
- 데이터셋 업로드 방식 설계
- 버전닝 전략
- 무결성 관리

### 주요 결정사항

#### 1. UI 레이아웃 통합
- **문제**: 데이터셋 버튼 클릭 시 전체 화면으로 나와서 기존 레이아웃(사이드바, 채팅, 작업공간) 무시
- **해결**:
  - 새 `DatasetPanel` 컴포넌트 생성 (컴팩트 테이블 디자인)
  - `app/page.tsx`에 상태 관리 추가
  - Sidebar에서 라우팅 대신 핸들러 호출
- **결과**: AdminProjectsPanel과 동일한 패턴으로 작업공간에 통합

#### 2. 하드코딩 데이터 제거
- **문제**: DB에 6개 샘플 데이터셋 하드코딩됨 (cls-imagenet-10 등)
- **원칙 위반**: CLAUDE.md - "no shortcut, no hardcoding, no dummy data"
- **해결**: DB에서 모든 샘플 데이터 삭제
- **결과**: 실제 업로드한 데이터만 표시

#### 3. task_type은 데이터셋 속성이 아니다
- **핵심 통찰**: 같은 이미지를 classification, detection, segmentation 등 다양하게 활용 가능
- **결정**:
  - ❌ Dataset.task_type 삭제
  - ✅ TrainingJob.task_type 추가
  - 데이터셋은 이미지 저장소, 학습 작업이 용도 결정

#### 4. 폴더 구조 유지
- **결정**: 업로드 시 폴더 구조 항상 유지
- **R2 경로**: `datasets/{id}/images/{original_path}`
- **이유**:
  - 원본 구조 보존
  - 파일명 충돌 방지
  - 유연성 확보

#### 5. labeled의 정의
- **정의**: `labeled = annotation.json 존재 여부`
- **규칙**:
  - labeled 업로드는 폴더만 가능 (annotation.json 필요)
  - unlabeled는 폴더/개별 파일 모두 가능
  - labeled 데이터셋에 labeled 폴더 병합 **금지**

#### 6. meta.json 생성 시점
- **unlabeled**: meta.json 없음 (DB만)
- **labeled 전환**: annotation.json + meta.json 함께 생성
- **export**: 항상 meta.json 포함
- **Single Source of Truth**: DB

#### 7. 버전닝 전략: Mutable + Snapshot
- **원칙**:
  - 데이터셋은 기본적으로 가변(mutable)
  - 학습 시작 시 자동 스냅샷 생성
  - 사용자가 명시적 버전 생성 가능 (v1, v2...)
- **효율성**:
  - 이미지는 모든 버전이 공유
  - 스냅샷은 annotation.json만 저장
  - 저장 공간 99% 절약 (10GB + 10MB + 10MB vs 30GB)

#### 8. 이미지 삭제 허용 + 무결성 관리
- **이미지 삭제**: 허용
- **영향받는 스냅샷 처리**:
  - 옵션 A: Broken 표시 (재현 불가)
  - 옵션 B: 자동 복구 (annotation 수정)
- **주기적 무결성 체크**: Celery task로 구현

### 구현 내용

#### Frontend
- `components/DatasetPanel.tsx`: 컴팩트 테이블 UI (새 파일)
  - 검색, 정렬 기능
  - 확장 가능한 행 (이미지 갤러리)
  - 이미지 업로드/조회

- `app/page.tsx`: 상태 관리 추가
  - `showDatasets` state
  - `handleOpenDatasets()` 핸들러
  - 작업공간에 DatasetPanel 렌더링

- `components/Sidebar.tsx`: 라우팅 제거
  - `router.push('/datasets')` → `onOpenDatasets()` 호출

#### Backend
- 기존 개별 이미지 업로드 API 유지
  - POST `/datasets/{id}/images`
  - GET `/datasets/{id}/images`

#### Database
- 하드코딩된 6개 샘플 데이터셋 삭제

### 관련 문서

- **설계 문서**: [DATASET_MANAGEMENT_DESIGN.md](./datasets/DATASET_MANAGEMENT_DESIGN.md)
  - 데이터 모델
  - 스토리지 구조
  - 12가지 업로드 시나리오
  - 버전닝 전략
  - 무결성 관리

- **기존 문서**:
  - [DICE_FORMAT_v2.md](./datasets/DICE_FORMAT_v2.md)
  - [STORAGE_ACCESS_PATTERNS.md](./datasets/STORAGE_ACCESS_PATTERNS.md)

### 다음 단계

#### Phase 2: 폴더 업로드 (다음 구현)
- [ ] 폴더 구조 유지 업로드 (`webkitdirectory`)
- [ ] labeled 데이터셋 생성 (annotation.json 포함)
- [ ] DB 모델 확장 (labeled, class_names, is_snapshot 등)

#### Phase 3: 버전닝
- [ ] 학습 시 자동 스냅샷
- [ ] 명시적 버전 생성
- [ ] 스냅샷 목록 UI

#### Phase 4: 무결성 관리
- [ ] 이미지 삭제 시 영향 분석
- [ ] Broken/복구 로직
- [ ] 주기적 무결성 체크

### 기술 스택
- Frontend: Next.js 14, TypeScript, Tailwind CSS
- Backend: FastAPI, Python, SQLAlchemy
- Storage: Cloudflare R2 (S3-compatible)
- Database: SQLite (local), PostgreSQL (production)

### 핵심 파일
- `mvp/frontend/components/DatasetPanel.tsx` (새로 생성)
- `mvp/frontend/app/page.tsx` (수정)
- `mvp/frontend/components/Sidebar.tsx` (수정)
- `mvp/backend/app/api/datasets_images.py` (기존)
- `mvp/backend/app/utils/r2_storage.py` (기존)

---

