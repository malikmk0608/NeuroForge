import type { Result } from '../../api/planner'

interface PlanPreviewProps {
  result: Result | null
  status: string
  busy: boolean
  onSubmit?: () => void
}

export default function PlanPreview({ result, status, busy, onSubmit }: PlanPreviewProps) {
  const plan = result?.plan
  const context = plan?.request_context
  return <aside className="card review" aria-labelledby="plan-heading" aria-live="polite" aria-busy={busy}>
    <div className="card-heading"><h2 id="plan-heading">Access plan</h2><span className="tag">{status}</span></div>
    {plan && result ? <>
      <p className="summary">{result.current_employee?.name} · {plan.action === 'OFFBOARD' ? 'Offboarding · Revoke all current access' : plan.current_role + ' → ' + plan.target_role}</p>
      <p className="hint">{[context?.request_title, context?.priority, context?.business_unit, context?.requester_reference].filter(Boolean).join(' · ')}</p>
      {(['grant','revoke','retain'] as const).map(group => <div key={group} className={'permission-group ' + group}>
        <div className="permission-heading">{group[0].toUpperCase() + group.slice(1)} ({plan.permissions[group].length})</div>
        <div className="permission-list">{plan.permissions[group].map(p => <span className="permission" key={p}>{p}</span>)}{!plan.permissions[group].length && <span className="none">None</span>}</div>
      </div>)}
      <div className="approval-note"><strong>Suggested risk · {plan.risk_suggestion.level}</strong><ul>{plan.risk_suggestion.reasons.map(r => <li key={r}>{r}</li>)}</ul>Every change requires two approvals.</div>
      {plan.clarification_questions.length > 0 && <p className="notice">{plan.clarification_questions.join(' ')}</p>}
      <div className="approval-note">Draft · No approvals recorded</div>
      {onSubmit && <button type="button" disabled={busy || !plan.ready_for_submission} onClick={onSubmit}>Submit for approval</button>}
      <details><summary>View activity</summary><ol>{result.activity_steps.map((s,i) => <li key={i}>{s.message}</li>)}</ol></details>
    </> : <div id="empty-state"><h3>A clear view of every change</h3><p>Complete the form to preview granted, revoked, and retained permissions.</p><div className="approval-note">Two approvals are required before access can change.</div></div>}
  </aside>
}
