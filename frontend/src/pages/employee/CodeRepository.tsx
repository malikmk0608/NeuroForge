const files = [
  { path: 'README.md', content: '# Access review workspace\nPrepare a request, review the access plan, and submit it for approval.' },
  { path: 'src/review.ts', content: "export const requiredApprovals = 2\nexport const initialStatus = 'PENDING_APPROVAL'" },
  { path: 'docs/roles.md', content: 'HR submits and applies changes.\nTwo distinct approvers review each request.' },
]

export default function CodeRepository() {
  return <section className="card app-content">
    <h2>Repository files</h2>
    <p className="app-caption">Sample repository · access-review / main</p>
    {files.map(file => <details className="file-row" key={file.path}>
      <summary>{file.path}</summary>
      <pre>{file.content}</pre>
    </details>)}
  </section>
}
