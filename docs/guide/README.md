# Implementation Guides (구현 가이드)

이 디렉토리는 Vision AI Training Platform의 다양한 기능을 구현하는 방법에 대한 상세 가이드를 포함합니다.

## 📚 가이드 목록

### [신규 모델 추가 가이드](./ADD_NEW_MODEL.md)
새로운 딥러닝 모델을 플랫폼에 추가하는 전체 과정을 설명합니다.

**다루는 내용:**
- ✅ 모델 선정 및 라이브러리 호환성 검증
- ✅ 모델 레지스트리에 메타데이터 추가
- ✅ Adapter 구현 (새로운 프레임워크인 경우)
- ✅ Config Schema 정의
- ✅ 호환성 테스트 및 UI 확인
- ✅ 커밋 및 PR 생성

**대상 독자**: 백엔드 개발자, ML 엔지니어

**소요 시간**: 모델당 30-60분

---

## 가이드 작성 원칙

1. **단계별 설명**: 각 작업을 순차적으로 따라할 수 있도록 구성
2. **실제 코드 예시**: 추상적인 설명보다 구체적인 코드 제공
3. **트러블슈팅**: 자주 발생하는 문제와 해결 방법 포함
4. **검증 방법**: 각 단계마다 올바르게 수행되었는지 확인하는 방법 제시

---

## 관련 문서

### 기획 문서
- [WEEK1_P0_FINAL.md](../planning/WEEK1_P0_FINAL.md) - P0 모델 선정 및 기획
- [WEEK1_PHASED_IMPLEMENTATION.md](../planning/WEEK1_PHASED_IMPLEMENTATION.md) - 3단계 구현 계획
- [IMPLEMENTATION_PRIORITY_ANALYSIS.md](../planning/IMPLEMENTATION_PRIORITY_ANALYSIS.md) - 우선순위 분석

### 아키텍처 문서
- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) - 전체 시스템 아키텍처
- [DATABASE_SCHEMA.md](../architecture/DATABASE_SCHEMA.md) - 데이터베이스 스키마

### API 문서
- [API_SPECIFICATION.md](../api/API_SPECIFICATION.md) - REST API 명세

---

## 기여하기

새로운 구현 가이드를 추가하려면:

1. `docs/guide/` 디렉토리에 새로운 `.md` 파일 생성
2. 이 README에 가이드 링크 추가
3. 다음 템플릿 구조 사용:
   ```markdown
   # 가이드 제목

   ## 개요
   (이 가이드가 다루는 내용)

   ## 사전 요구사항
   (필요한 지식이나 설정)

   ## Step 1: ...
   ## Step 2: ...

   ## 트러블슈팅

   ## 참고 자료
   ```

---

## 피드백

가이드 개선을 위한 피드백이나 제안사항은 GitHub Issues에 등록해주세요.
