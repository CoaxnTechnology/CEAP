import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import Section from '../components/ui/Section'
import InsightBanner from '../components/ui/InsightBanner'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import { useApp } from '../context/AppContext'
import { academicIntel } from '../data/osData'
import { api } from '../lib/api'

export default function Academic() {
  const navigate = useNavigate()
  const { toast } = useApp()
  const [data, setData] = useState(null)
  const [addingAssessment, setAddingAssessment] = useState(false)
  const [newAssessment, setNewAssessment] = useState({ title: '', department: '', class_name: '', teacher: '', due_date: '' })
  const [attdForm, setAttdForm] = useState({ class_name: '', date: '', present: '', total: '' })
  const [newCov, setNewCov] = useState({ department: '', class_name: '', coverage: '' })

  const load = () => api('/api/academic/overview').then(setData).catch(() => setData(null))

  useEffect(() => {
    load()
  }, [])

  const stats = data?.stats || {
    classesInSession: academicIntel.classesInSession,
    avgClassAttendance: academicIntel.avgClassAttendance,
    assessmentsDue: academicIntel.assessmentsDue,
    curriculumCoverage: academicIntel.curriculumCoverage,
  }
  const insights = data?.insights || academicIntel.insights
  const departments = data?.departments || academicIntel.departments
  const assessments = data?.assessments || []
  const coverageRows = data?.coverage || []
  const attendanceRows = data?.attendance || []
  const classOptions = [...new Set([...coverageRows.map((r) => r.class_name), ...attendanceRows.map((r) => r.class_name)])]

  async function saveCoverage(row) {
    try {
      await api('/api/academic/coverage', {
        method: 'POST',
        body: JSON.stringify({ department: row.department, class_name: row.class_name, coverage: row.coverage }),
      })
      toast(`Coverage updated for ${row.department} ${row.class_name}`, 'success')
      load()
    } catch {
      toast('Could not save coverage', 'error')
    }
  }

  async function addCoverage(e) {
    e.preventDefault()
    if (!newCov.department.trim() || !newCov.class_name.trim()) return
    try {
      await api('/api/academic/coverage', {
        method: 'POST',
        body: JSON.stringify({ department: newCov.department, class_name: newCov.class_name, coverage: Number(newCov.coverage) || 0 }),
      })
      toast(`Coverage added for ${newCov.department} ${newCov.class_name}`, 'success')
      setNewCov({ department: '', class_name: '', coverage: '' })
      load()
    } catch {
      toast('Could not add coverage', 'error')
    }
  }

  async function markGraded(id) {
    try {
      await api(`/api/academic/assessments/${id}`, { method: 'PATCH', body: JSON.stringify({ status: 'graded' }) })
      toast('Assessment marked graded', 'success')
      load()
    } catch {
      toast('Could not update assessment', 'error')
    }
  }

  async function createAssessment(e) {
    e.preventDefault()
    try {
      await api('/api/academic/assessments', {
        method: 'POST',
        body: JSON.stringify(newAssessment),
      })
      toast('Assessment added', 'success')
      setAddingAssessment(false)
      setNewAssessment({ title: '', department: '', class_name: '', teacher: '', due_date: '' })
      load()
    } catch {
      toast('Could not add assessment', 'error')
    }
  }

  async function recordAttendance(e) {
    e.preventDefault()
    try {
      await api('/api/academic/attendance', {
        method: 'POST',
        body: JSON.stringify(attdForm),
      })
      toast('Attendance recorded', 'success')
      setAttdForm({ class_name: '', date: '', present: '', total: '' })
      load()
    } catch {
      toast('Could not record attendance', 'error')
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Academic Workspace"
        title="Teaching & Learning Intelligence"
        subtitle="Curriculum coverage, assessments, and department health — AI-assisted, not a gradebook ERP."
        actions={
          <Button size="sm" onClick={() => navigate('/ai/chat', { state: { seedQuestion: 'Where is curriculum coverage lagging?' } })}>
            Ask Teacher AI
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Classes in session" value={String(stats.classesInSession)} spark={[38, 40, 41, 42, 42, 42, 42]} trend="up" delta="Live" />
        <KpiCard label="Avg attendance" value={`${stats.avgClassAttendance}%`} spark={[93, 94, 95, 95, 96, 95, 95.4]} trend="up" delta="+0.4" />
        <KpiCard label="Assessments due" value={String(stats.assessmentsDue)} spark={[12, 11, 10, 9, 8, 8, 8]} trend="warn" delta="SLA" />
        <KpiCard label="Curriculum coverage" value={`${stats.curriculumCoverage}%`} spark={[50, 55, 58, 60, 63, 66, 68]} trend="up" delta="Term" />
      </div>

      <InsightBanner title="Academic AI" items={insights} />

      <Section title="Department comparison" padding={false}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 text-xs uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Department</th>
                <th className="px-3 py-3">Coverage</th>
                <th className="px-3 py-3">Attendance</th>
                <th className="px-5 py-3">Student risk flags</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {departments.map((d) => (
                <tr key={d.name} className="hover:bg-slate-50/80">
                  <td className="px-5 py-3.5 font-medium text-slate-800">{d.name}</td>
                  <td className="px-3 py-3.5">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100">
                        <div className="h-full bg-navy-600" style={{ width: `${d.coverage}%` }} />
                      </div>
                      <span>{d.coverage}%</span>
                    </div>
                  </td>
                  <td className="px-3 py-3.5">{d.attendance != null ? `${d.attendance}%` : '—'}</td>
                  <td className="px-5 py-3.5">
                    <button
                      type="button"
                      onClick={() => navigate('/students', { state: { risk: 'High', from: 'academic' } })}
                      className="font-medium text-navy-700 hover:underline"
                    >
                      {d.risk} {d.risk === 1 ? 'student' : 'students'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        title="Curriculum coverage by class"
        subtitle="Track teaching progress per class — coverage updates flow into the department view above"
        action={
          <Button size="sm" variant="secondary" onClick={load}>Refresh</Button>
        }
        padding={false}
      >
        <form onSubmit={addCoverage} className="flex flex-wrap items-end gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <label className="text-xs font-medium text-slate-500">Department</label>
            <input
              className="field mt-1"
              placeholder="e.g. Mathematics"
              value={newCov.department}
              onChange={(e) => setNewCov({ ...newCov, department: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500">Class</label>
            <input
              className="field mt-1"
              placeholder="e.g. 10-A"
              value={newCov.class_name}
              onChange={(e) => setNewCov({ ...newCov, class_name: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500">Coverage %</label>
            <input
              type="number"
              min={0}
              max={100}
              className="field mt-1 w-20"
              value={newCov.coverage}
              onChange={(e) => setNewCov({ ...newCov, coverage: e.target.value })}
              required
            />
          </div>
          <Button size="sm" type="submit">Add class</Button>
        </form>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 text-xs uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Department</th>
                <th className="px-3 py-3">Class</th>
                <th className="px-3 py-3">Coverage</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {coverageRows.map((row) => (
                <CoverageRow key={row.id} row={row} onSave={saveCoverage} />
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        title="Class attendance"
        subtitle="Record present / total per class per day — department averages roll up from here"
        padding={false}
      >
        <div className="flex flex-wrap items-end gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            <label className="text-xs font-medium text-slate-500">Class</label>
            <select
              className="field mt-1"
              value={attdForm.class_name}
              onChange={(e) => setAttdForm({ ...attdForm, class_name: e.target.value })}
            >
              <option value="">Select class…</option>
              {classOptions.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500">Date</label>
            <input
              type="date"
              className="field mt-1"
              value={attdForm.date}
              onChange={(e) => setAttdForm({ ...attdForm, date: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500">Present</label>
            <input
              type="number"
              min={0}
              className="field mt-1 w-20"
              value={attdForm.present}
              onChange={(e) => setAttdForm({ ...attdForm, present: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500">Total</label>
            <input
              type="number"
              min={1}
              className="field mt-1 w-20"
              value={attdForm.total}
              onChange={(e) => setAttdForm({ ...attdForm, total: e.target.value })}
            />
          </div>
          <Button size="sm" onClick={recordAttendance}>Record</Button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 text-xs uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Class</th>
                <th className="px-3 py-3">Dept</th>
                <th className="px-3 py-3">Date</th>
                <th className="px-3 py-3">Present</th>
                <th className="px-3 py-3">Total</th>
                <th className="px-5 py-3">Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {attendanceRows.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50/80">
                  <td className="px-5 py-3.5 font-medium text-slate-800">{a.class_name}</td>
                  <td className="px-3 py-3.5">{a.department}</td>
                  <td className="px-3 py-3.5">{a.date}</td>
                  <td className="px-3 py-3.5">{a.present}</td>
                  <td className="px-3 py-3.5">{a.total}</td>
                  <td className="px-5 py-3.5">{a.rate}%</td>
                </tr>
              ))}
              {attendanceRows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-6 text-center text-sm text-slate-400">
                    No attendance recorded yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        title="Assessments"
        subtitle="Due dates, SLA, and grading status"
        action={
          <Button size="sm" variant="secondary" onClick={() => setAddingAssessment(true)}>
            Add assessment
          </Button>
        }
        padding={false}
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 text-xs uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">Assessment</th>
                <th className="px-3 py-3">Dept</th>
                <th className="px-3 py-3">Class</th>
                <th className="px-3 py-3">Teacher</th>
                <th className="px-3 py-3">Due</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {assessments.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50/80">
                  <td className="px-5 py-3.5 font-medium text-slate-800">{a.title}</td>
                  <td className="px-3 py-3.5">{a.department}</td>
                  <td className="px-3 py-3.5">{a.class_name}</td>
                  <td className="px-3 py-3.5">{a.teacher}</td>
                  <td className="px-3 py-3.5">{a.due_date}</td>
                  <td className="px-3 py-3.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        a.status === 'graded'
                          ? 'bg-success-50 text-success-700'
                          : 'bg-warning-50 text-warning-600'
                      }`}
                    >
                      {a.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5">
                    {a.status !== 'graded' && (
                      <Button size="sm" variant="ghost" onClick={() => markGraded(a.id)}>
                        Mark graded
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
              {assessments.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-6 text-center text-sm text-slate-400">
                    No assessments yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Section>

      <Modal open={addingAssessment} onClose={() => setAddingAssessment(false)} title="Add assessment">
        <form onSubmit={createAssessment} className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-500">Title</label>
            <input
              className="field mt-1"
              value={newAssessment.title}
              onChange={(e) => setNewAssessment({ ...newAssessment, title: e.target.value })}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-500">Department</label>
              <input
                className="field mt-1"
                value={newAssessment.department}
                onChange={(e) => setNewAssessment({ ...newAssessment, department: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500">Class</label>
              <input
                className="field mt-1"
                value={newAssessment.class_name}
                onChange={(e) => setNewAssessment({ ...newAssessment, class_name: e.target.value })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-500">Teacher</label>
              <input
                className="field mt-1"
                value={newAssessment.teacher}
                onChange={(e) => setNewAssessment({ ...newAssessment, teacher: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500">Due date</label>
              <input
                type="date"
                className="field mt-1"
                value={newAssessment.due_date}
                onChange={(e) => setNewAssessment({ ...newAssessment, due_date: e.target.value })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setAddingAssessment(false)}>Cancel</Button>
            <Button type="submit">Add</Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

function CoverageRow({ row, onSave }) {
  const [coverage, setCoverage] = useState(row.coverage)
  const [saving, setSaving] = useState(false)

  useEffect(() => setCoverage(row.coverage), [row.coverage])

  async function save() {
    if (saving) return
    setSaving(true)
    try {
      await onSave({ ...row, coverage })
    } finally {
      setSaving(false)
    }
  }

  return (
    <tr className="hover:bg-slate-50/80">
      <td className="px-5 py-3.5 font-medium text-slate-800">{row.department}</td>
      <td className="px-3 py-3.5">{row.class_name}</td>
      <td className="px-3 py-3.5">
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={100}
            value={coverage}
            onChange={(e) => setCoverage(e.target.value)}
            className="field w-20 !py-1 text-center"
          />
          <span className="text-xs text-slate-400">%</span>
        </div>
      </td>
      <td className="px-5 py-3.5 text-right">
        <Button size="sm" variant="ghost" onClick={save} disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </Button>
      </td>
    </tr>
  )
}
