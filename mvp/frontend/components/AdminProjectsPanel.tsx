'use client'

import { useState, useEffect } from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown, Search, X } from 'lucide-react'
import { cn } from '@/lib/utils/cn'

interface Project {
  id: number
  name: string
  description: string | null
  task_type: string | null
  created_at: string
  updated_at: string
  experiment_count: number
  owner_id: number | null
  owner_name: string | null
  owner_email: string | null
}

type SortField = 'name' | 'owner_name' | 'task_type' | 'experiment_count' | 'created_at'
type SortDirection = 'asc' | 'desc' | null

export default function AdminProjectsPanel() {
  const [projects, setProjects] = useState<Project[]>([])
  const [filteredProjects, setFilteredProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  // Sorting state
  const [sortField, setSortField] = useState<SortField | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(null)

  // Filter state - unified search
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    fetchProjects()
  }, [])

  useEffect(() => {
    applyFiltersAndSort()
  }, [projects, searchQuery, sortField, sortDirection])

  const fetchProjects = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/projects`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setProjects(data)
      } else if (response.status === 403) {
        alert('관리자 권한이 필요합니다.')
      }
    } catch (error) {
      console.error('Failed to fetch projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const applyFiltersAndSort = () => {
    let result = [...projects]

    // Apply unified search filter - search across all fields
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(p =>
        p.name.toLowerCase().includes(query) ||
        (p.description?.toLowerCase().includes(query)) ||
        (p.owner_name?.toLowerCase().includes(query)) ||
        (p.owner_email?.toLowerCase().includes(query)) ||
        (p.task_type?.toLowerCase().includes(query)) ||
        p.id.toString().includes(query)
      )
    }

    // Apply sorting
    if (sortField && sortDirection) {
      result.sort((a, b) => {
        let aVal: any = a[sortField]
        let bVal: any = b[sortField]

        // Handle null values
        if (aVal === null) aVal = ''
        if (bVal === null) bVal = ''

        // Compare
        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
        return 0
      })
    }

    setFilteredProjects(result)
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Cycle through: asc -> desc -> null
      if (sortDirection === 'asc') {
        setSortDirection('desc')
      } else if (sortDirection === 'desc') {
        setSortDirection(null)
        setSortField(null)
      }
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-4 h-4 text-gray-400" />
    }
    if (sortDirection === 'asc') {
      return <ArrowUp className="w-4 h-4 text-violet-400" />
    }
    return <ArrowDown className="w-4 h-4 text-violet-400" />
  }

  const clearSearch = () => {
    setSearchQuery('')
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">로딩 중...</div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h2 className="text-xl font-bold text-gray-900">프로젝트 관리</h2>
        <p className="text-sm text-gray-500 mt-1">
          전체 {projects.length}개 프로젝트 | 필터링 결과 {filteredProjects.length}개
        </p>
      </div>

      {/* Search */}
      <div className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="프로젝트명, 소유자, 작업 유형 등으로 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>
          {searchQuery && (
            <button
              onClick={clearSearch}
              className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
            >
              <X className="w-4 h-4" />
              초기화
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full">
          <thead className="bg-gray-100 sticky top-0">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('name')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  프로젝트명
                  {getSortIcon('name')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('owner_name')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  소유자
                  {getSortIcon('owner_name')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('task_type')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  작업 유형
                  {getSortIcon('task_type')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('experiment_count')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  실험 수
                  {getSortIcon('experiment_count')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('created_at')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  생성일
                  {getSortIcon('created_at')}
                </button>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredProjects.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  {searchQuery
                    ? '검색 조건에 맞는 프로젝트가 없습니다.'
                    : '프로젝트가 없습니다.'}
                </td>
              </tr>
            ) : (
              filteredProjects.map((project) => (
                <tr key={project.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {project.id}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="font-medium text-gray-900">{project.name}</div>
                    {project.description && (
                      <div className="text-gray-500 text-xs mt-0.5 truncate max-w-xs">
                        {project.description}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {project.owner_name ? (
                      <div>
                        <div className="text-gray-900">{project.owner_name}</div>
                        <div className="text-gray-500 text-xs">{project.owner_email}</div>
                      </div>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {project.task_type || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {project.experiment_count}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {formatDate(project.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
