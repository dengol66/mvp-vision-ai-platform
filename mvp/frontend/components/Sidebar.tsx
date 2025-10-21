'use client'

import { useState, useEffect } from 'react'
import { User, FolderIcon } from 'lucide-react'
import { cn } from '@/lib/utils/cn'

interface Project {
  id: number
  name: string
  description: string | null
  task_type: string | null
  created_at: string
  updated_at: string
  experiment_count: number
}

interface SidebarProps {
  onProjectSelect?: (projectId: number) => void
  selectedProjectId?: number | null
}

export default function Sidebar({
  onProjectSelect,
  selectedProjectId,
}: SidebarProps) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)

  // Fetch recent projects
  useEffect(() => {
    fetchRecentProjects()
  }, [])

  const fetchRecentProjects = async () => {
    setLoadingProjects(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/projects`)
      if (response.ok) {
        const data = await response.json()
        // Get top 5 most recent projects (excluding "Uncategorized")
        const filtered = data
          .filter((p: Project) => p.name !== 'Uncategorized')
          .sort((a: Project, b: Project) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          )
          .slice(0, 5)
        setProjects(filtered)
      }
    } catch (error) {
      console.error('Failed to fetch projects:', error)
    } finally {
      setLoadingProjects(false)
    }
  }

  const handleProjectClick = (projectId: number) => {
    // Select the project (workspace will update automatically)
    onProjectSelect?.(projectId)
  }

  // Dummy user data
  const user = {
    name: 'John Doe',
    email: 'john.doe@example.com',
    avatar: 'JD',
  }

  return (
    <div className="w-64 h-screen bg-gray-900 text-white flex flex-col">
      {/* Project Title */}
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-xl font-bold bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
          Vision AI Platform
        </h1>
        <p className="text-xs text-gray-400 mt-1">Training Platform MVP</p>
      </div>

      {/* Recent Projects */}
      <div className="flex-1 overflow-hidden flex flex-col px-4 py-2">
        <h2 className="text-sm font-semibold text-gray-400 mb-2 px-2">프로젝트</h2>
        <div className="flex-1 overflow-y-auto space-y-1">
          {loadingProjects ? (
            <div className="text-center py-4 text-gray-500 text-sm">
              로딩 중...
            </div>
          ) : projects.length > 0 ? (
            projects.map((project) => (
              <button
                key={project.id}
                onClick={() => handleProjectClick(project.id)}
                className={cn(
                  'w-full px-3 py-2.5 rounded-lg',
                  'text-left transition-colors',
                  'flex items-start gap-2',
                  'group',
                  selectedProjectId === project.id
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-300 hover:bg-gray-800/50'
                )}
              >
                <FolderIcon className={cn(
                  'w-4 h-4 mt-0.5 flex-shrink-0',
                  selectedProjectId === project.id
                    ? 'text-violet-400'
                    : 'text-gray-500 group-hover:text-violet-400'
                )} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{project.name}</p>
                  <p className="text-xs text-gray-500">
                    실험 {project.experiment_count}개
                  </p>
                </div>
              </button>
            ))
          ) : (
            <div className="text-center py-8 text-gray-500 text-sm">
              <p>프로젝트가 없습니다</p>
              <p className="text-xs mt-1 text-gray-600">
                채팅으로 프로젝트를 만들어보세요
              </p>
            </div>
          )}
        </div>
      </div>

      {/* User Info */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-full flex items-center justify-center font-semibold">
            {user.avatar}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate">{user.name}</p>
            <p className="text-xs text-gray-400 truncate">{user.email}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
