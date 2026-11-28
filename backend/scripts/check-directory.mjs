// Local integration check using the packaged backend, an ephemeral RSA key,
// and the database credentials inherited from the caller's terminal.
import { generateKeyPairSync, sign } from 'node:crypto'
import { createServer } from 'node:http'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { setTimeout as delay } from 'node:timers/promises'

const jar = fileURLToPath(new URL('../target/backend-0.1.0.jar', import.meta.url))
if (!existsSync(jar)) {
  throw new Error('Backend JAR missing. Package the backend with Maven first.')
}
const missing = ['DB_USER', 'DB_PASSWORD'].filter(name => !process.env[name])
if (missing.length) {
  throw new Error('Set ' + missing.join(' and ') + ' in the PowerShell window running this check.')
}
const { publicKey, privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048 })
const jwk = { ...publicKey.export({ format: 'jwk' }), kid: 'directory-check', alg: 'RS256', use: 'sig' }
const keys = createServer((req, res) => {
  if (req.url !== '/keys') { res.writeHead(404).end(); return }
  res.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify({ keys: [jwk] }))
})
await new Promise((resolve, reject) => keys.once('error', reject).listen(0, '127.0.0.1', resolve))
const issuer = 'http://127.0.0.1:' + keys.address().port
const java = process.env.JAVA_HOME ? join(process.env.JAVA_HOME, 'bin', process.platform === 'win32' ? 'java.exe' : 'java') : 'java'
const child = spawn(java, ['-jar', jar, '--server.port=0',
  '--spring.security.oauth2.resourceserver.jwt.jwk-set-uri=' + issuer + '/keys'],
  { env: { ...process.env, IAM_ISSUER: issuer }, stdio: ['ignore', 'pipe', 'inherit'] })
let output = ''
child.stdout.on('data', chunk => {
  process.stdout.write(chunk)
  output = (output + chunk).slice(-32000)
})
let launchError
child.on('error', error => { launchError = error })
const stop = () => { child.kill(); keys.close() }
process.once('SIGINT', stop)
try {
  let port
  for (let i = 0; i < 120; i++) {
    if (launchError) throw launchError
    if (child.exitCode !== null || child.signalCode) throw new Error('Backend stopped during startup. Check its startup message above.')
    port = output.match(/Tomcat started on port (\d+)/)?.[1]
    if (port) break
    await delay(500)
  }
  if (!port) throw new Error('Timed out waiting for backend startup.')
  const url = 'http://127.0.0.1:' + port + '/api/employees'
  if ((await fetch(url)).status !== 401) throw new Error('Expected HTTP 401 for the anonymous request.')
  const encode = obj => Buffer.from(JSON.stringify(obj)).toString('base64url')
  const now = Math.floor(Date.now() / 1000)
  const payload = encode({ alg: 'RS256', kid: jwk.kid }) + '.' + encode({
    iss: issuer, aud: 'neuroforge', sub: 'local-directory-check', scope: 'iam.plan', iat: now, exp: now + 60,
  })
  const token = payload + '.' + sign('RSA-SHA256', Buffer.from(payload), privateKey).toString('base64url')
  const response = await fetch(url, { headers: { Authorization: 'Bearer ' + token } })
  if (!response.ok) throw new Error('Authenticated employee request returned HTTP ' + response.status)
  const employees = await response.json()
  const codes = new Set(employees.map(e => e.employee_code))
  if (!['EF-1001','EF-1002','EF-1003','EF-1004','EF-1005','EF-1006','EF-1007'].every(code => codes.has(code))) {
    throw new Error('The directory response is missing seeded employees.')
  }
  console.table(employees.map(({ employee_code, name, department }) => ({ employee_code, name, department })))
  console.log('PASS: authenticated Spring Boot directory read returned ' + employees.length + ' employees.')
  if (process.argv.includes('--plan')) {
    const cwd = fileURLToPath(new URL('../../ai-service/', import.meta.url))
    const python = join(cwd, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
    const env = { ...process.env, BACKEND_MODE: 'http', BACKEND_BASE_URL: new URL(url).origin }
    delete env.DB_USER
    delete env.DB_PASSWORD
    await new Promise((resolve, reject) => {
      const check = spawn(python, ['-m', 'scripts.check_live_plan'], { cwd, env, stdio: ['pipe', 'inherit', 'inherit'] })
      check.once('error', reject)
      check.stdin.on('error', reject)
      check.once('close', code => code === 0 ? resolve() : reject(new Error('Planner check failed.')))
      check.stdin.end(token)
    })
  }
} finally {
  stop()
  process.removeListener('SIGINT', stop)
}
