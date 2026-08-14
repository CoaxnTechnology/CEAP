import { useState, useEffect } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, MessageSquare, Download, Share2, ExternalLink } from 'lucide-react'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

export default function DocumentDetail() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { toast } = useApp()
  const [doc, setDoc] = useState(
    location.state?.doc
      ? { ...location.state.doc, updated: location.state.doc.updated || location.state.doc.lastUpdated }
      : null
  )
  const [loading, setLoading] = useState(!doc)

  useEffect(() => {
    if (doc) return
    setLoading(true)
    api(`/api/repository/documents/${id}`)
      .then((data) => {
        if (data?.document) {
          const d = data.document
          setDoc({
            id: d.id,
            title: d.name,
            department: d.department_name || d.department_id || '',
            status: d.status === 'active' ? 'Current' : d.status,
            year: d.created_at ? new Date(d.created_at * 1000).getFullYear().toString() : '',
            updated: d.updated_at ? new Date(d.updated_at * 1000).toISOString().slice(0, 10) : '',
            owner: d.owner_email || '',
            citation: '',
            snippet: d.description || '',
          })
        }
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [id, doc])

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl py-16 text-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-navy-200 border-t-navy-700 mx-auto" />
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="mx-auto max-w-2xl py-16 text-center">
        <p className="text-slate-600">Document not found</p>
        <Button className="mt-4" variant="secondary" onClick={() => navigate('/library')}>
          Back to library
        </Button>
      </div>
    )
  }

  const body =
    doc.snippet ||
    `This is a prototype view of "${doc.title}".

In production, CEAP would render the full document from the connected source (Google Drive or OneDrive), with version history, owners, and audit trail.

Department: ${doc.department || '—'}
Type: ${doc.type || '—'}
Academic year: ${doc.year || '—'}
Status: ${doc.status || '—'}
${doc.citation ? `Citation: ${doc.citation}` : ''}
${doc.owner ? `Owner: ${doc.owner}` : ''}
${doc.updated ? `Last updated: ${doc.updated}` : ''}
`
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-xs font-medium text-navy-600 hover:underline"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </button>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">{doc.title}</h1>
            {doc.status && <StatusBadge status={doc.status} />}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {[doc.department, doc.type, doc.year].filter(Boolean).join(' · ')}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() =>
              navigate('/chat', { state: { seedQuestion: `Explain key points of ${doc.title}` } })
            }
          >
            <MessageSquare className="h-4 w-4" /> Ask AI
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => toast('Download started (prototype)', 'success')}
          >
            <Download className="h-4 w-4" /> Download
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              navigator.clipboard?.writeText(window.location.href)
              toast('Link copied to clipboard', 'success')
            }}
          >
            <Share2 className="h-4 w-4" /> Share
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-700">
            {body}
          </pre>
        </Card>
        <div className="space-y-4">
          <Card>
            <h3 className="text-sm font-semibold text-slate-900">Metadata</h3>
            <dl className="mt-3 space-y-2 text-sm">
              {doc.citation && (
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Citation</dt>
                  <dd className="font-medium text-navy-700">{doc.citation}</dd>
                </div>
              )}
              {doc.owner && (
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Owner</dt>
                  <dd className="font-medium">{doc.owner}</dd>
                </div>
              )}
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Updated</dt>
                <dd className="font-medium">{doc.updated || '—'}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-500">Department</dt>
                <dd className="font-medium">{doc.department || '—'}</dd>
              </div>
            </dl>
          </Card>
          <Button
            className="w-full"
            variant="secondary"
            onClick={() => navigate(`/search?q=${encodeURIComponent(doc.title)}`)}
          >
            <ExternalLink className="h-4 w-4" /> Find related in Search
          </Button>
        </div>
      </div>
    </div>
  )
}
