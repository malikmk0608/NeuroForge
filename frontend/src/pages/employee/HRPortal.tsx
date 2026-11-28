import type { EmployeeProfile } from '../../api/portal'

export default function HRPortal({ profile }: { profile: EmployeeProfile }) {
  return <section className="card app-content">
    <h2>Employment record</h2>
    <p className="app-caption">Your current directory record</p>
    <dl className="app-facts">
      <dt>Employee</dt><dd>{profile.name}</dd>
      <dt>Employee code</dt><dd>{profile.employee_code}</dd>
      <dt>Department</dt><dd>{profile.department}</dd>
      <dt>Assigned role</dt><dd>{profile.role}</dd>
    </dl>
  </section>
}
