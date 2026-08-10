/* CEAP Education Edition — AI Operating System mock universe */

export const workspaces = [
  { id: 'executive', label: 'Executive', path: '/', icon: 'LayoutDashboard', desc: 'Principal morning OS' },
  { id: 'academic', label: 'Academic', path: '/academic', icon: 'GraduationCap', desc: 'Teaching & learning intelligence' },
  { id: 'students', label: 'Students', path: '/students', icon: 'Users', desc: 'Student 360 & success' },
  { id: 'admissions', label: 'Admissions', path: '/admissions', icon: 'UserPlus', desc: 'Pipeline & conversion' },
  { id: 'finance', label: 'Finance', path: '/finance', icon: 'Wallet', desc: 'Revenue intelligence' },
  { id: 'hr', label: 'HR', path: '/hr', icon: 'Briefcase', desc: 'People & workforce' },
  { id: 'compliance', label: 'Compliance', path: '/compliance', icon: 'ShieldCheck', desc: 'Inspection readiness' },
  { id: 'knowledge', label: 'Knowledge', path: '/knowledge', icon: 'Library', desc: 'School memory & hub' },
  { id: 'ai', label: 'AI Studio', path: '/ai', icon: 'Sparkles', desc: 'Agents & generation' },
  { id: 'admin', label: 'Admin', path: '/admin', icon: 'Settings', desc: 'Platform control' },
]

export const morningBriefing = {
  date: 'Monday, 28 July 2025',
  greeting: 'Good morning',
  summary:
    'Attendance is strong at 96.2%. Fee collections lag 8% vs target. 3 high-risk students need counselor attention. Fire Safety Certificate expires in 18 days — Compliance AI recommends starting renewal today.',
  bullets: [
    { type: 'success', text: 'Attendance 96.2% — above term average' },
    { type: 'warning', text: '₹12.4L outstanding fees · 41 families overdue' },
    { type: 'alert', text: 'Fire Safety Certificate expires in 18 days' },
    { type: 'info', text: '12 admissions applications awaiting interview' },
    { type: 'ai', text: 'AI recommends parent outreach for Class 10 defaulters' },
  ],
}

export const executiveKpis = [
  { id: 'attendance', label: 'Attendance', value: '96.2%', delta: '+1.1%', trend: 'up', spark: [92, 93, 94, 95, 94, 96, 96.2] },
  { id: 'revenue', label: 'Fee collected (MTD)', value: '₹48.2L', delta: '−8% vs target', trend: 'down', spark: [30, 35, 38, 42, 44, 46, 48] },
  { id: 'admissions', label: 'Admissions pipeline', value: '86', delta: '+14 this week', trend: 'up', spark: [40, 48, 52, 60, 68, 74, 86] },
  { id: 'risk', label: 'At-risk students', value: '7', delta: '3 high', trend: 'warn', spark: [12, 11, 10, 9, 8, 7, 7] },
  { id: 'approvals', label: 'Pending approvals', value: '9', delta: '2 urgent', trend: 'warn', spark: [5, 6, 8, 7, 9, 10, 9] },
  { id: 'compliance', label: 'Inspection ready', value: '74%', delta: '+3 pts', trend: 'up', spark: [60, 62, 65, 68, 70, 72, 74] },
]

export const students = [
  {
    id: 's1',
    name: 'Aarav Mehta',
    class: '10-A',
    roll: '10A-14',
    photo: 'AM',
    gender: 'M',
    dob: '2010-03-12',
    bloodGroup: 'B+',
    admissionNo: 'GIS/2020/0412',
    house: 'Blue',
    riskScore: 78,
    riskLevel: 'High',
    attendance: 82,
    feesDue: 45000,
    feesStatus: 'Overdue',
    gpa: 6.8,
    parent: { name: 'Rohit Mehta', phone: '+91 98765 41001', email: 'rohit.mehta@email.com', relation: 'Father' },
    aiSummary:
      'Aarav shows declining attendance over 6 weeks and two overdue fee installments. Academic performance dipped in Math & Science mid-terms. Recommend counselor check-in and parent finance conversation.',
    recommendations: [
      'Schedule counselor session this week',
      'Send fee reminder with flexible plan option',
      'Math remedial support via Academic AI',
    ],
    medical: { allergies: 'None', conditions: 'Mild asthma', lastCheckup: '2025-01-15' },
    achievements: ['Science Olympiad Bronze 2024', 'Inter-house Debate Finalist'],
    behavior: 'Generally cooperative; 1 late arrival warning this term',
  },
  {
    id: 's2',
    name: 'Ananya Krishnan',
    class: '8-B',
    roll: '8B-07',
    photo: 'AK',
    gender: 'F',
    dob: '2012-07-22',
    bloodGroup: 'O+',
    admissionNo: 'GIS/2021/0288',
    house: 'Green',
    riskScore: 18,
    riskLevel: 'Low',
    attendance: 98,
    feesDue: 0,
    feesStatus: 'Cleared',
    gpa: 9.4,
    parent: { name: 'Lakshmi Krishnan', phone: '+91 98765 41022', email: 'lakshmi.k@email.com', relation: 'Mother' },
    aiSummary:
      'High-performing student with excellent attendance and cleared fees. Strong in STEM. Candidate for leadership club and scholarship mention in annual review.',
    recommendations: ['Nominate for Student Council', 'STEM enrichment track'],
    medical: { allergies: 'Peanuts', conditions: 'None', lastCheckup: '2025-02-01' },
    achievements: ['Gold – Math League', 'Perfect attendance 2024-25'],
    behavior: 'Exemplary',
  },
  {
    id: 's3',
    name: 'Vihaan Patel',
    class: '12-C',
    roll: '12C-03',
    photo: 'VP',
    gender: 'M',
    dob: '2008-11-05',
    bloodGroup: 'A+',
    admissionNo: 'GIS/2016/0091',
    house: 'Red',
    riskScore: 42,
    riskLevel: 'Medium',
    attendance: 91,
    feesDue: 15000,
    feesStatus: 'Partial',
    gpa: 8.1,
    parent: { name: 'Meera Patel', phone: '+91 98765 41033', email: 'meera.patel@email.com', relation: 'Mother' },
    aiSummary:
      'Board year student with solid academics. One pending fee installment. Monitor stress during pre-boards; offer wellness check-in.',
    recommendations: ['Confirm board exam registration docs', 'Offer wellness workshop'],
    medical: { allergies: 'None', conditions: 'None', lastCheckup: '2024-11-20' },
    achievements: ['Football Captain', 'Service Learning Award'],
    behavior: 'Positive peer influence',
  },
  {
    id: 's4',
    name: 'Sara Khan',
    class: '5-A',
    roll: '5A-19',
    photo: 'SK',
    gender: 'F',
    dob: '2015-01-30',
    bloodGroup: 'AB+',
    admissionNo: 'GIS/2022/0610',
    house: 'Yellow',
    riskScore: 25,
    riskLevel: 'Low',
    attendance: 95,
    feesDue: 0,
    feesStatus: 'Cleared',
    gpa: 8.9,
    parent: { name: 'Imran Khan', phone: '+91 98765 41044', email: 'imran.k@email.com', relation: 'Father' },
    aiSummary: 'Well-adjusted primary student. Strong reading scores. No operational risks.',
    recommendations: ['Reading club invitation'],
    medical: { allergies: 'Dust', conditions: 'None', lastCheckup: '2025-03-10' },
    achievements: ['Art Exhibition Winner'],
    behavior: 'Cheerful and engaged',
  },
  {
    id: 's5',
    name: 'Kabir Sharma',
    class: '9-A',
    roll: '9A-11',
    photo: 'KS',
    gender: 'M',
    dob: '2011-09-18',
    bloodGroup: 'B−',
    admissionNo: 'GIS/2019/0333',
    house: 'Blue',
    riskScore: 65,
    riskLevel: 'High',
    attendance: 79,
    feesDue: 28000,
    feesStatus: 'Overdue',
    gpa: 6.2,
    parent: { name: 'Neha Sharma', phone: '+91 98765 41055', email: 'neha.s@email.com', relation: 'Mother' },
    aiSummary:
      'Elevated risk: attendance + fees + academic dip. Multiple late arrivals. Parent meeting overdue since May.',
    recommendations: ['Urgent parent conference', 'Attendance intervention plan', 'Fee counseling'],
    medical: { allergies: 'None', conditions: 'None', lastCheckup: '2024-08-12' },
    achievements: [],
    behavior: '2 disciplinary notes this term',
  },
]

export function studentTimeline(studentId) {
  const base = {
    s1: [
      { id: 1, date: '2025-07-25', type: 'attendance', title: 'Absent – uninformed', detail: 'Class 10-A period 1–4' },
      { id: 2, date: '2025-07-20', type: 'fees', title: 'Fee reminder sent', detail: 'Installment 3 overdue ₹45,000' },
      { id: 3, date: '2025-07-10', type: 'academic', title: 'Mid-term results', detail: 'Math 58 · Science 62 · English 74' },
      { id: 4, date: '2025-06-28', type: 'meeting', title: 'Parent call logged', detail: 'Discussed attendance pattern' },
      { id: 5, date: '2025-06-01', type: 'document', title: 'Medical note uploaded', detail: 'Asthma action plan' },
      { id: 6, date: '2025-04-15', type: 'achievement', title: 'Science Olympiad Bronze', detail: 'Inter-school 2025' },
      { id: 7, date: '2020-04-01', type: 'admission', title: 'Admitted to GIS', detail: 'Class 5 entry' },
    ],
    s2: [
      { id: 1, date: '2025-07-22', type: 'achievement', title: 'Math League Gold', detail: 'State level' },
      { id: 2, date: '2025-07-01', type: 'fees', title: 'Annual fees cleared', detail: 'Full payment' },
      { id: 3, date: '2025-05-12', type: 'academic', title: 'Top of class 8-B', detail: 'GPA 9.4' },
      { id: 4, date: '2021-06-01', type: 'admission', title: 'Admitted to GIS', detail: 'Class 4 entry' },
    ],
  }
  return (
    base[studentId] || [
      { id: 1, date: '2025-07-01', type: 'academic', title: 'Term started', detail: '2025-26 academic year' },
      { id: 2, date: '2024-04-01', type: 'admission', title: 'Admitted', detail: 'Greenwood International' },
    ]
  )
}

export const studentDocuments = {
  s1: [
    { id: 1, name: 'Birth Certificate.pdf', type: 'Identity', updated: '2020-04-01' },
    { id: 2, name: 'Aadhaar.pdf', type: 'Identity', updated: '2023-01-12' },
    { id: 3, name: 'Report Card Term 1.pdf', type: 'Academic', updated: '2025-07-10' },
    { id: 4, name: 'Fee Receipt Apr.pdf', type: 'Finance', updated: '2025-04-05' },
    { id: 5, name: 'Asthma Action Plan.pdf', type: 'Medical', updated: '2025-06-01' },
  ],
  s2: [
    { id: 1, name: 'Birth Certificate.pdf', type: 'Identity', updated: '2021-06-01' },
    { id: 2, name: 'Report Card Term 1.pdf', type: 'Academic', updated: '2025-07-08' },
    { id: 3, name: 'Allergy Note.pdf', type: 'Medical', updated: '2025-02-01' },
  ],
}

export const financeIntel = {
  mtdCollected: 4820000,
  target: 5200000,
  outstanding: 1240000,
  predictedDefaulters: 18,
  scholarships: 8,
  cashIn: [32, 38, 41, 45, 44, 48, 48.2],
  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
  insights: [
    'Class 10 & 12 drive 41% of outstanding balance.',
    'Predicted 18 families may default without intervention this month.',
    'Scholarship disbursements on track — ₹6.2L remaining budget.',
    'AI: Offer 2-installment plans to families with >60 days overdue.',
  ],
  outstandingByClass: [
    { cls: '10', amount: 3.2 },
    { cls: '12', amount: 2.8 },
    { cls: '9', amount: 1.9 },
    { cls: '11', amount: 1.5 },
    { cls: '8', amount: 1.1 },
    { cls: 'Other', amount: 1.9 },
  ],
}

export const admissionsPipeline = [
  { id: 1, name: 'Ishaan Rao', grade: '1', stage: 'Applied', score: 82, counselor: 'Sneha K.', date: '2025-07-20' },
  { id: 2, name: 'Myra Singh', grade: '6', stage: 'Interview', score: 91, counselor: 'Rahul M.', date: '2025-07-18' },
  { id: 3, name: 'Dev Malhotra', grade: '9', stage: 'Offer', score: 88, counselor: 'Sneha K.', date: '2025-07-15' },
  { id: 4, name: 'Pari Desai', grade: 'Nursery', stage: 'Tour', score: 70, counselor: 'Anita D.', date: '2025-07-22' },
  { id: 5, name: 'Reyansh Gupta', grade: '11', stage: 'Enrolled', score: 94, counselor: 'Rahul M.', date: '2025-07-10' },
  { id: 6, name: 'Aisha Banerjee', grade: '4', stage: 'Applied', score: 77, counselor: 'Anita D.', date: '2025-07-24' },
]

export const admissionsStats = {
  applied: 42,
  interview: 18,
  offer: 12,
  enrolled: 14,
  conversion: '33%',
  targetSeats: 120,
  filled: 86,
}

export const hrSnapshot = {
  headcount: 85,
  presentToday: 81,
  onLeave: 4,
  openRoles: 3,
  expiringContracts: 2,
  trainingDue: 6,
  staff: [
    { id: 1, name: 'Meera Nair', role: 'HOD Academic', dept: 'Academic', status: 'Present', leaveBalance: 8 },
    { id: 2, name: 'Rahul Mehta', role: 'HR Lead', dept: 'HR', status: 'Present', leaveBalance: 5 },
    { id: 3, name: 'Vikram Singh', role: 'Admin Manager', dept: 'Admin', status: 'On Leave', leaveBalance: 2 },
    { id: 4, name: 'Sneha Kapoor', role: 'Finance Lead', dept: 'Finance', status: 'Present', leaveBalance: 11 },
    { id: 5, name: 'Anita Desai', role: 'DSL / Teacher', dept: 'Admin', status: 'Present', leaveBalance: 7 },
  ],
  leaveRequests: [
    { id: 1, name: 'Vikram Singh', type: 'Casual', dates: '28–29 Jul', status: 'Approved' },
    { id: 2, name: 'Pooja Iyer', type: 'Sick', dates: '28 Jul', status: 'Pending' },
    { id: 3, name: 'Arjun Menon', type: 'Earned', dates: '1–5 Aug', status: 'Pending' },
  ],
}

export const academicIntel = {
  classesInSession: 42,
  avgClassAttendance: 95.4,
  assessmentsDue: 8,
  curriculumCoverage: 68,
  departments: [
    { name: 'Science', coverage: 72, attendance: 96, risk: 2 },
    { name: 'Mathematics', coverage: 65, attendance: 94, risk: 4 },
    { name: 'Languages', coverage: 70, attendance: 97, risk: 1 },
    { name: 'Humanities', coverage: 66, attendance: 95, risk: 2 },
    { name: 'Arts & Sports', coverage: 80, attendance: 93, risk: 0 },
  ],
  insights: [
    'Math coverage lagging in Classes 9–10 — consider block periods.',
    '3 teachers have assessments pending beyond SLA.',
    'Board batch (12) revision plan 92% complete.',
  ],
}

export const knowledgeCards = [
  { id: 1, title: 'Child Protection Policy', type: 'Policy', dept: 'Admin', status: 'Current', summary: 'Safeguarding duties, DSL role, reporting timelines.', relations: 4, updated: '2025-06-12' },
  { id: 2, title: 'Fee Structure 2025-26', type: 'Circular', dept: 'Finance', status: 'Current', summary: 'Class-wise fees, sibling discount, payment windows.', relations: 3, updated: '2025-03-15' },
  { id: 3, title: 'Staff Leave Policy', type: 'Policy', dept: 'HR', status: 'Current', summary: 'CL, EL, maternity, approval chain via HR portal.', relations: 5, updated: '2025-04-01' },
  { id: 4, title: 'Exam SOP – Mid Terms', type: 'SOP', dept: 'Academic', status: 'Current', summary: 'Paper submission, invigilation, result publishing.', relations: 6, updated: '2025-05-20' },
  { id: 5, title: 'Fire Safety Certificate', type: 'Certificate', dept: 'Admin', status: 'Expiring', summary: 'Valid until mid-Aug 2025. Renewal in progress.', relations: 2, updated: '2024-08-15' },
  { id: 6, title: 'Leadership Review Minutes', type: 'Minutes', dept: 'Executive', status: 'Current', summary: 'Knowledge gaps, inspection prep, fee strategy.', relations: 8, updated: '2025-07-25' },
  { id: 7, title: 'New Teacher Onboarding', type: 'Training', dept: 'HR', status: 'Current', summary: '30-day checklist, safeguarding, systems access.', relations: 7, updated: '2025-02-10' },
  { id: 8, title: 'Parent Communication FAQ', type: 'FAQ', dept: 'Admin', status: 'Current', summary: 'Channels, SLAs, escalation for grievances.', relations: 3, updated: '2025-01-18' },
]

export const schoolMemory = [
  { id: 1, when: '2025-07-25 14:00', kind: 'Decision', title: 'Approve flexible fee plan for Class 10 defaulters', actor: 'Priya Sharma', tags: ['Finance', 'Students'] },
  { id: 2, when: '2025-07-25 10:30', kind: 'Meeting', title: 'Leadership Knowledge Review', actor: 'Meera Nair', tags: ['Compliance', 'Knowledge'] },
  { id: 3, when: '2025-07-24 16:20', kind: 'Approval', title: 'Parent Circular – Annual Day published', actor: 'Priya Sharma', tags: ['Generate'] },
  { id: 4, when: '2025-07-22 09:15', kind: 'Policy', title: 'Updated Transport monsoon SOP draft rejected', actor: 'Vikram Singh', tags: ['Transport'] },
  { id: 5, when: '2025-07-20 11:00', kind: 'Discussion', title: 'Board inspection evidence pack strategy', actor: 'Anita Desai', tags: ['Compliance'] },
  { id: 6, when: '2025-07-18 15:45', kind: 'Document', title: 'Leave Policy v3.1 synced from HR Drive', actor: 'System', tags: ['HR', 'Knowledge'] },
  { id: 7, when: '2025-07-15 13:00', kind: 'Decision', title: 'Open 2 PGT Science roles', actor: 'Rahul Mehta', tags: ['HR'] },
]

export const aiAgents = [
  { id: 'principal', name: 'Principal AI', scope: 'School-wide intelligence & decisions', color: '#1E3A5F', permissions: 'Executive + Approvals' },
  { id: 'teacher', name: 'Teacher AI', scope: 'Lesson support, assessments, students', color: '#0F766E', permissions: 'Academic + Student 360 (class)' },
  { id: 'finance', name: 'Finance AI', scope: 'Fees, forecasts, defaulters', color: '#B45309', permissions: 'Finance only' },
  { id: 'admissions', name: 'Admissions AI', scope: 'Pipeline, scoring, outreach', color: '#7C3AED', permissions: 'Admissions' },
  { id: 'hr', name: 'HR AI', scope: 'Leave, recruitment, policies', color: '#0369A1', permissions: 'HR' },
  { id: 'compliance', name: 'Compliance AI', scope: 'Inspection, evidence, gaps', color: '#B91C1C', permissions: 'Compliance' },
  { id: 'library', name: 'Library AI', scope: 'Knowledge retrieval & summaries', color: '#4F46E5', permissions: 'Knowledge read' },
  { id: 'success', name: 'Student Success AI', scope: 'Risk, interventions, wellbeing', color: '#059669', permissions: 'Students + Counselors' },
]

export const tasks = [
  { id: 1, title: 'Renew Fire Safety Certificate', owner: 'Vikram Singh', due: '2025-08-05', priority: 'Urgent', status: 'Open', workspace: 'Compliance' },
  { id: 2, title: 'Parent conference – Aarav Mehta', owner: 'Meera Nair', due: '2025-07-30', priority: 'High', status: 'Open', workspace: 'Students' },
  { id: 3, title: 'Review Annual Day circular draft', owner: 'Priya Sharma', due: '2025-07-28', priority: 'High', status: 'In Review', workspace: 'AI Studio' },
  { id: 4, title: 'Close Q1 fee follow-ups Class 10', owner: 'Sneha Kapoor', due: '2025-08-01', priority: 'Medium', status: 'Open', workspace: 'Finance' },
  { id: 5, title: 'Interview slot – Myra Singh', owner: 'Rahul Mehta', due: '2025-07-29', priority: 'Medium', status: 'Open', workspace: 'Admissions' },
  { id: 6, title: 'Approve leave – Pooja Iyer', owner: 'Rahul Mehta', due: '2025-07-28', priority: 'Low', status: 'Open', workspace: 'HR' },
]

export const approvals = [
  { id: 1, title: 'Fee waiver – Kabir Sharma (25%)', type: 'Fee Waiver', requester: 'Sneha Kapoor', amount: '₹7,000', status: 'Pending', sla: '12h left' },
  { id: 2, title: 'Parent Circular – Annual Day 2025', type: 'Publish Document', requester: 'AI Studio', amount: '—', status: 'Pending', sla: '2d left' },
  { id: 3, title: 'Purchase – Lab chemicals Q2', type: 'Purchase', requester: 'Meera Nair', amount: '₹1.2L', status: 'Pending', sla: '3d left' },
  { id: 4, title: 'Offer letter – PGT Physics', type: 'Recruitment', requester: 'Rahul Mehta', amount: '—', status: 'Approved', sla: 'Done' },
  { id: 5, title: 'Transport route change – Whitefield', type: 'Transport', requester: 'Amit Joshi', amount: '—', status: 'Pending', sla: '1d left' },
]

export const calendarEvents = [
  { id: 1, title: 'Leadership standup', date: '2025-07-28', time: '09:00', type: 'Meeting' },
  { id: 2, title: 'Admissions interviews', date: '2025-07-29', time: '11:00', type: 'Admissions' },
  { id: 3, title: 'Fire drill', date: '2025-07-30', time: '10:30', type: 'Compliance' },
  { id: 4, title: 'PTA executive', date: '2025-08-02', time: '16:00', type: 'Meeting' },
  { id: 5, title: 'Board exam briefing Class 12', date: '2025-08-05', time: '14:00', type: 'Academic' },
  { id: 6, title: 'Fee last date reminder blast', date: '2025-08-10', time: '09:00', type: 'Finance' },
]

export const workflowTemplates = [
  { id: 'admission', name: 'Admission Journey', stages: ['Inquiry', 'Application', 'Assessment', 'Interview', 'Offer', 'Enrollment'], color: '#7C3AED' },
  { id: 'leave', name: 'Staff Leave', stages: ['Request', 'Manager', 'HR', 'Calendar', 'Done'], color: '#0369A1' },
  { id: 'purchase', name: 'Purchase Request', stages: ['Request', 'Budget Check', 'Principal', 'PO', 'Receive'], color: '#B45309' },
  { id: 'recruitment', name: 'Recruitment', stages: ['Requisition', 'Posting', 'Screen', 'Interview', 'Offer', 'Onboard'], color: '#0F766E' },
  { id: 'complaint', name: 'Parent Complaint', stages: ['Intake', 'Triage', 'Investigate', 'Resolve', 'Close'], color: '#B91C1C' },
  { id: 'fee-waiver', name: 'Fee Waiver', stages: ['Request', 'Finance Review', 'Principal', 'Apply', 'Notify'], color: '#4F46E5' },
  { id: 'transport', name: 'Transport Change', stages: ['Request', 'Capacity', 'Approve', 'Roster', 'Notify'], color: '#334e68' },
  { id: 'hostel', name: 'Hostel Allocation', stages: ['Apply', 'Eligibility', 'Allocate', 'Fee', 'Check-in'], color: '#059669' },
]

export const analyticsBundles = [
  { id: 'academic', title: 'Academic trends', metric: 'Avg GPA', value: '8.1', change: '+0.2' },
  { id: 'fee', title: 'Fee collection', metric: 'MTD', value: '₹48.2L', change: '−8%' },
  { id: 'attendance', title: 'Attendance', metric: 'School', value: '96.2%', change: '+1.1%' },
  { id: 'inspection', title: 'Inspection readiness', metric: 'Score', value: '74%', change: '+3' },
  { id: 'admissions', title: 'Enrollment funnel', metric: 'Conversion', value: '33%', change: '+4' },
  { id: 'hr', title: 'Workforce', metric: 'Present', value: '95%', change: 'stable' },
]

export const favorites = [
  { label: 'Student 360 · Aarav Mehta', path: '/students/s1' },
  { label: 'Finance Intelligence', path: '/finance' },
  { label: 'Generate Circular', path: '/ai/studio' },
  { label: 'Compliance Center', path: '/compliance' },
]

export const quickActions = [
  { label: 'Ask AI', path: '/ai/chat', icon: 'Sparkles' },
  { label: 'New circular', path: '/ai/studio', icon: 'FilePenLine' },
  { label: 'Find student', path: '/students', icon: 'Users' },
  { label: 'Approvals', path: '/approvals', icon: 'CheckSquare' },
  { label: 'Evidence pack', path: '/compliance', icon: 'Package' },
  { label: 'Schedule meeting', path: '/calendar', icon: 'CalendarDays' },
]

export const commandItems = [
  { id: 'c1', group: 'Navigate', label: 'Executive Workspace', path: '/', keywords: 'home principal dashboard briefing' },
  { id: 'c2', group: 'Navigate', label: 'Students', path: '/students', keywords: 'student 360 risk' },
  { id: 'c3', group: 'Navigate', label: 'Finance Intelligence', path: '/finance', keywords: 'fees revenue cash' },
  { id: 'c4', group: 'Navigate', label: 'Admissions', path: '/admissions', keywords: 'pipeline enroll' },
  { id: 'c5', group: 'Navigate', label: 'Compliance Center', path: '/compliance', keywords: 'inspection fire' },
  { id: 'c6', group: 'Navigate', label: 'Knowledge Hub', path: '/knowledge', keywords: 'policy sop memory' },
  { id: 'c7', group: 'Navigate', label: 'School Memory', path: '/knowledge/memory', keywords: 'decisions meetings' },
  { id: 'c8', group: 'Navigate', label: 'AI Agents', path: '/ai', keywords: 'copilot agents' },
  { id: 'c9', group: 'Navigate', label: 'Document Studio', path: '/ai/studio', keywords: 'generate circular letter' },
  { id: 'c10', group: 'Navigate', label: 'Workflow Builder', path: '/workflows', keywords: 'automation leave admission' },
  { id: 'c11', group: 'Navigate', label: 'Analytics', path: '/analytics', keywords: 'bi charts trends' },
  { id: 'c12', group: 'Navigate', label: 'Tasks', path: '/tasks', keywords: 'todo work' },
  { id: 'c13', group: 'Navigate', label: 'Approvals', path: '/approvals', keywords: 'approve pending' },
  { id: 'c14', group: 'Navigate', label: 'Calendar', path: '/calendar', keywords: 'events schedule' },
  { id: 'c15', group: 'Actions', label: 'Invite user', path: '/admin/users', keywords: 'invite staff' },
  { id: 'c16', group: 'Actions', label: 'Open settings', path: '/settings', keywords: 'preferences' },
]

export const docStudioTypes = [
  'Circular', 'Letter', 'Notice', 'Certificate', 'Meeting Minutes', 'Policy', 'Email', 'Report',
  'Offer Letter', 'Appointment Letter', 'Transfer Certificate', 'Bonafide Certificate', 'Experience Letter',
]
