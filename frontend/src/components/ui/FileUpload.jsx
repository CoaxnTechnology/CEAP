import { useState, useRef, useCallback } from 'react'
import { Upload, File, X, AlertCircle } from 'lucide-react'
import Button from './Button'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function FileUpload({ onUploaded, onClose, uploadUrl = '/api/upload' }) {
  const [dragOver, setDragOver] = useState(false)
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const addFiles = useCallback((list) => {
    setError(null)
    const valid = []
    for (const f of list) {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
      if (!['.pdf', '.docx', '.pptx', '.xlsx', '.xls', '.csv', '.txt'].includes(ext)) {
        setError(`Unsupported format: ${f.name}`)
        continue
      }
      valid.push(f)
    }
    setFiles((prev) => [...prev, ...valid])
  }, [])

  function removeFile(i) {
    setFiles((prev) => prev.filter((_, idx) => idx !== i))
  }

  async function handleUpload() {
    if (!files.length) return
    setUploading(true)
    setError(null)
    const errs = []
    for (const f of files) {
      const fd = new FormData()
      fd.append('file', f)
      try {
        const res = await fetch(`${API_BASE}${uploadUrl}`, {
          method: 'POST', body: fd, credentials: 'include',
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.error || `HTTP ${res.status}`)
        }
        onUploaded?.(f.name)
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

      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={handleUpload} disabled={!files.length || uploading}>
          {uploading ? 'Uploading...' : `Upload ${files.length} file${files.length !== 1 ? 's' : ''}`}
        </Button>
      </div>
    </div>
  )
}
