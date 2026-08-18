import { useState, useRef, useCallback } from 'react'
import { Upload, File, X, AlertCircle } from 'lucide-react'
import Button from './Button'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function FileUpload({ onUploaded, onClose, uploadUrl = '/api/upload', existingNames = [] }) {
  const [dragOver, setDragOver] = useState(false)
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [currentFile, setCurrentFile] = useState(null)
  const [stage, setStage] = useState('uploading')
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const addFiles = useCallback((list) => {
    setError(null)
    const existing = new Set(existingNames.map((n) => n.trim().toLowerCase()))
    const valid = []
    const dups = []
    for (const f of list) {
      const name = f.name.trim()
      const ext = '.' + name.split('.').pop().toLowerCase()
      if (existing.has(name.toLowerCase())) {
        dups.push(name)
        continue
      }
      if (!['.pdf', '.docx', '.pptx', '.xlsx', '.xls', '.csv', '.txt'].includes(ext)) {
        setError(`Unsupported format: ${f.name}`)
        continue
      }
      valid.push(f)
    }
    if (dups.length) {
      setError(`${dups.join(', ')} already uploaded. Duplicates were skipped.`)
    }
    setFiles((prev) => [...prev, ...valid])
  }, [existingNames])

  function removeFile(i) {
    setFiles((prev) => prev.filter((_, idx) => idx !== i))
  }

  async function handleUpload() {
    if (!files.length) return
    setUploading(true)
    setError(null)
    setCurrentFile(files[0].name)
    setStage('uploading')
    const errs = []
    for (let i = 0; i < files.length; i++) {
      const f = files[i]
      setCurrentFile(f.name)
      const fd = new FormData()
      fd.append('file', f)
      try {
        setStage(i === 0 ? 'uploading' : 'indexing')
        const res = await fetch(`${API_BASE}${uploadUrl}`, {
          method: 'POST', body: fd, credentials: 'include',
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.error || `HTTP ${res.status}`)
        }
        onUploaded?.(f.name)
        setStage('indexing')
      } catch (err) {
        errs.push(`${f.name}: ${err.message}`)
      }
    }
    setUploading(false)
    if (errs.length) {
      setError(errs.join('; '))
    } else {
      setFiles([])
      onClose?.()
    }
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); addFiles(Array.from(e.dataTransfer.files)) }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition ${
          dragOver ? 'border-navy-400 bg-navy-50' : 'border-slate-200 bg-slate-50 hover:border-navy-300'
        }`}
      >
        <Upload className="mb-3 h-8 w-8 text-slate-400" />
        <p className="text-sm font-medium text-slate-600">Drop files here or click to browse</p>
        <p className="mt-1 text-xs text-slate-400">PDF, DOCX, PPTX, XLSX, CSV, TXT</p>
        <input ref={inputRef} type="file" multiple className="hidden" onChange={(e) => addFiles(Array.from(e.target.files))} />
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-danger-50 px-3 py-2 text-xs text-danger-600">
          <AlertCircle className="h-4 w-4 shrink-0" /> {error}
        </div>
      )}

      {files.length > 0 && (
        <ul className="space-y-1.5">
          {files.map((f, i) => (
            <li key={i} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm">
              <File className="h-4 w-4 shrink-0 text-slate-400" />
              <span className="flex-1 truncate text-slate-700">{f.name}</span>
              <span className="text-xs text-slate-400">{(f.size / 1024).toFixed(0)} KB</span>
              <button type="button" onClick={() => removeFile(i)} className="text-slate-400 hover:text-danger-500">
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {uploading && (
        <div className="space-y-2 rounded-lg bg-slate-50 px-3 py-3">
          <div className="flex items-center justify-between gap-2 text-xs">
            <span className="font-medium text-slate-600">{currentFile || 'Uploading…'}</span>
            <span className="text-slate-400">
              {stage === 'uploading' ? 'Uploading…' : 'Indexing — making it searchable…'}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
            <div className={`h-full rounded-full bg-navy-600 transition-all duration-700 ${stage === 'uploading' ? 'w-1/3 animate-pulse' : 'w-2/3 animate-pulse'}`} />
          </div>
        </div>
      )}

      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={handleUpload} disabled={!files.length || uploading}>
          {uploading ? 'Uploading...' : `Upload ${files.length} file${files.length !== 1 ? 's' : ''}`}
        </Button>
      </div>
    </div>
  )
}
