import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function Markdown({ text }) {
  const normalized = (text || '').replace(/<br\s*\/?>/gi, '  \n')
  return (
    <div className="space-y-2 text-sm leading-relaxed break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <div className="-mx-1 overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full border-collapse text-xs sm:text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-slate-200 bg-slate-100 px-2 py-1.5 text-left text-xs font-semibold text-slate-700 break-words">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-slate-100 px-2 py-1.5 align-top text-xs leading-relaxed text-slate-600 break-words sm:text-sm">{children}</td>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-navy-300 pl-3 text-slate-500">{children}</blockquote>
          ),
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-navy-600 underline">
              {children}
            </a>
          ),
          h1: ({ children }) => <h1 className="text-base font-semibold text-slate-900">{children}</h1>,
          h2: ({ children }) => <h2 className="text-sm font-semibold text-slate-900">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-900">{children}</h3>,
          ul: ({ children }) => <ul className="list-disc pl-4">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-4">{children}</ol>,
          li: ({ children }) => <li className="text-slate-700">{children}</li>,
        }}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  )
}