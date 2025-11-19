# E2E Test Guide

프론트엔드-백엔드 통합 테스트 가이드. Inference Test를 레퍼런스로 작성됨.

## 핵심 원칙

### 1. 프론트엔드 코드 우선 분석

**테스트는 프론트엔드 코드를 직접 참조해서 동일한 API 호출 패턴을 사용해야 함**

```
❌ 잘못된 접근: API 문서만 보고 테스트 작성
✅ 올바른 접근: 프론트엔드 코드 분석 → 동일한 호출 패턴으로 테스트 작성
```

**이유:**
- 프론트엔드에 버그가 있어도 테스트가 통과할 수 있음
- 테스트 성공이 실제 사용자 경험을 보장하지 않음

### 2. 프론트엔드-테스트 동기화

**프론트엔드와 테스트가 함께 성공/실패해야 함**

| 상황 | 의미 |
|------|------|
| 테스트 성공, 프론트엔드 성공 | 정상 |
| 테스트 실패, 프론트엔드 실패 | 정상 (버그 발견) |
| 테스트 성공, 프론트엔드 실패 | **테스트가 무의미** |
| 테스트 실패, 프론트엔드 성공 | 테스트 버그 |

### 3. 전체 프로세스 검증

**단위 curl 테스트가 아닌 E2E 스크립트로 전체 플로우 검증**

```
❌ curl로 개별 API만 테스트
✅ Python 스크립트로 전체 사용자 시나리오 테스트
```

---

## 테스트 작성 체크리스트

### Phase 1: 프론트엔드 분석

- [ ] 프론트엔드 컴포넌트 파일 확인
- [ ] API 호출 URL 정확히 파악
- [ ] Request body 구조 확인
- [ ] Response 처리 로직 확인
- [ ] 에러 처리 방식 확인
- [ ] 상태 관리 (폴링, 웹소켓 등) 확인

### Phase 2: 테스트 스크립트 작성

- [ ] 프론트엔드와 동일한 API URL 사용
- [ ] 프론트엔드와 동일한 Request body 구조
- [ ] 프론트엔드와 동일한 폴링 로직
- [ ] 프론트엔드와 동일한 결과 매칭 로직
- [ ] 타임아웃 설정
- [ ] 상세한 로그 출력

### Phase 3: 테스트 실행

- [ ] 테스트 스크립트 실행 및 성공 확인
- [ ] **프론트엔드에서 동일 시나리오 테스트**
- [ ] 두 결과가 일치하는지 확인
- [ ] 불일치 시 원인 분석 및 수정

### Phase 4: 문제 발견 시

- [ ] 프론트엔드 버그인지, 테스트 버그인지 구분
- [ ] 프론트엔드 버그면 프론트엔드 수정
- [ ] 테스트 버그면 테스트 수정
- [ ] 수정 후 다시 Phase 3 수행

---

## 레퍼런스: Inference Test

### 테스트 대상

- **기능**: 이미지 업로드 → 추론 실행 → 결과 표시
- **프론트엔드**: `TestInferencePanel.tsx`
- **백엔드**: `test_inference.py`
- **트레이너**: `predict.py`

### 발견된 문제들

#### 1. 엔드포인트 불일치

| 구분 | URL | 결과 |
|------|-----|------|
| E2E 테스트 | `/inference/jobs/detail/{id}` | 성공 |
| 프론트엔드 | `/inference/jobs/{id}` | 실패 |

**원인**: 테스트가 API 문서 기준, 프론트엔드는 잘못된 URL 사용

**교훈**: 프론트엔드 코드를 먼저 분석했다면 같은 버그를 가진 테스트를 작성해서 함께 실패했을 것

#### 2. 파일명 매칭 불일치

| 단계 | 파일명 |
|------|--------|
| 업로드 전 | `image.jpg` |
| S3 저장 | `uuid-xxx.jpg` |
| 결과 반환 | `uuid-xxx.jpg` |
| 프론트엔드 매칭 | `image.jpg` (원본) |

**원인**: 프론트엔드가 UUID 파일명을 원본으로 매핑하지 않음

**해결**: 업로드 응답의 `uploaded_files` 매핑 정보 활용

#### 3. Task type 불일치

| 백엔드 | 프론트엔드 UI |
|--------|-------------|
| `detection` | `object_detection`만 인식 |

**해결**: 프론트엔드에서 두 값 모두 인식하도록 수정

### 테스트 스크립트

```bash
# 위치: platform/backend/test_inference_e2e.py

# Pretrained 모델로 테스트
python test_inference_e2e.py \
  --job-id 23 \
  --pretrained \
  --images "test_images/*.jpg"

# 학습된 체크포인트로 테스트
python test_inference_e2e.py \
  --job-id 23 \
  --images "test_images/*.jpg"
```

### 검증 결과

```json
{
  "total_images": 2,
  "avg_inference_time_ms": 198.16,
  "results": [
    {
      "image_name": "uuid.jpg",
      "predicted_boxes": [
        {"label": "giraffe", "confidence": 0.8775, "x1": 374, "y1": 64, "x2": 602, "y2": 358}
      ]
    },
    {
      "image_name": "uuid.jpg",
      "predicted_boxes": [
        {"label": "vase", "confidence": 0.8934, ...},
        {"label": "potted plant", "confidence": 0.6381, ...}
      ]
    }
  ]
}
```

---

## 향후 테스트 대상

### Training

- [ ] 데이터셋 업로드 → 학습 시작 → 진행률 표시 → 완료
- 프론트엔드: `TrainingPanel.tsx`
- 체크포인트: `DatasetUpload.tsx`, `TrainingConfig.tsx`

### Export

- [ ] 모델 선택 → Export 형식 선택 → Export 실행 → 다운로드
- 프론트엔드: `ExportJobList.tsx`, `CreateExportModal.tsx`

### Dataset Management

- [ ] 데이터셋 생성 → 이미지 업로드 → 버전 관리
- 프론트엔드: `DatasetPanel.tsx`

---

## 테스트 환경 설정

### 필수 서비스

```bash
# Backend (port 8000)
cd platform/backend
venv/Scripts/python.exe -m uvicorn app.main:app --port 8000

# Frontend (port 3000)
cd platform/frontend
pnpm dev

# MinIO (ports 9000, 9002)
docker-compose up -d minio
```

### 테스트 이미지

```
platform/backend/test_images/
├── 000000000025.jpg  # COCO - 기린
└── 000000000030.jpg  # COCO - 화분
```

---

## 커밋 시 체크리스트

- [ ] 테스트 스크립트 성공
- [ ] 프론트엔드 수동 테스트 성공
- [ ] 두 결과 일치 확인
- [ ] 관련 파일 모두 커밋 (테스트 스크립트, 테스트 데이터)
