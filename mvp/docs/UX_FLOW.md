# UX Flow Design - UI vs Chat 통합

프로젝트 생성부터 학습 완료까지의 전체 플로우를 **UI 조작 방식**과 **Chat 방식**으로 정리하고, 공통 Frontend UX를 설계합니다.

## 핵심 원칙

1. **동일한 결과**: UI든 Chat이든 최종 결과는 동일해야 함
2. **일관된 피드백**: 두 방식 모두 같은 UI 패널로 피드백 제공
3. **상태 동기화**: 어떤 방식으로든 상태 변경 시 모든 UI가 즉시 반영
4. **선택의 자유**: 사용자가 중간에 방식을 바꿔도 자연스럽게 연결

---

## 전체 플로우 맵

```
1. 프로젝트 생성 (선택적)
   ↓
2. 학습 설정 (모델, 데이터셋, 하이퍼파라미터)
   ↓
3. 학습 시작
   ↓
4. 학습 진행 (실시간 모니터링)
   ↓
5. 학습 완료 (결과 확인)
   ↓
6. 추가 작업 (재학습, 비교, 내보내기 등)
```

---

## 1. 프로젝트 생성

### UI 방식

**트리거**: 사이드바 "새 프로젝트" 버튼 클릭

**플로우**:
```
[사이드바] 새 프로젝트 버튼 클릭
   ↓
[다이얼로그] 프로젝트 정보 입력 폼 표시
   - 프로젝트 이름 (필수)
   - 설명 (선택)
   - 작업 유형 (선택: image_classification, object_detection, etc.)
   ↓
[API] POST /api/v1/projects
   ↓
[UI 업데이트]
   - 다이얼로그 닫기
   - 사이드바 프로젝트 목록 갱신
   - 우측 패널: 새 프로젝트 상세 화면 표시 (실험 0개)
   - Toast: "프로젝트가 생성되었습니다"
```

**필요한 컴포넌트**:
- `CreateProjectDialog.tsx` (신규)
- `Sidebar.tsx` (버튼 추가)
- `ProjectDetail.tsx` (기존)

### Chat 방식

**트리거**: 채팅에서 "신규 프로젝트 생성" 선택 또는 자연어로 요청

**플로우**:
```
[Chat] "신규 프로젝트를 만들고 싶어요"
   ↓
[LLM] ASK_CLARIFICATION - "프로젝트 이름을 입력해주세요"
   ↓
[Chat] "이미지 분류 프로젝트 - ResNet 실험용"
   ↓
[LLM] (선택적) "작업 유형을 선택하시겠어요? (기본: image_classification)"
   ↓
[Chat] "기본값으로 할게요" or "image_classification"
   ↓
[LLM] CREATE_PROJECT 액션
   ↓
[Backend] action_handlers.py - _handle_create_project()
   - POST /api/v1/projects
   - Return: project_id
   ↓
[Response]
   - message: "프로젝트 '이미지 분류 프로젝트'가 생성되었습니다"
   - created_project_id: 5
   ↓
[Frontend]
   - ChatPanel: 응답 메시지 표시
   - 우측 패널: ProjectDetail(projectId=5) 자동 표시
   - 사이드바: 프로젝트 목록 갱신
```

**필요한 백엔드 변경**:
- `ActionType.CREATE_PROJECT` 추가
- `action_handlers.py`: `_handle_create_project()` 구현
- `conversation_manager.py`: `created_project_id` 응답에 포함

**필요한 프론트엔드 변경**:
- `ChatPanel.tsx`: `created_project_id` 처리
- `page.tsx`: 프로젝트 생성 시 우측 패널 전환

### 공통점

- 백엔드 API: `POST /api/v1/projects`
- 결과 화면: 우측 패널에 `ProjectDetail` 표시
- 사이드바 프로젝트 목록 자동 갱신

### 차이점

| 항목 | UI 방식 | Chat 방식 |
|------|---------|-----------|
| 입력 방식 | 다이얼로그 폼 (한 번에 입력) | 대화형 질문/답변 (순차적) |
| 피드백 | Toast 메시지 | 채팅 메시지 |
| 취소 | 다이얼로그 닫기 | 대화 재시작 필요 |
| 검증 | 폼 검증 (즉시) | LLM 검증 (자연어) |

---

## 2. 학습 설정 (모델, 데이터셋, 하이퍼파라미터)

### UI 방식

**트리거**:
- 옵션 A: 사이드바 "새 실험 시작" 버튼
- 옵션 B: 프로젝트 상세 화면에서 "실험 추가" 버튼
- 옵션 C: 우측 패널 빈 상태에서 "학습 시작" 버튼

**플로우**:
```
[트리거] 버튼 클릭
   ↓
[우측 패널] TrainingConfigPanel 표시
   ↓
[폼 입력] 사용자가 설정값 입력
   - 프레임워크: timm (기본값, 변경 가능)
   - 모델: resnet18, resnet50, efficientnet_b0 (드롭다운)
   - 데이터셋 경로: 텍스트 입력 또는 파일 탐색기
   - Epochs: 숫자 입력 (기본값 50, min=1, max=1000)
   - Batch Size: 숫자 입력 (기본값 32, 옵션: 16, 32, 64, 128)
   - Learning Rate: 숫자 입력 (기본값 0.001)
   - (선택) 프로젝트 선택: 드롭다운 (기존 프로젝트 + "없음")
   - (선택) 실험 이름: 텍스트 입력
   - (선택) 태그: 태그 입력
   ↓
[검증] 클라이언트 측 검증
   - 필수 필드 체크
   - 데이터셋 경로 존재 확인 (선택적)
   - 숫자 범위 검증
   ↓
[버튼] "학습 시작" 클릭
   ↓
[API] POST /api/v1/training/jobs
   {
     "config": { ... },
     "project_id": 5,
     "experiment_name": "ResNet18 baseline",
     "tags": ["baseline", "resnet"]
   }
   ↓
[UI 업데이트]
   - 우측 패널: TrainingPanel(jobId) 표시
   - 프로젝트가 있으면: 프로젝트 실험 카운트 +1
   - Toast: "학습이 시작되었습니다"
```

**필요한 컴포넌트**:
- `TrainingConfigPanel.tsx` (신규) - 학습 설정 폼
- `ModelSelect.tsx` (신규) - 모델 선택 드롭다운
- `DatasetPathInput.tsx` (신규) - 경로 입력 + 파일 탐색기

### Chat 방식 (현재 구현됨)

**트리거**: 채팅에서 자연어로 학습 요청

**플로우**:
```
[Chat] "ResNet18로 학습하고 싶어"
   ↓
[LLM] ASK_CLARIFICATION - "데이터셋 경로를 알려주세요"
   ↓
[Chat] "C:\datasets\cls\imagenet-10"
   ↓
[LLM] ASK_CLARIFICATION - "Epochs, batch size, learning rate를 알려주세요"
   ↓
[Chat] "기본값으로 해줘"
   ↓
[LLM] SHOW_PROJECT_OPTIONS - "프로젝트를 선택해주세요"
   ↓
[Chat] "2" (기존 프로젝트 선택)
   ↓
[LLM] SHOW_PROJECT_LIST - 프로젝트 목록 표시
   ↓
[Chat] "2" (2번 프로젝트)
   ↓
[LLM] SELECT_PROJECT
   ↓
[Backend]
   - config가 완성되었으므로 parsed_intent.status = 'complete'
   - metadata에 project_id 포함
   ↓
[Frontend] ChatPanel.tsx
   - POST /api/v1/training/jobs
   - onTrainingRequested(jobId) 호출
   ↓
[UI 업데이트]
   - 우측 패널: TrainingPanel(jobId) 표시
   - 프로젝트가 선택되었으면: ProjectDetail도 갱신
```

### 공통점

- 백엔드 API: `POST /api/v1/training/jobs`
- 결과 화면: 우측 패널에 `TrainingPanel` 표시
- 데이터 구조: 동일한 `config` + `metadata` 형식

### 차이점

| 항목 | UI 방식 | Chat 방식 |
|------|---------|-----------|
| 입력 방식 | 전체 폼 한 번에 표시 | 순차적 질문/답변 |
| 기본값 | 폼 필드에 미리 표시 | "기본값으로" 요청 필요 |
| 검증 | 실시간 폼 검증 | LLM이 자연어로 검증 |
| 진행 상황 | 폼 완성도로 확인 | 대화 흐름으로 확인 |
| 수정 | 필드 클릭해서 즉시 수정 | 이전 단계로 돌아가기 어려움 |

### 설계 고민: UI 방식의 위치

**옵션 1**: 별도의 "학습 설정" 페이지
- 장점: 모든 옵션을 한눈에 볼 수 있음
- 단점: 페이지 전환 필요, Chat과 일관성 부족

**옵션 2**: 우측 패널에 `TrainingConfigPanel` 표시
- 장점: Chat과 같은 공간에서 진행, 일관성 유지
- 단점: 패널 전환 필요

**옵션 3**: 다이얼로그 모달
- 장점: 어디서든 시작 가능, 집중도 높음
- 단점: 화면 가림, Chat과 다른 UX

**추천: 옵션 2 + 단계별 폼**
- 우측 패널에 표시하되, Chat처럼 단계별로 입력
- Step 1: 프레임워크 + 모델 선택
- Step 2: 데이터셋 경로
- Step 3: 하이퍼파라미터
- Step 4: 프로젝트 연결 (선택)
- Step 5: 최종 확인 및 시작

이렇게 하면 Chat과 유사한 단계적 경험을 제공하면서도 UI의 즉시성을 유지할 수 있습니다.

---

## 3. 학습 시작

### 공통 플로우 (UI/Chat 동일)

```
[API] POST /api/v1/training/jobs
   ↓
[Backend] training_manager.py
   - TrainingJob 생성 (status: pending)
   - 데이터셋 경로 검증
   - num_classes 자동 탐지 (ImageFolder)
   - MLflow experiment 연결 또는 생성
   ↓
[Backend] start_training()
   - Python 프로세스 생성
   - job.status = 'running'
   - job.pid 저장
   ↓
[Response] { "id": 65, "status": "running", ... }
   ↓
[Frontend]
   - setTrainingJobId(65)
   - 우측 패널: TrainingPanel(65) 표시
```

### UI 업데이트 (공통)

**우측 패널**: `TrainingPanel`
- 학습 상태 헤더 (running, 진행률)
- 실시간 메트릭 차트 (Loss, Accuracy)
- 로그 콘솔 (stdout)
- 제어 버튼 (일시정지, 중지)

**프로젝트 목록** (프로젝트가 있는 경우):
- 실험 카운트 +1
- 새 실험 카드 추가 (status: running)

---

## 4. 학습 진행 (실시간 모니터링)

### 공통 플로우 (UI/Chat 동일)

```
[Frontend] TrainingPanel
   - useEffect: 폴링 시작 (GET /api/v1/training/jobs/{id})
   - 2초마다 상태 갱신
   ↓
[Backend]
   - job.status, job.current_epoch, job.progress
   - MLflow에서 최신 메트릭 조회
   ↓
[Frontend] UI 업데이트
   - 진행률 바
   - 메트릭 차트
   - 로그 스트림
   - 남은 시간 예측
```

### 실시간 기능

1. **메트릭 차트**:
   - Loss 그래프 (Epoch별)
   - Accuracy 그래프 (Epoch별)
   - 자동 스케일링

2. **로그 콘솔**:
   - 자동 스크롤
   - 색상 코딩 (ERROR: 빨강, WARNING: 노랑)
   - 필터 (전체/에러만)

3. **제어**:
   - 일시정지 (미구현)
   - 중지 버튼 (POST /api/v1/training/jobs/{id}/stop)

---

## 5. 학습 완료

### 공통 플로우

```
[Backend] Training 프로세스 종료
   - job.status = 'completed'
   - job.completed_at 기록
   - job.final_accuracy 저장
   ↓
[Frontend] 폴링으로 감지
   - TrainingPanel 상태 업데이트
   - 완료 메시지 표시
   - "결과 보기" 버튼 활성화
```

### UI 업데이트

**TrainingPanel**:
- 헤더: "학습 완료" (초록색)
- 최종 메트릭 요약
- 버튼:
  - "MLflow에서 보기" → MLflow UI 새 탭
  - "모델 다운로드" → .pth 파일 다운로드
  - "재학습" → 같은 설정으로 다시 시작
  - "비교하기" → 다른 실험과 비교

**프로젝트 상세**:
- 실험 카드 상태: completed (초록색)
- 최종 정확도 표시
- 클릭 시 TrainingPanel로 전환

---

## 6. 추가 작업

### 재학습

**UI 방식**:
```
[TrainingPanel] "재학습" 버튼 클릭
   ↓
[다이얼로그] 설정 수정 폼
   - 기존 설정 미리 채워짐
   - 원하는 값 수정
   ↓
[API] POST /api/v1/training/jobs
   ↓
새 학습 시작 (플로우 3번으로)
```

**Chat 방식**:
```
[Chat] "방금 학습한 것과 같은 설정으로 epochs만 100으로 늘려서 다시 학습해줘"
   ↓
[LLM]
   - 이전 job 설정 로드
   - epochs: 100으로 수정
   - CREATE_TRAINING 액션
   ↓
새 학습 시작
```

### 비교하기

**UI 방식**:
```
[프로젝트 상세] 여러 실험 선택 (체크박스)
   ↓
"비교하기" 버튼 클릭
   ↓
[우측 패널] ComparisonPanel
   - 설정 비교 표
   - 메트릭 비교 차트
   - 최종 결과 비교
```

**Chat 방식**:
```
[Chat] "실험 64와 65를 비교해줘"
   ↓
[LLM] COMPARE_EXPERIMENTS 액션
   ↓
[Frontend] ComparisonPanel 표시
```

---

## 공통 백엔드 API

| Endpoint | Method | 용도 | UI/Chat |
|----------|--------|------|---------|
| `/api/v1/projects` | POST | 프로젝트 생성 | 공통 |
| `/api/v1/projects` | GET | 프로젝트 목록 | 공통 |
| `/api/v1/projects/{id}` | GET | 프로젝트 상세 | 공통 |
| `/api/v1/projects/{id}/experiments` | GET | 실험 목록 | 공통 |
| `/api/v1/training/jobs` | POST | 학습 시작 | 공통 |
| `/api/v1/training/jobs/{id}` | GET | 학습 상태 | 공통 |
| `/api/v1/training/jobs/{id}/stop` | POST | 학습 중지 | 공통 |
| `/api/v1/training/jobs/{id}/metrics` | GET | 메트릭 조회 | 공통 |
| `/api/v1/chat/message` | POST | 채팅 메시지 | Chat 전용 |
| `/api/v1/chat/capabilities` | GET | 플랫폼 정보 | Chat 전용 |

---

## 공통 Frontend 상태

### 전역 상태 (page.tsx)

```typescript
const [sessionId, setSessionId] = useState<number | null>(null)
const [trainingJobId, setTrainingJobId] = useState<number | null>(null)
const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
```

### 상태 전환 로직

```typescript
// 프로젝트 생성 (UI 또는 Chat)
onProjectCreated(projectId) {
  setSelectedProjectId(projectId)  // 우측 패널: ProjectDetail
}

// 학습 시작 (UI 또는 Chat)
onTrainingStarted(jobId) {
  setTrainingJobId(jobId)           // 우측 패널: TrainingPanel
  setSelectedProjectId(null)        // ProjectDetail 숨김
}

// 프로젝트 선택 (Sidebar 또는 Chat)
onProjectSelected(projectId) {
  setSelectedProjectId(projectId)  // 우측 패널: ProjectDetail
  setTrainingJobId(null)            // TrainingPanel 숨김
}
```

---

## 구현 우선순위

### Phase 1: 핵심 플로우 (현재 상태)
- ✅ Chat 방식 학습 설정 및 시작
- ✅ 프로젝트 선택 (Chat)
- ✅ 학습 진행 모니터링 (TrainingPanel)
- ✅ 프로젝트 상세 화면 (ProjectDetail)

### Phase 2: UI 방식 추가 (다음 단계)
- [ ] `CreateProjectDialog.tsx` - 프로젝트 생성 UI
- [ ] `TrainingConfigPanel.tsx` - 학습 설정 폼 (단계별)
- [ ] Sidebar "새 프로젝트" 버튼
- [ ] 우측 패널 상태 전환 로직 개선

### Phase 3: 고급 기능
- [ ] 재학습 기능
- [ ] 실험 비교 기능 (`ComparisonPanel.tsx`)
- [ ] 모델 다운로드
- [ ] 학습 일시정지/재개

### Phase 4: 편의성 개선
- [ ] 데이터셋 경로 파일 탐색기
- [ ] 설정 템플릿 (자주 쓰는 설정 저장)
- [ ] 학습 큐 (여러 학습 순차 실행)
- [ ] 알림 (학습 완료 시)

---

## 다음 액션 아이템

1. **UI 방식 학습 설정 구현 결정**:
   - 옵션 2 (우측 패널 단계별 폼) vs 옵션 3 (다이얼로그)
   - 어떤 방식이 더 나을까요?

2. **프로젝트 생성 UI**:
   - `CreateProjectDialog.tsx` 먼저 구현
   - Sidebar에 "새 프로젝트" 버튼 추가

3. **Chat 방식 개선**:
   - `CREATE_PROJECT` 액션 추가
   - `created_project_id` 응답 처리

어떤 부분부터 구현할까요?
