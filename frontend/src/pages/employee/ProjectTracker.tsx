import { useState } from 'react'

const issues = [
  { id: 'IAM-12', title: 'Review the role permission matrix', status: 'In progress' },
  { id: 'IAM-15', title: 'Check the employee onboarding guide', status: 'Open' },
  { id: 'IAM-18', title: 'Publish the access review checklist', status: 'Done' },
]

export default function ProjectTracker() {
  const [filter, setFilter] = useState('All statuses')
  return <section className="card app-content">
    <h2>Project issues</h2>
    <p className="app-caption">Sample project · Identity operations</p>
    <label htmlFor="issue-status">Filter by status</label>
    <select id="issue-status" value={filter} onChange={event => setFilter(event.target.value)}>
      {['All statuses', 'Open', 'In progress', 'Done'].map(status => <option key={status}>{status}</option>)}
    </select>
    <ul className="app-rows">{issues.filter(issue => filter === 'All statuses' || issue.status === filter).map(issue =>
      <li key={issue.id}><div><small>{issue.id}</small><strong>{issue.title}</strong></div><span className="tag">{issue.status}</span></li>
    )}</ul>
  </section>
}
