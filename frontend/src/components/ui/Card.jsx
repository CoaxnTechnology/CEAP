export default function Card({ children, className = '', padding = true, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border border-slate-200/80 shadow-sm ${
        padding ? 'p-5' : ''
      } ${onClick ? 'cursor-pointer hover:border-navy-200 hover:shadow-md transition-all' : ''} ${className}`}
    >
      {children}
    </div>
  )
}
