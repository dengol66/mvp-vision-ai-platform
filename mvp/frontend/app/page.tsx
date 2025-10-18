'use client'

import { useState } from 'react'
import ChatPanel from '@/components/ChatPanel'
import TrainingPanel from '@/components/TrainingPanel'

export default function Home() {
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [trainingJobId, setTrainingJobId] = useState<number | null>(null)

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
        <h1 className="text-xl font-semibold text-gray-900">
          Vision AI Training Platform
        </h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">MVP</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">
        {/* Chat Panel - Left */}
        <div className="w-1/2 border-r border-gray-200">
          <ChatPanel
            sessionId={sessionId}
            onSessionCreated={setSessionId}
            onTrainingRequested={setTrainingJobId}
          />
        </div>

        {/* Training Panel - Right */}
        <div className="w-1/2">
          <TrainingPanel trainingJobId={trainingJobId} />
        </div>
      </main>
    </div>
  )
}
