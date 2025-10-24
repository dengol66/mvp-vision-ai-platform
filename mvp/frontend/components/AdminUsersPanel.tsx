'use client'

import { useState, useEffect } from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown, Search, X } from 'lucide-react'
import { cn } from '@/lib/utils/cn'

interface User {
  id: number
  email: string
  full_name: string | null
  company: string | null
  company_custom: string | null
  division: string | null
  division_custom: string | null
  department: string | null
  phone_number: string | null
  system_role: string
  is_active: boolean
  created_at: string
  project_count: number
}

type SortField = 'email' | 'full_name' | 'company' | 'division' | 'department' | 'system_role' | 'project_count' | 'created_at'
type SortDirection = 'asc' | 'desc' | null

export default function AdminUsersPanel() {
  const [users, setUsers] = useState<User[]>([])
  const [filteredUsers, setFilteredUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)

  // Sorting state
  const [sortField, setSortField] = useState<SortField | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(null)

  // Filter state
  const [nameFilter, setNameFilter] = useState('')
  const [emailFilter, setEmailFilter] = useState('')
  const [companyFilter, setCompanyFilter] = useState('')
  const [divisionFilter, setDivisionFilter] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState('')

  useEffect(() => {
    fetchUsers()
  }, [])

  useEffect(() => {
    applyFiltersAndSort()
  }, [users, nameFilter, emailFilter, companyFilter, divisionFilter, departmentFilter, roleFilter, sortField, sortDirection])

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/users`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      } else if (response.status === 403) {
        alert('관리자 권한이 필요합니다.')
      }
    } catch (error) {
      console.error('Failed to fetch users:', error)
    } finally {
      setLoading(false)
    }
  }

  const applyFiltersAndSort = () => {
    let result = [...users]

    // Apply filters
    if (nameFilter) {
      result = result.filter(u =>
        u.full_name?.toLowerCase().includes(nameFilter.toLowerCase())
      )
    }
    if (emailFilter) {
      result = result.filter(u =>
        u.email.toLowerCase().includes(emailFilter.toLowerCase())
      )
    }
    if (companyFilter) {
      result = result.filter(u =>
        (u.company?.toLowerCase().includes(companyFilter.toLowerCase())) ||
        (u.company_custom?.toLowerCase().includes(companyFilter.toLowerCase()))
      )
    }
    if (divisionFilter) {
      result = result.filter(u =>
        (u.division?.toLowerCase().includes(divisionFilter.toLowerCase())) ||
        (u.division_custom?.toLowerCase().includes(divisionFilter.toLowerCase()))
      )
    }
    if (departmentFilter) {
      result = result.filter(u =>
        u.department?.toLowerCase().includes(departmentFilter.toLowerCase())
      )
    }
    if (roleFilter) {
      result = result.filter(u =>
        u.system_role.toLowerCase().includes(roleFilter.toLowerCase())
      )
    }

    // Apply sorting
    if (sortField && sortDirection) {
      result.sort((a, b) => {
        let aVal: any = a[sortField]
        let bVal: any = b[sortField]

        // Handle custom fields
        if (sortField === 'company') {
          aVal = a.company_custom || a.company || ''
          bVal = b.company_custom || b.company || ''
        } else if (sortField === 'division') {
          aVal = a.division_custom || a.division || ''
          bVal = b.division_custom || b.division || ''
        }

        // Handle null values
        if (aVal === null) aVal = ''
        if (bVal === null) bVal = ''

        // Compare
        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
        return 0
      })
    }

    setFilteredUsers(result)
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

  const clearFilters = () => {
    setNameFilter('')
    setEmailFilter('')
    setCompanyFilter('')
    setDivisionFilter('')
    setDepartmentFilter('')
    setRoleFilter('')
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'superadmin':
        return '최고 관리자'
      case 'admin':
        return '관리자'
      case 'guest':
        return '게스트'
      default:
        return role
    }
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'superadmin':
        return 'bg-red-100 text-red-700'
      case 'admin':
        return 'bg-violet-100 text-violet-700'
      case 'guest':
        return 'bg-gray-100 text-gray-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">로딩 중...</div>
      </div>
    )
  }

  const hasFilters = nameFilter || emailFilter || companyFilter || divisionFilter || departmentFilter || roleFilter

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h2 className="text-xl font-bold text-gray-900">사용자 관리</h2>
        <p className="text-sm text-gray-500 mt-1">
          전체 {users.length}명 | 필터링 결과 {filteredUsers.length}명
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="이름 검색..."
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
              className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="이메일 검색..."
              value={emailFilter}
              onChange={(e) => setEmailFilter(e.target.value)}
              className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="회사 검색..."
              value={companyFilter}
              onChange={(e) => setCompanyFilter(e.target.value)}
              className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="사업부 검색..."
              value={divisionFilter}
              onChange={(e) => setDivisionFilter(e.target.value)}
              className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="부서 검색..."
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="권한 검색..."
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-violet-500"
            />
          </div>
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
            >
              <X className="w-4 h-4" />
              필터 초기화
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
                  onClick={() => handleSort('full_name')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  이름
                  {getSortIcon('full_name')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('email')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  이메일
                  {getSortIcon('email')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('company')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  회사
                  {getSortIcon('company')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('division')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  사업부
                  {getSortIcon('division')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('department')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  부서
                  {getSortIcon('department')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('system_role')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  권한
                  {getSortIcon('system_role')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('project_count')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  프로젝트
                  {getSortIcon('project_count')}
                </button>
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                <button
                  onClick={() => handleSort('created_at')}
                  className="flex items-center gap-1 hover:text-violet-600"
                >
                  가입일
                  {getSortIcon('created_at')}
                </button>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                  {hasFilters
                    ? '필터 조건에 맞는 사용자가 없습니다.'
                    : '사용자가 없습니다.'}
                </td>
              </tr>
            ) : (
              filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {user.id}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {user.full_name || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {user.email}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {user.company_custom || user.company || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {user.division_custom || user.division || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {user.department || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className={cn(
                      'px-2 py-1 text-xs font-medium rounded',
                      getRoleBadgeColor(user.system_role)
                    )}>
                      {getRoleLabel(user.system_role)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 text-center">
                    {user.project_count}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {formatDate(user.created_at)}
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
