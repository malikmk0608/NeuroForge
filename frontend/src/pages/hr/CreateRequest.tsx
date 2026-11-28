import { portal } from '../../api/portal'
import { useEffect, useRef, useState } from 'react'
import { planner, type Options, type Result } from '../../api/planner'
import PlanPreview from '../../components/hr/PlanPreview'

const initial = {
  'request-type': 'ROLE_CHANGE', employee: '', manager: '', 'target-role': '',
  'effective-date': '', 'assignment-type': '', justification: '', 'ai-description': '',
  'request-title': 'Employee access change', 'requester-reference': '', priority: 'NORMAL', 'business-unit': '',
}
type Fields = typeof initial

function nextWeekday() {
  const local = new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Kolkata', year:'numeric', month:'2-digit', day:'2-digit'}).format(new Date())
  const day = new Date(local + 'T00:00:00Z')
  do { day.setUTCDate(day.getUTCDate() + 1) } while ([0, 6].includes(day.getUTCDay()))
  return day.toISOString().slice(0, 10)
}

export default function CreateRequest({ integrated = false }: { integrated?: boolean }) {
  const key = useRef('')
  function call<T>(route: string, body?: object) {
    return integrated ? portal<T>('planner/' + route, body ? {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
    } : {}) : planner<T>(route,body)
  }
  async function submit() {
    if (busy || !result?.plan?.ready_for_submission) return
    setBusy(true)
    setError('')
    try {
      const receipt = await portal<{request_id:string}>('planner/submit',{
        method:'POST', headers:{'Content-Type':'application/json','Idempotency-Key':key.current},
        body:JSON.stringify({plan:result.plan})
      })
      location.hash='request/'+receipt.request_id
    } catch(e) { setError(e instanceof Error ? e.message : 'Submission failed.') }
    finally { setBusy(false) }
  }
  const [fields, setFields] = useState(initial)
  const [options, setOptions] = useState<Options | null>(null)
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('Awaiting details')
  const revision = useRef(0)
  const manual = useRef(new Set<keyof Fields>())
  const employees = options?.employees ?? []
  const roles = options?.roles ?? []
  const employee = employees.find(person => person.employee_code === fields.employee)
  const offboard = fields['request-type'] === 'OFFBOARD'
  const configured = options?.model?.configured
  const provider = options?.model?.provider === 'groq' ? 'Groq' : 'OpenAI'

  useEffect(() => {
    let active = true
    call<Options>('form-options').then(data => {
      if (!active) return
      if (integrated && data.backend_mode !== 'http') throw new Error('Start the portal planner in HTTP mode to use MySQL employees.')
      setOptions(data)
      const example = data.employees.find(e => e.employee_code === 'EF-1001')
      if (data.backend_mode === 'mock' && example && revision.current === 0) {
        setFields({...initial, employee: example.employee_code, manager: 'EF-1002', 'target-role': 'MANAGER',
          'effective-date': nextWeekday(), 'assignment-type': 'PERMANENT', 'request-title': example.name + ' - role change to MANAGER',
          'business-unit': example.department, 'requester-reference': 'Rohan Mehta - HR Operations (demo)',
          justification: 'Taking responsibility for the engineering team and its delivery reporting.'})
      }
    }).catch((failure: unknown) => {
      if (active) setError(failure instanceof Error ? failure.message : 'Unable to load employee data.')
    })
    return () => { active = false }
  }, [])

  function suggestions(next: Fields) {
    const person = employees.find(e => e.employee_code === next.employee)
    const action = next['request-type'] === 'OFFBOARD' ? 'offboarding' : 'role change to ' + (next['target-role'] || 'a new role')
    if (!manual.current.has('request-title')) next['request-title'] = person ? person.name + ' - ' + action : 'Employee access change'
    if (!manual.current.has('business-unit')) next['business-unit'] = person?.department ?? ''
    if (next.manager === next.employee) next.manager = ''
    return next
  }

  function edit(key: keyof Fields, value: string) {
    revision.current++
    manual.current.add(key)
    setFields(suggestions({...fields, [key]: value}))
    setResult(null)
    setError('')
    setFeedback('')
    setStatus('Awaiting details')
  }

  async function run(ai: boolean) {
    if (busy) return
    const message = fields['ai-description'].trim()
    if (ai && !message) { setFeedback('Enter a request description first.'); return }
    if (!ai && !fields.justification.trim()) { setError('Please enter a business justification.'); return }
    const version = revision.current
    setBusy(true)
    setResult(null)
    setFeedback('')
    setError('')
    setStatus(ai ? 'Interpreting' : 'Generating')
    const request_context = {request_title: fields['request-title'].trim(), priority: fields.priority,
      business_unit: fields['business-unit'].trim() || null, requester_reference: fields['requester-reference'].trim() || null}
    try {
      const body = ai ? { message, use_model: true, request_context } : {
        employee_code: fields.employee, request_context,
        target_role: offboard ? undefined : fields['target-role'],
        details: {manager: fields.manager, effective_date: fields['effective-date'], justification: fields.justification.trim(),
          assignment_type: offboard ? undefined : fields['assignment-type']},
      }
      const data = await call<Result>(ai ? 'plan' : offboard ? 'offboard' : 'role-change', body)
      if (version !== revision.current) return
      const questions = [...data.interpretation.clarification_questions, ...(data.plan?.clarification_questions ?? [])]
      if (ai) {
        const intent = data.interpretation
        const details = data.extracted_details
        setFields(suggestions({...fields, employee: intent.employee_code || '', 'target-role': intent.target_role || '',
          'request-type': intent.action === 'OFFBOARD' ? 'OFFBOARD' : 'ROLE_CHANGE', manager: details.manager || '',
          'effective-date': details.effective_date || '', justification: details.justification || '', 'assignment-type': details.assignment_type || ''}))
        setFeedback(questions.length ? questions.join(' ') : 'Review the extracted fields, then generate your access plan.')
      }
      if (!data.plan && (!ai || !questions.length)) throw new Error([data.message, ...questions].join(' '))
      key.current = crypto.randomUUID()
      setResult(data)
      setStatus(data.plan ? data.plan.has_changes ? 'Draft' : 'No changes' : 'Needs clarification')
    } catch (failure) {
      if (version === revision.current) {
        setError(failure instanceof Error ? failure.message : 'Unable to reach the planner.')
        setStatus('Needs attention')
      }
    } finally { setBusy(false) }
  }
  return <>
{!integrated && <header><a className="brand" href="/">N<span>NeuroForge</span></a><span className="environment">Access Management</span></header>}
  <main>
    {integrated && <p><a href="#">Back to requests</a></p>}<div className="intro"><p className="eyebrow">IDENTITY & ACCESS MANAGEMENT</p><h1>Request an access change</h1><p>Prepare employee access requests for review and approval.</p></div>
    <div className="layout">
      <section className="card" aria-labelledby="form-title">
        <details className="ai-assistant">
          <summary><strong>Describe the request</strong> <span id="model-status" className="tag">{configured ? provider + ' configured' : 'AI unavailable'}</span></summary>
          <p className="hint">Optional: let AI fill the form, then review and complete the details below.</p>
          <label htmlFor="ai-description">Request description</label>
          <textarea id="ai-description" rows={3} maxLength={4000} placeholder="For example: Give EF-1001 the MANAGER role." value={fields["ai-description"]} onChange={e => edit("ai-description", e.target.value)}></textarea>
          <p id="provider-disclosure" className="hint">{configured ? 'Your description will be sent to ' + provider + ' when you choose AI prefill.' : 'You can complete the form manually.'}</p>
          <button id="interpret-description" type="button" disabled={busy || !configured || !employees.length} onClick={() => void run(true)}>Use AI to fill form</button>
          <p id="ai-feedback" className="notice" role="status" hidden={!feedback}>{feedback}</p>
        </details>
        <div className="card-heading"><h2 id="form-title">Request details</h2><span id="request-tag" className="tag">{offboard ? 'Offboarding' : 'Role change'}</span></div>
        <form id="request-form" onSubmit={event => { event.preventDefault(); void run(false) }}>
          <label htmlFor="request-title">Request title <span>*</span></label>
          <input id="request-title" maxLength={160} required value={fields["request-title"]} onChange={e => edit("request-title", e.target.value)} />
          <label htmlFor="requester-reference">Requester reference (optional)</label>
          <input id="requester-reference" maxLength={160} placeholder="Requester name or team" value={fields["requester-reference"]} onChange={e => edit("requester-reference", e.target.value)} />
          <div className="field-grid">
            <div><label htmlFor="priority">Priority</label><select id="priority" value={fields["priority"]} onChange={e => edit("priority", e.target.value)}><option value="LOW">Low</option><option value="NORMAL">Normal</option><option value="HIGH">High</option></select></div>
            <div><label htmlFor="business-unit">Business unit / team</label><input id="business-unit" maxLength={120} placeholder="For example, Engineering" value={fields["business-unit"]} onChange={e => edit("business-unit", e.target.value)} /></div>
          </div>
          <p className="hint">Priority indicates urgency. The access plan assesses risk separately.</p>
          <label htmlFor="request-type">Request type <span>*</span></label>
          <select id="request-type" value={fields["request-type"]} onChange={e => edit("request-type", e.target.value)}><option value="ROLE_CHANGE">Role change</option><option value="OFFBOARD">Offboarding</option></select>
          <label htmlFor="employee">Employee <span>*</span></label>
          <select id="employee" required value={fields["employee"]} onChange={e => edit("employee", e.target.value)}><option value="">Loading employees…</option>{employees.map(e => <option key={e.employee_code} value={e.employee_code}>{e.name} · {e.employee_code}</option>)}</select>
          <p id="employee-context" className="hint">{employee ? 'Current employee record for ' + employee.name : 'Select an employee to see their current role.'}</p>
          <div className="field-grid employee-facts">
            <div><label htmlFor="current-role">Current role</label><input id="current-role" value={employee?.role || ''} readOnly placeholder="Populated from employee record" /></div>
            <div><label htmlFor="current-department">Current department</label><input id="current-department" value={employee?.department || ''} readOnly placeholder="Populated from employee record" /></div>
          </div>
          <div className="field-grid">
            <div id="target-role-field" hidden={offboard}><label htmlFor="target-role">Target role <span>*</span></label><select id="target-role" required={!offboard} value={fields["target-role"]} onChange={e => edit("target-role", e.target.value)}><option value="">Select a role</option>{roles.map(role => <option key={role}>{role}</option>)}</select></div>
            <div><label htmlFor="effective-date">Effective date <span>*</span></label><input id="effective-date" type="date" required value={fields["effective-date"]} onChange={e => edit("effective-date", e.target.value)} /></div>
          </div>
          <label htmlFor="manager">Reporting manager <span>*</span></label>
          <select id="manager" required value={fields["manager"]} onChange={e => edit("manager", e.target.value)}><option value="">Select a manager</option>{employees.filter(e => e.employee_code !== fields.employee && (!integrated || e.role === 'MANAGER')).map(e => <option key={e.employee_code} value={e.employee_code}>{e.name} · {e.employee_code}</option>)}</select>
          <p className="hint">Choose the employee’s reporting manager. This does not select the two approvers.</p>
          <div id="assignment-field" hidden={offboard}><label htmlFor="assignment-type">Assignment type <span>*</span></label>
          <select id="assignment-type" required={!offboard} value={fields["assignment-type"]} onChange={e => edit("assignment-type", e.target.value)}><option value="">Select assignment type</option><option value="PERMANENT">Permanent</option><option value="TEMPORARY">Temporary</option></select>
          <p id="temporary-note" className="notice" hidden={offboard || fields["assignment-type"] !== "TEMPORARY"}>Temporary assignment is recorded as a request detail. Automatic expiry is not available in this prototype.</p></div>
          <p id="offboard-note" className="notice" hidden={!offboard}>Offboarding proposes revoking all current access. Two approvals are required before any change can be applied.</p>
          <label htmlFor="justification">Business justification <span>*</span></label>
          <textarea id="justification" rows={4} required maxLength={1000} placeholder="Explain why this change is needed and what responsibilities are changing." value={fields["justification"]} onChange={e => edit("justification", e.target.value)}></textarea>
          <div className="form-footer"><span>Fields marked * are required.</span><button id="generate" type="submit" disabled={busy || !employees.length}>Generate access plan</button></div>
        </form>
        <p id="error" className="error" role="alert" hidden={!error}>{error}</p>
      </section>
      <PlanPreview result={result} status={status} busy={busy} onSubmit={integrated ? submit : undefined} />
    </div>
    <footer>NeuroForge <span>Identity &amp; Access Management · {integrated ? <a href="#">Request history</a> : <a href="/docs">API documentation</a>}</span></footer>
  </main>
  </>
}
