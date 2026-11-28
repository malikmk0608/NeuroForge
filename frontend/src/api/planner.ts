export interface Employee {
  employee_code: string
  name: string
  role: string
  department: string
}
export interface Options {
  employees: Employee[]
  roles: string[]
  backend_mode: string
  model: { configured: boolean; provider: string }
}
export interface Result {
  message: string
  current_employee: Employee | null
  interpretation: {
    action: string | null
    employee_code: string | null
    target_role: string | null
    clarification_questions: string[]
  }
  extracted_details: Partial<Record<'manager' | 'effective_date' | 'justification' | 'assignment_type', string | null>>
  plan: null | {
    action: string
    current_role: string
    target_role: string | null
    ready_for_submission: boolean
    has_changes: boolean
    request_context: { request_title: string; priority: string; business_unit?: string; requester_reference?: string }
    permissions: Record<'grant' | 'revoke' | 'retain', string[]>
    clarification_questions: string[]
    risk_suggestion: { level: string; reasons: string[] }
  }
  activity_steps: { message: string }[]
}

export async function planner<T>(route: string, body?: object): Promise<T> {
  const response = await fetch('/agent/' + route, {
    method: body ? 'POST' : 'GET',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body && JSON.stringify(body),
    signal: AbortSignal.timeout(body ? 45000 : 10000),
  })
  if (!response.headers.get('content-type')?.includes('application/json'))
    throw new Error('The planner is unavailable. Check that the local service is running on port 8002.')
  const data = await response.json()
  if (!response.ok) {
    const detail = data.detail
    throw new Error(Array.isArray(detail) ? detail.map(item => item.msg).join(' ') : String(detail || 'Request failed.'))
  }
  return data
}
