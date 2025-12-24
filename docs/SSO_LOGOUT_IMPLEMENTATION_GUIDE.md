# SSO 로그아웃 구현 가이드 (Keycloak + NextAuth)

> **작성 목적**: Vision AI Platform에서 검증된 SSO 로그아웃 구현을 Labeler 프로젝트에 적용하기 위한 가이드

## 📌 왜 SSO 로그아웃이 복잡한가?

SSO 로그아웃은 **두 세션을 모두 정리**해야 합니다:
1. **NextAuth 세션** (애플리케이션 레벨)
2. **Keycloak 세션** (SSO 제공자 레벨)

단순히 NextAuth만 로그아웃하면 Keycloak 세션이 살아있어서, 재로그인 시 자동으로 로그인되는 문제가 발생합니다.

---

## 🏗️ 아키텍처 개요

### 로그아웃 플로우

```
사용자가 로그아웃 버튼 클릭
  ↓
/api/auth/logout (세션 쿠키 살아있음)
  - getToken()으로 id_token 획득 가능
  - Keycloak logout URL로 브라우저 리다이렉트
  ↓
Keycloak 세션 로그아웃
  - 브라우저 쿠키를 통한 로그아웃 (SSO 세션 삭제)
  ↓
/auth/logout-success (중간 페이지)
  - "로그아웃 중입니다..." 메시지 표시
  - signOut({ callbackUrl: '/' }) 실행
  - NextAuth 클라이언트 세션 정리
  ↓
/ (메인 페이지, 파라미터 없이)
  - window.location.replace로 이동 (히스토리 대체)
  ↓
Middleware: 세션 없음 감지 → 로그인 페이지로 리다이렉트
```

---

## 📁 파일 구조

```
app/
├── api/
│   └── auth/
│       ├── logout/
│       │   └── route.ts          # Custom logout endpoint
│       └── [...nextauth]/
│           └── route.ts           # NextAuth 설정
├── auth/
│   ├── signin/
│   │   └── page.tsx               # Custom signin page
│   └── logout-success/
│       └── page.tsx               # Logout 중간 페이지
├── middleware.ts                  # 인증 체크
└── contexts/
    └── AuthContext.tsx            # 로그아웃 함수
```

---

## 🔧 단계별 구현

### 1. Custom Logout Endpoint (`/api/auth/logout/route.ts`)

**목적**: Keycloak 브라우저 세션 로그아웃

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { getToken } from 'next-auth/jwt'

export async function GET(request: NextRequest) {
  // NEXTAUTH_URL 사용 (0.0.0.0 문제 방지)
  const baseUrl = process.env.NEXTAUTH_URL ||
                  `${request.headers.get('x-forwarded-proto') || 'http'}://${request.headers.get('x-forwarded-host') || request.headers.get('host')}`

  // 토큰 가져오기 (세션 쿠키가 아직 살아있음)
  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
  })

  // Keycloak 로그아웃 URL로 리다이렉트
  if (token?.idToken) {
    const keycloakIssuer = process.env.KEYCLOAK_ISSUER
    const logoutUrl = `${keycloakIssuer}/protocol/openid-connect/logout`

    // 중간 페이지로 리다이렉트 (logout 파라미터 없이)
    const redirectUri = `${baseUrl}/auth/logout-success`

    const params = new URLSearchParams({
      id_token_hint: token.idToken as string,
      post_logout_redirect_uri: redirectUri,
    })

    return NextResponse.redirect(`${logoutUrl}?${params.toString()}`)
  }

  // id_token이 없으면 바로 logout-success로 (baseUrl 사용)
  return NextResponse.redirect(new URL('/auth/logout-success', baseUrl))
}
```

**핵심 포인트**:
- ✅ `getToken()` 호출 **전**에 `baseUrl` 계산 (항상 NEXTAUTH_URL 우선)
- ✅ `id_token_hint` 필수 (Keycloak이 어떤 세션을 로그아웃할지 식별)
- ✅ `post_logout_redirect_uri`는 `/auth/logout-success` (로그아웃 파라미터 없이!)

---

### 2. Logout Success Page (`/auth/logout-success/page.tsx`)

**목적**: NextAuth 클라이언트 세션 정리 및 메인으로 리다이렉트

```typescript
'use client'

import { useEffect } from 'react'
import { signOut } from 'next-auth/react'
import { useRouter } from 'next/navigation'

export default function LogoutSuccessPage() {
  const router = useRouter()

  useEffect(() => {
    // NextAuth 클라이언트 세션 정리 (callbackUrl 명시!)
    signOut({ redirect: false, callbackUrl: '/' })
      .then(() => {
        // 메인 페이지로 이동 (히스토리에 남기지 않음)
        window.location.replace('/')
      })
      .catch((error) => {
        console.error('signOut failed:', error)
      })
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-violet-600 mx-auto"></div>
        <p className="mt-6 text-lg text-gray-700">로그아웃 중입니다...</p>
      </div>
    </div>
  )
}
```

**핵심 포인트**:
- ✅ **`callbackUrl: '/'` 필수!** - 재로그인 시 이 페이지로 리다이렉트되는 것을 방지
- ✅ `window.location.replace('/')` 사용 - 브라우저 히스토리에 이 페이지 남기지 않음
- ✅ `redirect: false` - NextAuth가 자동으로 리다이렉트하지 않도록

---

### 3. Middleware 설정 (`middleware.ts`)

**목적**: `/auth/logout-success` 페이지를 인증 체크에서 제외

```typescript
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // 공개 페이지
  if (pathname === "/") {
    return NextResponse.next()
  }

  // NextAuth 엔드포인트는 통과
  if (pathname.startsWith("/api/auth/")) {
    return NextResponse.next()
  }

  // Error 페이지와 Auth 페이지는 통과
  if (pathname.startsWith("/auth/error") ||
      pathname.startsWith("/auth/signin") ||
      pathname.startsWith("/auth/logout-success")) {  // 🔑 이거 필수!
    return NextResponse.next()
  }

  // 토큰 확인
  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
  })

  // 인증된 사용자는 통과
  if (token) {
    return NextResponse.next()
  }

  // 미인증 사용자 → 로그인 페이지로
  const nextAuthUrl = process.env.NEXTAUTH_URL || `${request.nextUrl.origin}`
  const signInUrl = new URL(`${nextAuthUrl}/api/auth/signin`)
  const originalPath = pathname + request.nextUrl.search
  signInUrl.searchParams.set("callbackUrl", originalPath)

  return NextResponse.redirect(signInUrl.toString())
}

export const config = {
  matcher: [
    // 🔑 matcher에도 추가!
    "/((?!api/auth|auth/error|auth/signin|auth/logout-success|_next/static|_next/image|favicon.ico).*)",
  ],
}
```

**핵심 포인트**:
- ✅ 코드와 matcher 패턴 **둘 다** `/auth/logout-success` 제외 필요
- ✅ 제외하지 않으면 middleware가 즉시 로그인 페이지로 리다이렉트하여 `signOut()` 실행 안됨

---

### 4. AuthContext 로그아웃 함수 (`contexts/AuthContext.tsx`)

**목적**: 사용자 상태 초기화 및 로그아웃 엔드포인트 호출

```typescript
async function logout() {
  setError(null)
  setUser(null)
  // Custom logout endpoint로 리다이렉트 (Keycloak 로그아웃)
  window.location.href = '/api/auth/logout'
}
```

**핵심 포인트**:
- ✅ `window.location.href` 사용 (전체 페이지 리다이렉트)
- ✅ `signOut()`을 여기서 호출하면 안됨! (세션 쿠키 먼저 삭제되어 id_token 못 가져옴)

---

### 5. NextAuth 설정 (`/api/auth/[...nextauth]/route.ts`)

**중요**: JWT에 `id_token` 저장 필수

```typescript
export const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  providers: [
    KeycloakProvider({
      clientId: process.env.KEYCLOAK_CLIENT_ID!,
      clientSecret: process.env.KEYCLOAK_CLIENT_SECRET || "",
      issuer: process.env.KEYCLOAK_ISSUER,
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      // 🔑 id_token 저장 필수!
      if (account) {
        token.accessToken = account.access_token
        token.refreshToken = account.refresh_token
        token.expiresAt = account.expires_at
        token.idToken = account.id_token  // 이게 있어야 Keycloak logout 가능!
      }
      return token
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string
      return session
    },
  },
  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },
  session: {
    strategy: "jwt",
    maxAge: 60 * 60,
  },
}
```

---

## ⚠️ 주의사항 (우리가 겪었던 함정들)

### 1. ❌ `signOut()`에 `callbackUrl` 없이 호출하면

```typescript
// ❌ 잘못된 예시
signOut({ redirect: false })
```

**문제**: NextAuth가 현재 페이지(`/auth/logout-success`)를 callbackUrl로 저장
**결과**: 재로그인 시 로그아웃 페이지로 리다이렉트됨 → 즉시 로그아웃됨

**해결**:
```typescript
// ✅ 올바른 예시
signOut({ redirect: false, callbackUrl: '/' })
```

---

### 2. ❌ `router.push('/')` 사용하면

```typescript
// ❌ 잘못된 예시
router.push('/')
```

**문제**: 브라우저 히스토리에 `/auth/logout-success` 남음
**결과**: 뒤로가기 시 로그아웃 페이지로 돌아가서 다시 `signOut()` 실행

**해결**:
```typescript
// ✅ 올바른 예시
window.location.replace('/')
```

---

### 3. ❌ `request.nextUrl.origin` 사용하면

```typescript
// ❌ 잘못된 예시
return NextResponse.redirect(new URL('/auth/logout-success', request.nextUrl.origin))
```

**문제**: On-premise Kubernetes 환경에서 `0.0.0.0:3000` 반환
**결과**: Keycloak "invalid redirect url" 에러

**해결**:
```typescript
// ✅ 올바른 예시
const baseUrl = process.env.NEXTAUTH_URL || fallback
return NextResponse.redirect(new URL('/auth/logout-success', baseUrl))
```

---

### 4. ❌ Middleware에서 `/auth/logout-success` 제외 안하면

**문제**: Keycloak logout 후 `/auth/logout-success`로 돌아왔을 때 middleware가 세션 체크
**결과**: 세션 없음 → 즉시 로그인 페이지로 리다이렉트 → `signOut()` 실행 안됨

**해결**: 코드 + matcher 패턴 둘 다 제외 추가

---

### 5. ❌ 로그아웃 엔드포인트에서 `signOut()` 먼저 호출하면

```typescript
// ❌ 잘못된 예시
await signOut()
const token = await getToken(...)  // null 반환!
```

**문제**: `signOut()`이 세션 쿠키를 삭제 → `getToken()`이 null 반환 → id_token 없음
**결과**: "missing parameters: id_token_hint" 에러

**해결**: `getToken()` **먼저** 호출, Keycloak logout **후** NextAuth signOut

---

## 📋 배포 전 체크리스트

### 환경 변수 설정

```bash
# Frontend
NEXTAUTH_URL=https://your-frontend-url  # 🔑 필수! (0.0.0.0 방지)
NEXTAUTH_SECRET=your-secret-key
KEYCLOAK_ISSUER=https://your-keycloak-url/realms/your-realm
KEYCLOAK_CLIENT_ID=your-client-id
KEYCLOAK_CLIENT_SECRET=your-client-secret
```

### Keycloak Client 설정

Keycloak Admin Console에서:

1. **Valid Redirect URIs**:
   ```
   https://your-frontend-url/*
   ```

2. **Valid Post Logout Redirect URIs**:
   ```
   https://your-frontend-url/auth/logout-success
   https://your-frontend-url/*
   ```

3. **Web Origins**:
   ```
   https://your-frontend-url
   ```

### 코드 체크리스트

- [ ] `/api/auth/logout/route.ts` 생성 완료
- [ ] `/auth/logout-success/page.tsx` 생성 완료
- [ ] `middleware.ts`에 `/auth/logout-success` 제외 추가 (코드 + matcher)
- [ ] `AuthContext`의 logout 함수가 `/api/auth/logout` 호출
- [ ] NextAuth JWT callback에 `id_token` 저장
- [ ] `signOut()`에 `callbackUrl: '/'` 명시
- [ ] `window.location.replace('/')` 사용 (not `router.push`)
- [ ] `baseUrl`을 함수 시작에서 계산 (모든 경로에서 일관되게 사용)

---

## 🧪 테스트 시나리오

### 1. 기본 로그아웃 테스트
1. 로그인 상태에서 로그아웃 버튼 클릭
2. "로그아웃 중입니다..." 메시지 확인
3. 메인 페이지로 이동
4. 로그인되지 않은 상태 확인

### 2. 재로그인 테스트
1. 로그아웃 완료
2. 로그인 버튼 클릭
3. Keycloak에서 ID/PW 입력
4. ✅ **메인 페이지로 리다이렉트** (로그아웃 페이지 X)
5. 로그인된 상태 확인

### 3. 뒤로가기 테스트
1. 로그아웃 완료 후 메인 페이지
2. 브라우저 뒤로가기 클릭
3. ✅ **로그아웃 페이지로 가지 않아야 함**

### 4. SSO 동시 로그아웃 테스트
1. Vision AI Platform에서 로그인
2. 다른 탭에서 Labeler 열기 (자동 로그인됨 - SSO)
3. Vision AI에서 로그아웃
4. Labeler 탭 새로고침
5. ✅ **Labeler도 로그아웃되어야 함** (SSO 세션 삭제됨)

---

## 🐛 트러블슈팅

### "invalid redirect url" 에러

**원인**: Keycloak에 redirect URI가 등록되지 않음
**해결**:
1. Keycloak Admin Console → Clients → Your Client
2. "Valid Post Logout Redirect URIs"에 추가:
   ```
   https://your-url/auth/logout-success
   ```

### "missing parameters: id_token_hint" 에러

**원인**: NextAuth JWT에 id_token이 저장되지 않음
**해결**: NextAuth `jwt` callback 확인:
```typescript
if (account) {
  token.idToken = account.id_token  // 이거 있나?
}
```

### 재로그인 시 로그아웃 페이지로 리다이렉트됨

**원인**: `signOut()`에 `callbackUrl` 명시 안함
**해결**:
```typescript
signOut({ redirect: false, callbackUrl: '/' })  // callbackUrl 추가!
```

### 로그아웃 페이지에서 무한 리다이렉트

**원인**: Middleware가 `/auth/logout-success`를 제외하지 않음
**해결**: Middleware 코드 + matcher 패턴에 모두 추가

### 0.0.0.0:3000 URL로 리다이렉트됨

**원인**: `NEXTAUTH_URL` 환경 변수 미설정
**해결**:
```bash
NEXTAUTH_URL=https://your-actual-url
```

---

## 📚 참고 자료

- [NextAuth.js Documentation](https://next-auth.js.org/)
- [Keycloak OIDC Logout Spec](https://openid.net/specs/openid-connect-rpinitiated-1_0.html)
- [Vision AI Platform SSO Implementation](https://github.com/your-repo/mvp-vision-ai-platform)

---

## 📝 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-01-XX | 1.0 | 초기 문서 작성 (Vision AI Platform 검증 완료) |

---

## ✅ Labeler 적용 체크리스트

- [ ] 이 문서를 읽고 전체 플로우 이해
- [ ] 환경 변수 설정 완료
- [ ] Keycloak Client 설정 완료
- [ ] 코드 구현 완료 (5개 파일)
- [ ] 로컬 환경에서 테스트 완료
- [ ] 개발/스테이징 환경에서 테스트 완료
- [ ] 프로덕션 배포 완료
- [ ] SSO 동시 로그아웃 테스트 완료 (Vision AI + Labeler)
