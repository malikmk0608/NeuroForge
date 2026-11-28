import { useState } from 'react'

const teams = [
  { name: 'Engineering', contact: 'Engineering lead', remit: 'Code reviews and project delivery' },
  { name: 'Finance', contact: 'Expense desk', remit: 'Expense reports and reimbursements' },
  { name: 'HR', contact: 'People operations', remit: 'Employee records and role changes' },
]

export default function TeamDirectory() {
  const [query, setQuery] = useState('')
  const matches = teams.filter(team => team.name.toLowerCase().includes(query.trim().toLowerCase()))
  return <section className="card app-content">
    <h2>Team contacts</h2>
    <p className="app-caption">Sample department directory</p>
    <label htmlFor="team-search">Find a department</label>
    <input id="team-search" type="search" value={query} onChange={event => setQuery(event.target.value)} />
    <ul className="app-rows">{matches.map(team => <li key={team.name}>
      <div><small>{team.name}</small><strong>{team.contact}</strong><span>{team.remit}</span></div>
    </li>)}</ul>
    {matches.length === 0 && <p>No departments match your search.</p>}
  </section>
}
