export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="max-w-2xl w-full text-center">
        <h1 className="text-4xl font-bold mb-4">
          Vision AI Training Platform
        </h1>
        <p className="text-muted-foreground text-lg mb-8">
          자연어로 컴퓨터 비전 모델을 학습하세요
        </p>
        <div className="flex gap-4 justify-center">
          <a
            href="/training"
            className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-8 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
          >
            학습 시작하기
          </a>
          <a
            href="/docs"
            className="inline-flex h-10 items-center justify-center rounded-md border border-input bg-background px-8 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            문서 보기
          </a>
        </div>
      </div>
    </main>
  );
}
