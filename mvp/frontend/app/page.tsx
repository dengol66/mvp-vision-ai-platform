'use client'

import { useState, useRef, useEffect } from 'react'
import Sidebar from '@/components/Sidebar'
import ChatPanel from '@/components/ChatPanel'
import TrainingPanel from '@/components/TrainingPanel'
import ProjectDetail from '@/components/ProjectDetail'

export default function Home() {
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [trainingJobId, setTrainingJobId] = useState<number | null>(null)
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [centerWidth, setCenterWidth] = useState(35) // Chat panel width (35%)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return

      const containerRect = containerRef.current.getBoundingClientRect()
      const newCenterWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100

      // Clamp between 25% (min) and 50% (max) for chat panel
      const clampedWidth = Math.max(25, Math.min(50, newCenterWidth))
      setCenterWidth(clampedWidth)
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging])

  const handleProjectSelect = (projectId: number) => {
    setSelectedProjectId(projectId)
  }

  return (
    <div className="h-screen flex">
      {/* Sidebar - Fixed Left */}
      <Sidebar
        onProjectSelect={handleProjectSelect}
        selectedProjectId={selectedProjectId}
      />

      {/* Main Content Area - 3 Column Layout */}
      <main ref={containerRef} className="flex-1 flex overflow-hidden relative">
        {/* Chat Panel - Center (Resizable) */}
        <div
          style={{ width: `${centerWidth}%` }}
          className="border-r border-gray-200"
        >
          <ChatPanel
            sessionId={sessionId}
            onSessionCreated={setSessionId}
            onTrainingRequested={setTrainingJobId}
          />
        </div>

        {/* Resizer */}
        <div
          onMouseDown={handleMouseDown}
          className={`w-1 bg-gray-200 hover:bg-violet-400 cursor-col-resize transition-colors relative group ${
            isDragging ? 'bg-violet-500' : ''
          }`}
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>

        {/* Workspace Panel - Right (Dynamic Content) */}
        <div style={{ width: `${100 - centerWidth}%` }} className="flex-1">
          {selectedProjectId ? (
            // Show project detail when project is selected
            <ProjectDetail
              projectId={selectedProjectId}
              onBack={() => setSelectedProjectId(null)}
            />
          ) : trainingJobId ? (
            // Show training panel when training job exists
            <TrainingPanel trainingJobId={trainingJobId} />
          ) : (
            // Default empty state
            <div className="h-full flex items-center justify-center bg-gray-50">
              <div className="text-center text-gray-500">
                <p className="text-sm">작업 공간</p>
                <p className="text-xs mt-1 text-gray-400">
                  프로젝트를 선택하거나 학습을 시작하세요
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
