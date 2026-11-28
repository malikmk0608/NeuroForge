import { useEffect, useRef } from 'react'
import type { EmployeeProfile } from '../../api/portal'
import CodeRepository from '../../pages/employee/CodeRepository'
import ProjectTracker from '../../pages/employee/ProjectTracker'
import TeamDirectory from '../../pages/employee/TeamDirectory'
import HRPortal from '../../pages/employee/HRPortal'
import FinanceExpense from '../../pages/employee/FinanceExpense'

export const applications = [
  { slug: 'code-repository', name: 'Code Repository', permission: 'GIT_READ', View: CodeRepository },
  { slug: 'project-tracker', name: 'Project Tracker', permission: 'JIRA_EDIT', View: ProjectTracker },
  { slug: 'team-directory', name: 'Team Directory', permission: 'TEAM_DIRECTORY', View: TeamDirectory },
  { slug: 'hr-portal', name: 'HR Portal', permission: 'HRIS_READ', View: HRPortal },
  { slug: 'finance-expense', name: 'Finance & Expense', permission: 'ERP_READ', View: FinanceExpense },
]
type Application = (typeof applications)[number]

function AccessStatus({ granted }: { granted: boolean }) {
  return <strong className={'access-status ' + (granted ? 'granted' : 'denied')}>
    {granted ? 'Access granted' : 'Access denied'}
  </strong>
}

export function DemoAppCard({ app, profile }: { app: Application; profile: EmployeeProfile }) {
  return <a className="app-link" href={'#apps/' + app.slug}>
    <h3>{app.name} <span aria-hidden="true">→</span></h3>
    <p>Requires <code>{app.permission}</code></p>
    <AccessStatus granted={profile.permissions.includes(app.permission)} />
  </a>
}

export function ApplicationScreen({ app, profile }: { app: Application; profile: EmployeeProfile }) {
  const granted = profile.permissions.includes(app.permission)
  const View = app.View
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    const previousTitle = document.title
    document.title = app.name + ' · NeuroForge'
    heading.current?.focus()
    return () => { document.title = previousTitle }
  }, [app.name])
  return <main className="employee-app">
    <a className="back-link" href="#">← My access</a>
    <h1 ref={heading} tabIndex={-1}>{app.name}</h1>
    <p className="employee-identity">{profile.name} · {profile.employee_code} · {profile.role}</p>
    <section className="card app-permissions" aria-label="Application access">
      <div role="status"><AccessStatus granted={granted} /></div>
      <dl className="app-facts">
        <dt>Required permission</dt><dd><code>{app.permission}</code></dd>
        <dt>Current permissions</dt>
        <dd className="permission-list">{profile.permissions.length ? profile.permissions.map(permission =>
          <code key={permission} className={'permission' + (permission === app.permission ? ' matched' : '')}>{permission}</code>
        ) : 'None assigned'}</dd>
      </dl>
    </section>
    {granted && <View profile={profile} />}
  </main>
}
