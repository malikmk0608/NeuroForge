import type { Employee } from './api/planner'
import { useEffect, useState, type FormEvent } from 'react'
import { portal, session, message, type Detail, type EmployeeProfile, type Entry, type Session } from './api/portal'
import CreateRequest from './pages/hr/CreateRequest'
import { applications, ApplicationScreen, DemoAppCard } from './components/employee/DemoAppCard'

function useLocation() {
  const [route, setRoute] = useState(location.hash.slice(1))
  useEffect(() => {
    const change = () => setRoute(location.hash.slice(1))
    window.addEventListener('hashchange', change)
    return () => window.removeEventListener('hashchange', change)
  }, [])
  return route
}

function Login({ reload }: { reload: () => Promise<void> }) {
  const [error,setError] = useState('')
  const [busy,setBusy] = useState(false)
  async function login(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fields = new FormData(e.currentTarget)
    setBusy(true); setError('')
    try {
      await portal('login', { method:'POST', body:new URLSearchParams({
        username:String(fields.get('username')).trim(), password:String(fields.get('password')) }) })
      location.hash = ''
      await reload()
    } catch(e) { setError(message(e)) } finally { setBusy(false) }
  }
  return <main className="login"><section className="card"><p className="eyebrow">NEUROFORGE</p><h1>Sign in</h1>
    <p>Use your HR, approver, or employee account.</p><form onSubmit={login}>
    <label htmlFor="username">Username</label><input id="username" name="username" autoComplete="username" required autoFocus/>
    <label htmlFor="password">Password</label><input id="password" type="password" name="password" autoComplete="current-password" required/>
    <button disabled={busy}>Sign in</button></form>{error && <p role="alert">{error}</p>}</section></main>
}

function Rows({ rows, links }: { rows:Entry[]; links:boolean }) {
  if (!rows.length) return <p>No requests yet.</p>
  return <ul className="requests">{rows.map(r => <li key={r.request_id}><div>
    {links ? <a href={'#request/'+r.request_id}>Request #{r.request_id}</a> : <strong>Request #{r.request_id}</strong>}
    <p>{r.name} · {r.target_role || 'Offboarding'}</p></div><span className="tag">{r.status.replaceAll('_',' ')} · {r.approved_count}/2</span></li>)}</ul>
}

function Queue({ hr }: {hr:boolean}) {
  const [rows,setRows] = useState<Entry[]>([])
  const [directory,setDirectory] = useState<Employee[]>([])
  const [loading,setLoading] = useState(true)
  const [error,setError] = useState('')
  useEffect(() => {
    let live = true
    async function read() { try { const [data,people] = await Promise.all([portal<Entry[]>('requests'), hr ? portal<Employee[]>('directory') : Promise.resolve([])]); if(live){setRows(data);setDirectory(people);setError('')} }
      catch(e){if(live)setError(message(e))} finally {if(live)setLoading(false)} }
    void read(); const timer = setInterval(read,7000)
    return () => {live=false; clearInterval(timer)}
  },[hr])
  return <main><div className="intro"><p className="eyebrow">{hr ? 'HR OPERATIONS':'APPROVER WORKSPACE'}</p>
    <h1>{hr ? 'Access requests':'Approval queue'}</h1></div>
    {hr && <p><a className="action" href="#create">Create access request</a></p>}
    <section className="card"><h2>{hr ? 'Request history':'Requests for review'}</h2>
    {error && <p role="alert">{error}</p>}{loading ? <p>Loading requests…</p> : <Rows rows={hr ? rows : rows.filter(r=>r.status==='PENDING_APPROVAL')} links/>}</section>
    {!hr && rows.some(r=>r.status!=='PENDING_APPROVAL') && <section className="card"><h2>Decision history</h2><Rows rows={rows.filter(r=>r.status!=='PENDING_APPROVAL')} links/></section>}
    {hr && <section className="card"><h2>Employee directory</h2><ul className="requests">{directory.map(e=><li key={e.employee_code}>
      <div><strong>{e.name}</strong><p>{e.employee_code} · {e.department}</p></div><span className="tag">{e.role}</span></li>)}</ul></section>}</main>
}

function Review({ id, user }: {id:string; user:Session}) {
  const [request,setRequest] = useState<Detail>()
  const [error,setError] = useState('')
  const [busy,setBusy] = useState(false)
  const path='requests/'+id
  async function refresh(){ setRequest(await portal<Detail>(path)) }
  useEffect(() => { void refresh().catch(e=>setError(message(e))) },[id])
  async function act(action:string) {
    setBusy(true); setError('')
    try {
      await portal(path+(action==='APPLY'?'/apply':'/decisions'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision:action})})
      await refresh()
    } catch(e){setError(message(e)); await refresh().catch(()=>{})} finally{setBusy(false)}
  }
  return <main><p><a href="#">Back to requests</a></p><h1>Request #{id}</h1>
    {error && <p className="error" role="alert">{error}</p>}
    {request && <section className="card"><div className="card-heading"><h2>{request.plan.request_context?.request_title || 'Access change'}</h2>
    <span className="tag">{request.status.replaceAll('_',' ')} · {request.approved_count}/2</span></div>
    <p>{request.name} ({request.employee_code}) · {request.plan.current_role} → {request.target_role || 'Offboarded'}</p>
    <p>{request.plan.justification}</p><p>Effective {request.effective_date} · Manager {request.plan.manager} · Submitted by {request.requester}</p>
    {['grant','revoke','retain'].map(group=><p key={group}><strong>{group.toUpperCase()}</strong> · {request.plan.proposed_permissions[group].join(', ') || 'None'}</p>)}
    <h3>Activity</h3><ol>{request.events.map((v,i)=><li key={i}>{v.actor} · {v.event_type} · {new Date(v.occurred_at).toLocaleString()}</li>)}</ol>
    {user.role==='APPROVER' && request.status==='PENDING_APPROVAL' && (request.events.some(v=>v.actor===user.username && v.event_type==='APPROVE')
      ? <p>Your approval is recorded. A different approver must decide next.</p> :
      <div className="actions"><button disabled={busy} onClick={()=>act('APPROVE')}>Approve</button><button className="reject" disabled={busy} onClick={()=>act('REJECT')}>Reject</button></div>)}
    {user.role==='HR' && request.status==='APPROVED' && <button disabled={busy} onClick={()=>act('APPLY')}>Apply change</button>}
    </section>}</main>
}

function EmployeeHome({ route }: { route: string }) {
  const [data, setData] = useState<EmployeeProfile>()
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    let timer: number
    async function read() {
      try {
        const profile = await portal<EmployeeProfile>('profile', { signal: controller.signal })
        if (controller.signal.aborted) return
        setData(profile)
        setError('')
      } catch (failure) {
        if (controller.signal.aborted) return
        setData(undefined)
        setError(message(failure))
      }
      timer = window.setTimeout(read, 7000)
    }
    void read()
    return () => { controller.abort(); window.clearTimeout(timer) }
  }, [])
  if (!data) return <main>{error ? <p className="error" role="alert">{error}</p> : <p role="status">Loading your access…</p>}</main>
  if (route.startsWith('apps/')) {
    const app = applications.find(item => route === 'apps/' + item.slug)
    return app ? <ApplicationScreen key={app.slug} app={app} profile={data} /> :
      <main><h1>Application not found</h1><a href="#">Back to My access</a></main>
  }
  return <main><p className="eyebrow">EMPLOYEE PORTAL</p><h1>My access</h1>
    <section className="card"><h2>{data.name}</h2><p>{data.employee_code} · {data.department}</p><h3>Current role · {data.role}</h3>
    <div className="permission-list">{data.permissions.map(p=><span key={p} className="permission">{p}</span>)}</div></section>
    <section className="card"><h2>My applications</h2><div className="app-access">
      {applications.map(app => <DemoAppCard key={app.slug} app={app} profile={data} />)}
    </div></section>
    <section className="card"><h2>My access changes</h2><Rows rows={data.requests} links={false}/></section></main>
}

export default function Portal(){
  const [user,setUser]=useState<Session>()
  const [error,setError]=useState('')
  const route=useLocation()
  async function reload(){setUser(await session());setError('')}
  useEffect(()=>{
    const read=()=>{void reload().catch(e=>setError(message(e)))}
    read(); window.addEventListener('session-ended',read)
    return ()=>window.removeEventListener('session-ended',read)
  },[])
  if(error) return <main><p role="alert">{error}</p><button onClick={()=>location.reload()}>Retry connection</button></main>
  if(!user) return <main>Connecting to NeuroForge…</main>
  if(!user.role) return <Login reload={reload}/>
  const hr=user.role==='HR'
  return <><header><a className="brand" href="#">NeuroForge</a><div className="actions"><span>{user.username} · {user.role}</span>
    <button onClick={async()=>{try{await portal('logout',{method:'POST'});location.hash='';await reload()}catch(e){setError(message(e))}}}>Sign out</button></div></header>
    {user.role==='EMPLOYEE' ? <EmployeeHome key={user.username} route={route}/> : hr && route==='create' ? <CreateRequest integrated/> :
     /^request\/\d+$/.test(route) ? <Review key={route} id={route.split('/')[1]} user={user}/> : <Queue hr={hr}/>}</>
}

