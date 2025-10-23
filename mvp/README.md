# Vision AI Training Platform - MVP

> 자연어로 Vision 모델을 학습하는 AI 플랫폼 (MVP 버전)

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-20.x-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

## 📋 목차

- [개요](#-개요)
- [주요 기능](#-주요-기능)
- [시스템 요구사항](#-시스템-요구사항)
- [프로젝트 구조](#-프로젝트-구조)
- [Quick Start](#-quick-start)
- [상세 설치 가이드](#-상세-설치-가이드)
- [사용 방법](#-사용-방법)
- [개발 가이드](#-개발-가이드)
- [트러블슈팅](#-트러블슈팅)

## 🎯 개요

Vision AI Training Platform은 개발자가 **자연어로 대화하듯** Vision 모델을 학습할 수 있는 플랫폼입니다.

**예시:**
```
사용자: "ResNet-18로 이미지 분류 학습해줘. 데이터셋은 C:\datasets\cls\imagenet-10"
AI: 알겠습니다! 학습 설정을 진행하겠습니다...
```

## ✨ 주요 기능

### 🗣️ 자연어 기반 학습 설정
- LLM(Gemini)을 통한 자연어 이해
- 대화형 파라미터 수집
- 프로젝트 기반 실험 관리

### 🤖 다양한 모델 지원
- **timm**: ResNet-18/50, EfficientNet-B0 (Image Classification)
- **Ultralytics**: YOLOv8n/s/m (Detection, Segmentation, Pose)
- **HuggingFace Transformers**: (예정)

### 📊 실시간 모니터링
- 학습 진행률 실시간 업데이트
- MLflow 기반 실험 추적
- Grafana 대시보드
- Prometheus 메트릭 수집

### 💻 사용자 친화적 UI
- Chat 기반 인터페이스
- 프로젝트/실험 관리
- 실시간 로그 및 메트릭 확인

## 🖥️ 시스템 요구사항

### 필수 소프트웨어

| 소프트웨어 | 버전 | 용도 |
|-----------|------|------|
| **Python** | 3.11+ | Backend 및 Training |
| **Node.js** | 20.x | Frontend |
| **Docker Desktop** | 4.26+ | 인프라 서비스 |
| **Git** | 최신 | 버전 관리 |

### 하드웨어 권장사항

- **CPU**: 4 cores 이상
- **RAM**: 8GB 이상 (16GB 권장)
- **Disk**: 20GB 이상 여유 공간
- **GPU**: (선택) NVIDIA GPU with CUDA 11.8+ (학습 가속용)

### OS 지원

- ✅ Windows 10/11
- ✅ macOS 12+
- ✅ Linux (Ubuntu 20.04+)

## 📁 프로젝트 구조

```
mvp/
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── api/            # REST API 엔드포인트
│   │   ├── models/         # 데이터 모델 (Conversation State Machine)
│   │   ├── services/       # 비즈니스 로직 (ActionHandlers, ConversationManager)
│   │   ├── utils/          # 유틸리티 (LLM, Dataset Analyzer)
│   │   └── db/             # Database 모델 및 설정
│   ├── requirements.txt    # Python 의존성
│   ├── migrate_*.py        # DB 마이그레이션 스크립트
│   └── init_db.py          # DB 초기화
│
├── frontend/               # Next.js 프론트엔드
│   ├── app/               # Next.js 14 App Router
│   ├── components/        # React 컴포넌트
│   ├── lib/              # 유틸리티 함수
│   └── package.json
│
├── training/              # PyTorch 학습 스크립트
│   ├── adapters/         # 프레임워크별 Adapter (timm, ultralytics)
│   ├── train.py          # 메인 학습 스크립트
│   └── requirements.txt
│
├── docker-compose.yml     # 인프라 서비스 (루트 디렉토리)
└── README.md             # 이 파일
```

## 🚀 Quick Start

5분 안에 플랫폼을 실행할 수 있습니다!

### 1. 레포지토리 클론

```bash
git clone https://github.com/your-org/mvp-vision-ai-platform.git
cd mvp-vision-ai-platform
```

### 2. 환경 변수 설정

```bash
# Backend 환경 변수 (mvp/backend/.env)
cd mvp/backend
cp .env.example .env
```

`.env` 파일 편집:
```bash
# 필수: Google Gemini API Key
GOOGLE_API_KEY=your_gemini_api_key_here

# 데이터베이스 (Docker Compose 사용 시 기본값 유지)
DATABASE_URL=sqlite:///./app.db

# LLM 설정
LLM_MODEL=gemini-1.5-flash
LLM_TEMPERATURE=0.7

# MLflow (Docker Compose 사용)
MLFLOW_TRACKING_URI=http://localhost:5000
```

### 3. Docker 인프라 시작

```bash
# 루트 디렉토리로 이동
cd ../..

# Docker Compose로 모든 인프라 서비스 시작
docker-compose up -d

# 상태 확인
docker-compose ps
```

서비스가 시작되면:
- 📊 Grafana: http://localhost:3001 (admin/admin)
- 🔬 MLflow: http://localhost:5000
- 📈 Prometheus: http://localhost:9090
- 💾 MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

### 4. Backend 실행

```bash
cd mvp/backend

# Python 가상환경 생성 (최초 1회)
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 초기화
python init_db.py

# 데이터베이스 마이그레이션 (Phase 1+2 적용)
python migrate_add_conversation_state.py
python migrate_existing_sessions.py

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

Backend API: http://localhost:8000
API 문서: http://localhost:8000/docs

### 5. Frontend 실행

```bash
# 새 터미널 열기
cd mvp/frontend

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행
npm run dev
```

Frontend: http://localhost:3000

### 6. 첫 학습 시작! 🎉

1. http://localhost:3000 접속
2. Chat에서 대화 시작:
   ```
   ResNet-18로 이미지 분류 학습해줘
   ```
3. AI와 대화하며 설정 완료
4. 학습 시작 및 실시간 모니터링

## 📖 상세 설치 가이드

### 1단계: 환경 준비

#### Docker Desktop 설치

**Windows:**
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) 다운로드
2. 설치 후 재시작
3. WSL 2 backend 활성화 (권장)

**macOS:**
```bash
brew install --cask docker
```

**Linux (Ubuntu):**
```bash
# Docker Engine 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치
sudo apt-get install docker-compose-plugin
```

#### Python 3.11 설치

**Windows:**
```bash
# winget 사용
winget install Python.Python.3.11

# 또는 https://www.python.org/downloads/ 에서 직접 다운로드
```

**macOS:**
```bash
brew install python@3.11
```

**Linux:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

#### Node.js 20 설치

**Windows:**
```bash
winget install OpenJS.NodeJS
```

**macOS:**
```bash
brew install node@20
```

**Linux:**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2단계: 프로젝트 클론 및 설정

```bash
# 1. 레포지토리 클론
git clone https://github.com/your-org/mvp-vision-ai-platform.git
cd mvp-vision-ai-platform

# 2. Backend 환경 변수 설정
cd mvp/backend
cp .env.example .env

# .env 파일 편집 (필수: GOOGLE_API_KEY)
# Windows: notepad .env
# macOS/Linux: nano .env
```

### 3단계: Docker 서비스 시작

```bash
# 루트 디렉토리로 이동
cd ../..

# Docker Compose로 인프라 시작
docker-compose up -d

# 로그 확인 (선택사항)
docker-compose logs -f

# 모든 서비스가 healthy 될 때까지 대기 (~1분)
docker-compose ps
```

**실행되는 서비스:**
- PostgreSQL (5432) - 메인 DB
- MongoDB (27017) - Document Store
- Redis (6379) - Cache & Queue
- MinIO (9000) - Object Storage
- Temporal (7233) - Workflow Engine
- Prometheus (9090) - Metrics
- Grafana (3001) - Visualization
- MLflow (5000) - Experiment Tracking
- Mailhog (8025) - Email Testing

### 4단계: Backend 설정 및 실행

```bash
cd mvp/backend

# 1. Python 가상환경 생성
python -m venv venv

# 2. 가상환경 활성화
# Windows PowerShell:
venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

# 3. 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 4. 데이터베이스 초기화
python init_db.py

# 5. Phase 1+2 마이그레이션 적용
python migrate_add_conversation_state.py
python migrate_existing_sessions.py

# 6. 서버 실행
uvicorn app.main:app --reload --port 8000
```

**확인:**
- Backend: http://localhost:8000
- API 문서: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 5단계: Frontend 설정 및 실행

```bash
# 새 터미널 열기
cd mvp/frontend

# 1. 의존성 설치
npm install

# 2. 환경 변수 설정 (선택사항)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

# 3. 개발 서버 실행
npm run dev
```

**확인:**
- Frontend: http://localhost:3000

### 6단계: 샘플 데이터셋 준비 (선택사항)

```bash
# 샘플 ImageNet 데이터셋 생성
cd mvp/backend
python scripts/create_sample_imagenet.py

# 생성 위치: C:\datasets\cls\imagenet-10
# - 10개 클래스
- - 각 클래스당 ~100개 이미지 (총 1000개)
```

## 💡 사용 방법

### 1. Chat을 통한 학습 설정

#### 예시 1: ResNet 이미지 분류

```
사용자: ResNet-18로 이미지 분류 학습해줘

AI: ResNet 모델로 이미지 분류 작업을 진행하시겠군요.
    데이터셋 경로를 알려주세요.

사용자: C:\datasets\cls\imagenet-10

AI: 데이터셋 분석 완료:
    - 형식: ImageFolder
    - 클래스: 10개
    - 총 이미지: 1000개

    학습 하이퍼파라미터는 어떻게 하시겠어요?

사용자: 기본값으로 해줘

AI: 알겠습니다!
    - 에포크: 50
    - 배치 크기: 32
    - 학습률: 0.001

    프로젝트를 선택해주세요:
    1️⃣ 신규 프로젝트 생성
    2️⃣ 기존 프로젝트 선택
    3️⃣ 프로젝트 없이 실험만 진행

사용자: 1

AI: 신규 프로젝트 이름을 입력해주세요.

사용자: 이미지 분류 프로젝트 - ImageNet 10 클래스

AI: 프로젝트 '이미지 분류 프로젝트'가 생성되었습니다.

    학습을 시작하시겠습니까? (예/아니오)

사용자: 예

AI: 학습이 시작되었습니다! (Job ID: 1)
    우측 패널에서 진행 상황을 확인하실 수 있습니다.
```

#### 예시 2: YOLO 객체 탐지

```
사용자: YOLOv8으로 객체 탐지 학습

AI: YOLOv8 모델로 객체 탐지를 진행하시겠군요.
    어떤 YOLO 모델을 사용하시겠어요? (yolov8n, yolov8s, yolov8m)

사용자: yolov8n

AI: 데이터셋 경로를 알려주세요. (YOLO 형식: data.yaml)

사용자: C:\datasets\det\coco8

AI: 설정 완료! 학습을 시작하시겠어요?

사용자: 예
```

### 2. 실시간 모니터링

학습 시작 후:

1. **Training Panel** (우측)
   - 실시간 진행률 표시
   - Epoch/Step 정보
   - 현재 Loss/Accuracy

2. **Grafana Dashboard**
   - http://localhost:3001 접속
   - Training Metrics 대시보드 확인
   - GPU 사용률, 메모리, Loss/Accuracy 그래프

3. **MLflow Tracking**
   - http://localhost:5000 접속
   - 실험 비교
   - 메트릭 히스토리
   - 모델 아티팩트 다운로드

### 3. 프로젝트 관리

**프로젝트 생성:**
- Chat에서 "1번" 선택
- 프로젝트 이름 및 설명 입력

**프로젝트 선택:**
- Sidebar에서 프로젝트 클릭
- 해당 프로젝트의 실험 목록 확인

**실험 추적:**
- 각 학습은 하나의 실험(Experiment)
- 프로젝트 내에서 여러 실험 비교 가능
- MLflow에서 상세 메트릭 확인

## 🛠️ 개발 가이드

### Backend 개발

```bash
cd mvp/backend

# 의존성 추가
pip install package_name
pip freeze > requirements.txt

# 코드 포맷팅
black app/
isort app/

# Linting
flake8 app/

# 테스트
pytest tests/

# DB 마이그레이션 생성
python create_migration.py "migration_name"
```

### Frontend 개발

```bash
cd mvp/frontend

# 의존성 추가
npm install package_name

# 코드 포맷팅
npm run format

# Linting
npm run lint

# Type 체크
npm run type-check

# 빌드
npm run build
```

### 새로운 모델 프레임워크 추가

1. `mvp/training/adapters/`에 새 Adapter 클래스 생성:

```python
# mvp/training/adapters/your_framework_adapter.py
from .base import TrainingAdapter

class YourFrameworkAdapter(TrainingAdapter):
    def load_model(self, model_name: str, num_classes: int):
        # 모델 로드 로직
        pass

    def train_epoch(self, train_loader, optimizer, criterion):
        # 학습 로직
        pass

    # ... 기타 메소드 구현
```

2. `mvp/backend/app/utils/training_manager.py`에 등록:

```python
FRAMEWORK_ADAPTERS = {
    "timm": "TimmAdapter",
    "ultralytics": "UltralyticsAdapter",
    "your_framework": "YourFrameworkAdapter",  # 추가
}
```

3. Chat capabilities 업데이트 (`mvp/backend/app/api/chat.py`)

### 새로운 Action 추가 (Phase 1+2 Architecture)

1. `ActionType` enum에 추가:

```python
# mvp/backend/app/models/conversation.py
class ActionType(str, Enum):
    # ... 기존 액션들
    YOUR_NEW_ACTION = "your_new_action"
```

2. Action Handler 구현:

```python
# mvp/backend/app/services/action_handlers.py
async def _handle_your_new_action(
    self,
    action_response: GeminiActionResponse,
    session: SessionModel,
    user_message: str
) -> Dict[str, Any]:
    """Handle your new action"""
    # 비즈니스 로직 구현

    return {
        "new_state": ConversationState.NEXT_STATE,
        "message": "응답 메시지",
        "temp_data": updated_temp_data,
    }
```

3. Action Router에 등록:

```python
handlers = {
    # ... 기존 핸들러들
    ActionType.YOUR_NEW_ACTION: self._handle_your_new_action,
}
```

## 🐛 트러블슈팅

### Docker 관련

**문제: Docker 컨테이너가 시작되지 않음**
```bash
# 기존 컨테이너 정리
docker-compose down -v

# 이미지 재다운로드
docker-compose pull

# 재시작
docker-compose up -d
```

**문제: 포트 충돌 (이미 사용 중)**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :8000
kill -9 <PID>
```

### Backend 관련

**문제: ModuleNotFoundError**
```bash
# 가상환경이 활성화되었는지 확인
which python  # 가상환경 경로가 나와야 함

# 의존성 재설치
pip install -r requirements.txt
```

**문제: Database locked (SQLite)**
```bash
# DB 파일 삭제 후 재생성
rm app.db
python init_db.py
python migrate_add_conversation_state.py
```

**문제: Gemini API 오류 (401 Unauthorized)**
```bash
# .env 파일 확인
cat .env | grep GOOGLE_API_KEY

# API Key가 올바른지 확인
# https://makersuite.google.com/app/apikey 에서 발급
```

### Frontend 관련

**문제: npm install 실패**
```bash
# 캐시 정리
npm cache clean --force

# node_modules 삭제 후 재설치
rm -rf node_modules package-lock.json
npm install
```

**문제: API 연결 오류**
```bash
# Backend가 실행 중인지 확인
curl http://localhost:8000/health

# CORS 설정 확인 (mvp/backend/app/main.py)
```

### 학습 관련

**문제: 학습이 시작되지 않음**
```bash
# Backend 로그 확인
# 터미널에서 에러 메시지 확인

# Job 상태 확인
curl http://localhost:8000/api/v1/training/jobs/{job_id}
```

**문제: GPU를 사용하지 않음**
```bash
# CUDA 설치 확인
python -c "import torch; print(torch.cuda.is_available())"

# PyTorch GPU 버전 설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**문제: Out of Memory**
```bash
# Batch size 줄이기
# Chat에서 배치 크기를 16 또는 8로 설정

# 또는 config에서 직접 수정
```

### 일반적인 문제

**문제: 모든 것이 느림**
```bash
# Docker 리소스 확인 (Docker Desktop > Settings > Resources)
# CPU: 최소 4 cores 할당
# Memory: 최소 8GB 할당

# WSL 2 메모리 제한 (.wslconfig)
[wsl2]
memory=8GB
```

**문제: 마이그레이션 에러**
```bash
# 마이그레이션 재실행
python migrate_add_conversation_state.py
python migrate_existing_sessions.py

# 실패 시 DB 초기화
rm app.db
python init_db.py
python migrate_add_conversation_state.py
```

## 📚 추가 문서

- [Phase 1+2 Implementation](backend/PHASE1_2_IMPLEMENTATION.md) - Conversation State Machine 구현 상세
- [Conversation Architecture](../docs/CONVERSATION_STATE_ARCHITECTURE.md) - 아키텍처 설계 문서
- [Adapter Pattern](../docs/ADAPTER_DESIGN.md) - Multi-framework Adapter 설계
- [MVP Plan](../MVP_PLAN.md) - MVP 계획 및 로드맵
- [MVP Structure](../MVP_STRUCTURE.md) - 상세 폴더 구조
- [CLAUDE.md](../CLAUDE.md) - Claude Code 작업 가이드

## 🤝 기여하기

1. Fork the Project
2. Create Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit Changes (`git commit -m 'feat: add amazing feature'`)
4. Push to Branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

**Commit Convention:**
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 수정
- `refactor`: 코드 리팩토링
- `test`: 테스트 추가/수정

## 📄 라이선스

MIT License - [LICENSE](../LICENSE) 파일 참고

## 📧 문의

- GitHub Issues: [Issues](https://github.com/your-org/mvp-vision-ai-platform/issues)
- Email: flytothejy@naver.com

---

**Made with ❤️ by Vision AI Team**

**Latest Update:** Phase 1+2 (Conversation State Machine) 구현 완료 (2025-10-21)
