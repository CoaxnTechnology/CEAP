import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import Card from './Card'

export default function KpiCard({ label, value, delta, trend = 'flat', spark = [], onClick }) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor =
    trend === 'up' ? 'text-success-600' : trend === 'down' ? 'text-danger-600' : trend === 'warn' ? 'text-warning-600' : 'text-slate-400'

  const max = Math.max(...(spark.length ? spark : [1]))
  const min = Math.min(...(spark.length ? spark : [0]))
  const range = max - min || 1

  return (
    <Card className="card-hover !p-4" onClick={onClick}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        {delta && (
          <span className={`inline-flex items-center gap-0.5 text-[11px] font-semibold ${trendColor}`}>
            <TrendIcon className="h-3 w-3" />
            {delta}
          </span>
        )}
      </div>
      <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
      {spark.length > 0 && (
        <div className="mt-3 flex h-8 items-end gap-0.5">
          {spark.map((v, i) => (
            <div
              key={i}
              className="flex-1 rounded-sm bg-navy-200/80"
              style={{ height: `${12 + ((v - min) / range) * 20}px` }}
            />
          ))}
        </div>
      )}
    </Card>
  )
}
