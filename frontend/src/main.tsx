import Portal from './Portal'
import { createRoot } from 'react-dom/client'
import CreateRequest from './pages/hr/CreateRequest'
import './index.css'

createRoot(document.getElementById('root')!).render(location.pathname === '/planner' ? <CreateRequest /> : <Portal />)
