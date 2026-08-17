import ReactMarkdown from 'react-markdown'

export default function Markdown({ text }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed">
      <ReactMarkdown
        components={{
          table: ({ children }) => (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full border-collapse">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-slate-200 bg-slate-100 px-2.5 py-1.5 text-left font-semibold text-slate-700 word-break break-word">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-slate-100 px-2.5 py-1.5 text-slate-600 word-break break-word">{children}</td>
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
        {text}
      </ReactMarkdown>
    </div>
  )
}