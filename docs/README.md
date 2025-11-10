# Documentation Index

Vision AI Training Platform 전체 문서 인덱스입니다.

---

## 문서 위치

### 📁 MVP 문서
**위치**: [mvp/docs/](../mvp/docs/)
**상태**: ✅ MVP 완료 (유지 모드)
**내용**: MVP 구현 과정, 아키텍처, 계획, 이슈 등

**주요 문서**:
- [MVP 계획](../mvp/docs/planning/MVP_PLAN.md)
- [MVP 구조](../mvp/docs/planning/MVP_STRUCTURE.md)
- [MVP 아키텍처](../mvp/docs/architecture/)
- [개발 가이드](../mvp/docs/guides/)

### 📁 Platform 문서
**위치**: [platform/docs/](../platform/docs/)
**상태**: ⏳ Platform 개발 진행 중
**내용**: Platform 아키텍처, 개발 가이드, 마이그레이션

**주요 문서**:
- [Platform 아키텍처](../platform/docs/architecture/)
- [3-Tier 개발](../platform/docs/development/3_TIER_DEVELOPMENT.md)
- [에러 핸들링](../platform/docs/architecture/ERROR_HANDLING_DESIGN.md)
- [통합 실패 처리](../platform/docs/architecture/INTEGRATION_FAILURE_HANDLING.md)
- [운영 가이드](../platform/docs/architecture/OPERATIONS_RUNBOOK.md)

### 📁 공용 문서
**위치**: `docs/` (현재 디렉토리)
- [CONVERSATION_LOG.md](CONVERSATION_LOG.md) - 프로젝트 대화 로그
- [reviews/](reviews/) - 설계 리뷰 문서
- [_archived/](_archived/) - 아카이브된 문서

---

## Quick Links

### MVP
- [MVP 계획](../mvp/docs/planning/MVP_PLAN.md)
- [MVP 구조](../mvp/docs/planning/MVP_STRUCTURE.md)
- [MVP 설계 가이드](../mvp/docs/planning/MVP_DESIGN_GUIDE.md)
- [시작하기](../mvp/docs/guides/GETTING_STARTED.md)
- [개발 워크플로우](../mvp/docs/guides/DEV_WORKFLOW.md)

### Platform
- [Platform 아키텍처](../platform/docs/architecture/)
- [Backend 설계](../platform/docs/architecture/BACKEND_DESIGN.md)
- [3-Tier 개발 가이드](../platform/docs/development/3_TIER_DEVELOPMENT.md)
- [에러 핸들링 설계](../platform/docs/architecture/ERROR_HANDLING_DESIGN.md)
- [통합 실패 처리](../platform/docs/architecture/INTEGRATION_FAILURE_HANDLING.md)
- [운영 가이드](../platform/docs/architecture/OPERATIONS_RUNBOOK.md)
- [MVP → Platform 마이그레이션](../platform/docs/migration/MVP_TO_PLATFORM.md)

### 리뷰
- [최종 설계 리뷰](reviews/FINAL_DESIGN_REVIEW_2025-01-11.md)

---

## 문서 구조 개요

```
프로젝트/
├── docs/                            # 공용 문서
│   ├── _archived/                   # 아카이브
│   ├── reviews/                     # 설계 리뷰
│   ├── CONVERSATION_LOG.md          # 대화 로그
│   └── README.md                    # 문서 인덱스 (현재 파일)
│
├── mvp/
│   └── docs/                        # MVP 전체 문서
│       ├── guides/                  # 개발 가이드
│       ├── architecture/            # MVP 아키텍처
│       ├── datasets/                # 데이터셋 설계
│       ├── llm/                     # LLM 통합
│       ├── k8s/                     # Kubernetes
│       ├── planning/                # MVP 계획
│       ├── production/              # MVP 프로덕션
│       └── README.md                # MVP 문서 인덱스
│
└── platform/
    └── docs/                        # Platform 문서
        ├── architecture/            # Platform 아키텍처
        ├── development/             # Platform 개발 가이드
        ├── migration/               # MVP → Platform 마이그레이션
        └── README.md                # Platform 문서 인덱스
```

---

## 문서 사용 가이드

### 새로운 개발자
1. MVP가 완료되었으며, 현재 Platform 개발 단계입니다
2. MVP 이해를 위해서는 [mvp/docs/](../mvp/docs/)를 참고하세요
3. Platform 개발에는 [platform/docs/](../platform/docs/)를 참고하세요

### MVP 관련 작업
- MVP 코드 수정 시: [mvp/docs/](../mvp/docs/) 참고
- MVP 아키텍처 이해: [mvp/docs/architecture/](../mvp/docs/architecture/)
- MVP 개발 가이드: [mvp/docs/guides/](../mvp/docs/guides/)

### Platform 개발
- Platform 아키텍처: [platform/docs/architecture/](../platform/docs/architecture/)
- 개발 가이드: [platform/docs/development/](../platform/docs/development/)
- 3-Tier 환경: [3_TIER_DEVELOPMENT.md](../platform/docs/development/3_TIER_DEVELOPMENT.md)

---

**Last Updated**: 2025-01-11
