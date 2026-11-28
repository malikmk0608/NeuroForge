export interface Session { csrf: string; username?: string; role?: 'HR' | 'APPROVER' | 'EMPLOYEE' }
let csrf = ''
export async function portal<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch('/portal/' + path, { ...options, cache: 'no-store',
    headers: { 'X-CSRF-TOKEN': csrf, ...options.headers } })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    if (response.status === 401 && path !== 'login') window.dispatchEvent(new Event('session-ended'))
    const detail = data.detail
    throw new Error(Array.isArray(detail) ? detail.map(d => d.msg).join(' ') : detail ||
      (response.status === 401 ? 'Check your username and password.' :
       response.status === 403 ? 'Access denied. Refresh and sign in again.' : 'Request failed. Check that the portal services are running.'))
  }
  if (response.status === 204) return undefined as T
  return response.json()
}
export async function session() {
  const current = await portal<Session>('session')
  csrf = current.csrf
  return current
}
export interface Entry {
  request_id: number; status: string; employee_code: string; name: string; action: string
  target_role: string | null; approved_count: number; effective_date: string; requester: string
}
export interface EmployeeProfile {
  name: string
  role: string
  department: string
  employee_code: string
  permissions: string[]
  requests: Entry[]
}
export interface Detail extends Entry {
  plan: { current_role: string; justification: string; manager: string; request_context?: { request_title: string }
    proposed_permissions: Record<string,string[]> }
  events: { actor: string; event_type: string; occurred_at: string }[]
}
export function message(e: unknown) { return e instanceof Error ? e.message : 'Request failed.' }

