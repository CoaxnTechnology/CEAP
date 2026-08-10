import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Activity,
  BookOpen,
  Shield,
  CheckCircle2,
  AlertTriangle,
  FileWarning,
} from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { api } from '../lib/api'

const icons = {
  update: BookOpen,
  chat: Activity,
  generate: FileWarning,
  sync: CheckCircle2,
  approve: Shield,
  alert: AlertTriangle,
}

export default function ActivityPage() {
  const navigate = useNavigate()
  const [activity, setActivity] = useState([])

  useEffect(() => {
    api('/api/activity')
      .then((r) => setActivity(r.activity || []))
      .catch(() => setActivity([]))
  }, [])

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Activity</h1>
          <p className="mt-1 text-sm text-slate-500">Audit trail of platform actions</p>
        </div>
        <Button size="sm" variant="secondary" onClick={() => navigate('/')}>
          Dashboard
        </Button>
      </div>

      <Card padding={false}>
        <ul className="divide-y divide-slate-50">
          {activity.map((item) => {
            const Icon = icons[item.type] || Activity
            return (
              <li key={item.id} className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50/80">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy-50 text-navy-600">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-slate-700">
                    <span className="font-semibold text-slate-900">{item.user}</span>{' '}
                    <span className="text-slate-500">{item.action.toLowerCase()}</span>{' '}
                    <span className="font-medium text-navy-800">{item.target}</span>
                  </p>
                </div>
                <span className="shrink-0 text-xs text-slate-400">{item.time}</span>
              </li>
            )
          })}
        </ul>
      </Card>
    </div>
  )
}
