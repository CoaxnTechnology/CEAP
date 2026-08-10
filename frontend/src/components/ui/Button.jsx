export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled,
  type = 'button',
  ...props
}) {
  const variants = {
    primary: 'bg-navy-900 text-white hover:bg-navy-800 disabled:opacity-50',
    secondary:
      'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50',
    danger: 'bg-danger-600 text-white hover:bg-danger-500 disabled:opacity-50',
    success: 'bg-success-600 text-white hover:bg-success-700 disabled:opacity-50',
    ghost: 'text-slate-600 hover:bg-slate-100 disabled:opacity-50',
    dangerOutline:
      'border border-danger-200 bg-danger-50 text-danger-600 hover:bg-danger-100 disabled:opacity-50',
  }
  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-5 py-3 text-sm',
  }
  return (
    <button
      type={type}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition focus:outline-none focus:ring-2 focus:ring-navy-200 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
