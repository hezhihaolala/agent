import type { AgentResult, AuditLog, Person, Relationship, Source } from './types'

let csrfToken = ''

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message)
  }
}

function cookieCsrf(): string {
  const cookie = document.cookie.split('; ').find((item) => item.startsWith('guiyuan_csrf='))
  return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : ''
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = csrfToken || cookieCsrf()
    if (token) headers.set('X-CSRF-Token', token)
  }
  const response = await fetch(path, { ...init, headers, credentials: 'include' })
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new ApiError(data.detail || `请求失败（${response.status}）`, response.status)
  return data as T
}

export const api = {
  async login(username: string, password: string) {
    const result = await request<{ username: string; csrf_token: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) })
    csrfToken = result.csrf_token
    return result
  },
  async me() {
    const result = await request<{ username: string; csrf_token: string }>('/api/auth/me')
    csrfToken = result.csrf_token
    return result
  },
  async logout() {
    await request<void>('/api/auth/logout', { method: 'POST' })
    csrfToken = ''
  },
  changePassword: (currentPassword: string, newPassword: string) => request<void>('/api/auth/password', { method: 'POST', body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) }),
  people: () => request<Person[]>('/api/persons'),
  createPerson: (payload: Partial<Person>) => request<Person>('/api/persons', { method: 'POST', body: JSON.stringify(payload) }),
  updatePerson: (id: string, payload: Partial<Person>) => request<Person>(`/api/persons/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deletePerson: (id: string) => request<void>(`/api/persons/${id}`, { method: 'DELETE' }),
  relationships: () => request<Relationship[]>('/api/relationships'),
  createRelationship: (payload: Pick<Relationship, 'kind' | 'person_id' | 'relative_id'>) => request<Relationship>('/api/relationships', { method: 'POST', body: JSON.stringify({ ...payload, verification_status: 'unverified' }) }),
  deleteRelationship: (id: string) => request<void>(`/api/relationships/${id}`, { method: 'DELETE' }),
  sources: () => request<Source[]>('/api/sources'),
  auditLogs: () => request<AuditLog[]>('/api/audit-logs'),
  uploadSource: (form: FormData) => request<Source>('/api/sources', { method: 'POST', body: form }),
  linkSourceToPerson: (sourceId: string, personId: string) => request(`/api/sources/${sourceId}/links`, { method: 'POST', body: JSON.stringify({ entity_type: 'person', entity_id: personId }) }),
  queryAgent: (message: string) => request<AgentResult>('/api/agent/query', { method: 'POST', body: JSON.stringify({ message }) }),
  confirmDraft: (id: string) => request(`/api/change-drafts/${id}/confirm`, { method: 'POST' }),
  rejectDraft: (id: string) => request(`/api/change-drafts/${id}/reject`, { method: 'POST' }),
}
