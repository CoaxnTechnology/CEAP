/* ─── CoAxn Enterprise AI Platform (CEAP) – Education Edition ─── */
/* Mock data for prototype UI only – no real backend */

export const currentUser = {
  name: 'Priya Sharma',
  role: 'Principal',
  email: 'demo@ceap.ai',
  avatar: 'PS',
  school: 'Greenwood International School',
}

export const departments = [
  'Academic',
  'HR',
  'Finance',
  'Admin',
  'Transport',
  'IT',
  'Sports',
]

export const academicYears = ['2024-25', '2025-26', '2023-24']

export const documentTypes = [
  'Policy',
  'Circular',
  'Certificate',
  'Report',
  'Letter',
  'SOP',
  'Handbook',
]

/* ─── Dashboard KPIs ─── */
export const kpis = [
  {
    id: 'coverage',
    label: 'Knowledge Coverage',
    value: '87%',
    change: '+4% vs last month',
    trend: 'up',
    description: 'Policies & SOPs indexed',
  },
  {
    id: 'gaps',
    label: 'Open Gaps',
    value: '12',
    change: '3 critical',
    trend: 'down',
    description: 'Missing or outdated docs',
  },
  {
    id: 'expiring',
    label: 'Expiring Certificates',
    value: '5',
    change: 'Within 30 days',
    trend: 'warn',
    description: 'Safety & compliance certs',
  },
  {
    id: 'users',
    label: 'Active Users',
    value: '48',
    change: '+6 this week',
    trend: 'up',
    description: 'Staff using CEAP',
  },
]

export const complianceReadiness = {
  available: 42,
  expiring: 5,
  missing: 7,
  outdated: 3,
}

export const recentActivity = [
  {
    id: 1,
    user: 'Anita Desai',
    action: 'Updated',
    target: 'Child Protection Policy v3.2',
    time: '12 min ago',
    type: 'update',
  },
  {
    id: 2,
    user: 'Rahul Mehta',
    action: 'Asked AI',
    target: 'Leave policy for teaching staff',
    time: '28 min ago',
    type: 'chat',
  },
  {
    id: 3,
    user: 'Sneha Kapoor',
    action: 'Generated',
    target: 'Parent Circular – Annual Day 2025',
    time: '1 hr ago',
    type: 'generate',
  },
  {
    id: 4,
    user: 'Vikram Singh',
    action: 'Synced',
    target: 'HR Drive / Policies folder',
    time: '2 hrs ago',
    type: 'sync',
  },
  {
    id: 5,
    user: 'Priya Sharma',
    action: 'Approved',
    target: 'Fee Policy Amendment – 2025-26',
    time: '3 hrs ago',
    type: 'approve',
  },
  {
    id: 6,
    user: 'System',
    action: 'Flagged',
    target: 'Fire Safety Certificate expiring in 18 days',
    time: '5 hrs ago',
    type: 'alert',
  },
]

export const knowledgeGaps = [
  {
    id: 1,
    title: 'Transport Safety SOP',
    department: 'Transport',
    severity: 'critical',
    reason: 'Missing document – required for board inspection',
  },
  {
    id: 2,
    title: 'Cyber Safety Guidelines',
    department: 'IT',
    severity: 'high',
    reason: 'No version for 2025-26 academic year',
  },
  {
    id: 3,
    title: 'Staff Grievance Policy',
    department: 'HR',
    severity: 'medium',
    reason: 'Last updated 2022 – may be outdated',
  },
  {
    id: 4,
    title: 'Lab Chemical Disposal Procedure',
    department: 'Academic',
    severity: 'high',
    reason: 'Not found in knowledge base',
  },
  {
    id: 5,
    title: 'Visitor Management Protocol',
    department: 'Admin',
    severity: 'medium',
    reason: 'Incomplete – missing annexures',
  },
]

/* ─── Search results ─── */
export const searchResults = [
  {
    id: 1,
    title: 'Child Protection Policy',
    snippet:
      'All staff, volunteers and contractors must complete safeguarding training within 30 days of joining. Any concern regarding child safety must be reported immediately to the Designated Safeguarding Lead (DSL)...',
    status: 'Current',
    department: 'Admin',
    type: 'Policy',
    year: '2025-26',
    citation: 'CPP-2025-v3.2 §4.1',
    lastUpdated: '2025-06-12',
    owner: 'Anita Desai',
  },
  {
    id: 2,
    title: 'Staff Leave Policy',
    snippet:
      'Teaching staff are entitled to 12 days casual leave and 15 days earned leave per academic year. Maternity leave of 26 weeks is available as per statutory provisions. Leave applications must be submitted via the HR portal...',
    status: 'Current',
    department: 'HR',
    type: 'Policy',
    year: '2025-26',
    citation: 'HR-LEAVE-2025 §2.3',
    lastUpdated: '2025-04-01',
    owner: 'Rahul Mehta',
  },
  {
    id: 3,
    title: 'Fee Structure Circular 2025-26',
    snippet:
      'Tuition fees for the academic year 2025-26 have been revised. Class 1–5: ₹1,45,000; Class 6–8: ₹1,65,000; Class 9–12: ₹1,85,000. Sibling discount of 10% applies to the younger child...',
    status: 'Current',
    department: 'Finance',
    type: 'Circular',
    year: '2025-26',
    citation: 'FIN-CIR-2025-08',
    lastUpdated: '2025-03-15',
    owner: 'Sneha Kapoor',
  },
  {
    id: 4,
    title: 'Fire Safety Certificate',
    snippet:
      'This is to certify that Greenwood International School, Building Block A & B, has been inspected and found compliant with fire safety norms under the State Fire Safety Act. Valid until 15 August 2025...',
    status: 'Expiring',
    department: 'Admin',
    type: 'Certificate',
    year: '2024-25',
    citation: 'FSC-2024-091',
    lastUpdated: '2024-08-15',
    owner: 'Vikram Singh',
  },
  {
    id: 5,
    title: 'Examination SOP – Mid-Term Assessments',
    snippet:
      'Mid-term examinations shall be conducted in September and February. Question papers must be submitted to the Academic Coordinator 14 days in advance. Invigilation duty roster will be published 7 days prior...',
    status: 'Current',
    department: 'Academic',
    type: 'SOP',
    year: '2025-26',
    citation: 'ACAD-EXAM-SOP-v2',
    lastUpdated: '2025-05-20',
    owner: 'Meera Nair',
  },
  {
    id: 6,
    title: 'Parent Communication Guidelines',
    snippet:
      'All formal parent communications must be approved by the Head of Department before dispatch. Circulars are issued via CEAP Document Studio. Emergency SMS is reserved for safety-critical alerts only...',
    status: 'Current',
    department: 'Admin',
    type: 'Policy',
    year: '2025-26',
    citation: 'ADM-PCG-2025 §3',
    lastUpdated: '2025-01-10',
    owner: 'Priya Sharma',
  },
  {
    id: 7,
    title: 'Transport Safety Circular – Monsoon',
    snippet:
      'During monsoon season, all school buses must carry emergency kits, first-aid boxes and waterproof tarpaulins. Drivers must report waterlogging on routes immediately to the Transport Coordinator...',
    status: 'Outdated',
    department: 'Transport',
    type: 'Circular',
    year: '2023-24',
    citation: 'TRN-CIR-2023-11',
    lastUpdated: '2023-06-01',
    owner: 'Amit Joshi',
  },
]

export const relatedKnowledge = [
  { id: 1, title: 'Safeguarding Training Checklist', type: 'SOP' },
  { id: 2, title: 'DSL Role Description', type: 'Policy' },
  { id: 3, title: 'Incident Reporting Form', type: 'Form' },
  { id: 4, title: 'Board Inspection Evidence Pack 2024', type: 'Report' },
]

export const conversationHistory = [
  { id: 1, title: 'Leave entitlement for teachers', department: 'hr', time: 'Today', preview: 'How many casual leave days...' },
  { id: 2, title: 'Child protection reporting steps', department: 'admin', time: 'Today', preview: 'What is the process if a staff...' },
  { id: 3, title: 'Fee refund policy query', department: 'finance', time: 'Yesterday', preview: 'Can parents claim partial refund...' },
  { id: 4, title: 'Exam paper submission deadline', department: 'academic', time: 'Yesterday', preview: 'When should question papers...' },
  { id: 5, title: 'Fire drill schedule requirements', department: 'admin', time: '2 days ago', preview: 'How often must fire drills...' },
]

/* ─── Compliance ─── */
export const inspectionFrameworks = [
  { id: 'govt', label: 'Government Inspection' },
  { id: 'board', label: 'Board Affiliation (CBSE)' },
  { id: 'accred', label: 'Accreditation (NABET/ISO)' },
]

export const complianceEvidence = [
  {
    id: 1,
    title: 'Child Protection Policy',
    framework: 'govt',
    status: 'Available',
    lastUpdated: '2025-06-12',
    owner: 'Anita Desai',
    category: 'Safeguarding',
  },
  {
    id: 2,
    title: 'Fire Safety Certificate',
    framework: 'govt',
    status: 'Expiring',
    lastUpdated: '2024-08-15',
    owner: 'Vikram Singh',
    category: 'Safety',
  },
  {
    id: 3,
    title: 'Building Stability Certificate',
    framework: 'govt',
    status: 'Available',
    lastUpdated: '2025-01-20',
    owner: 'Vikram Singh',
    category: 'Infrastructure',
  },
  {
    id: 4,
    title: 'Staff Qualification Records',
    framework: 'board',
    status: 'Available',
    lastUpdated: '2025-04-01',
    owner: 'Rahul Mehta',
    category: 'HR',
  },
  {
    id: 5,
    title: 'Transport Safety SOP',
    framework: 'govt',
    status: 'Missing',
    lastUpdated: '—',
    owner: 'Amit Joshi',
    category: 'Transport',
  },
  {
    id: 6,
    title: 'Annual Academic Calendar',
    framework: 'board',
    status: 'Available',
    lastUpdated: '2025-03-01',
    owner: 'Meera Nair',
    category: 'Academic',
  },
  {
    id: 7,
    title: 'Fee Structure Disclosure',
    framework: 'govt',
    status: 'Available',
    lastUpdated: '2025-03-15',
    owner: 'Sneha Kapoor',
    category: 'Finance',
  },
  {
    id: 8,
    title: 'Lab Safety Audit Report',
    framework: 'accred',
    status: 'Outdated',
    lastUpdated: '2023-11-10',
    owner: 'Meera Nair',
    category: 'Safety',
  },
  {
    id: 9,
    title: 'Inclusive Education Policy',
    framework: 'board',
    status: 'Missing',
    lastUpdated: '—',
    owner: 'Anita Desai',
    category: 'Academic',
  },
  {
    id: 10,
    title: 'Water Quality Certificate',
    framework: 'govt',
    status: 'Expiring',
    lastUpdated: '2024-09-01',
    owner: 'Vikram Singh',
    category: 'Health',
  },
  {
    id: 11,
    title: 'Teacher Training Log 2024-25',
    framework: 'accred',
    status: 'Available',
    lastUpdated: '2025-02-28',
    owner: 'Rahul Mehta',
    category: 'HR',
  },
  {
    id: 12,
    title: 'Emergency Evacuation Plan',
    framework: 'govt',
    status: 'Available',
    lastUpdated: '2025-05-01',
    owner: 'Vikram Singh',
    category: 'Safety',
  },
]

export const evidencePackPreview = [
  { name: '01_Child_Protection_Policy.pdf', size: '245 KB', status: 'Ready' },
  { name: '02_Fire_Safety_Certificate.pdf', size: '180 KB', status: 'Expiring' },
  { name: '03_Building_Stability_Cert.pdf', size: '320 KB', status: 'Ready' },
  { name: '04_Staff_Qualification_Records.xlsx', size: '1.2 MB', status: 'Ready' },
  { name: '05_Transport_Safety_SOP.pdf', size: '—', status: 'Missing' },
  { name: '06_Academic_Calendar_2025.pdf', size: '95 KB', status: 'Ready' },
  { name: '07_Fee_Structure_Disclosure.pdf', size: '110 KB', status: 'Ready' },
  { name: 'Cover_Letter_Inspection.docx', size: '42 KB', status: 'Draft' },
]

/* ─── Knowledge Library ─── */
export const knowledgeLibrary = [
  {
    id: 1,
    title: 'Child Protection Policy',
    department: 'Admin',
    type: 'Policy',
    status: 'Current',
    year: '2025-26',
    updated: '2025-06-12',
  },
  {
    id: 2,
    title: 'Fee Policy',
    department: 'Finance',
    type: 'Policy',
    status: 'Current',
    year: '2025-26',
    updated: '2025-03-15',
  },
  {
    id: 3,
    title: 'Leave Policy',
    department: 'HR',
    type: 'Policy',
    status: 'Current',
    year: '2025-26',
    updated: '2025-04-01',
  },
  {
    id: 4,
    title: 'Examination SOP',
    department: 'Academic',
    type: 'SOP',
    status: 'Current',
    year: '2025-26',
    updated: '2025-05-20',
  },
  {
    id: 5,
    title: 'Fire Safety Certificate',
    department: 'Admin',
    type: 'Certificate',
    status: 'Expiring',
    year: '2024-25',
    updated: '2024-08-15',
  },
  {
    id: 6,
    title: 'Transport Safety Circular',
    department: 'Transport',
    type: 'Circular',
    status: 'Outdated',
    year: '2023-24',
    updated: '2023-06-01',
  },
  {
    id: 7,
    title: 'Student Handbook 2025-26',
    department: 'Academic',
    type: 'Handbook',
    status: 'Current',
    year: '2025-26',
    updated: '2025-03-01',
  },
  {
    id: 8,
    title: 'IT Acceptable Use Policy',
    department: 'IT',
    type: 'Policy',
    status: 'Current',
    year: '2025-26',
    updated: '2025-02-10',
  },
]

/* ─── Meetings ─── */
export const meetings = [
  {
    id: 1,
    title: 'Leadership Knowledge Review',
    date: '2025-07-30',
    time: '10:00 AM',
    attendees: ['Priya Sharma', 'Meera Nair', 'Rahul Mehta'],
    status: 'Upcoming',
    agenda: 'Review open knowledge gaps before board inspection',
  },
  {
    id: 2,
    title: 'Compliance Evidence Sync',
    date: '2025-07-28',
    time: '2:00 PM',
    attendees: ['Anita Desai', 'Vikram Singh'],
    status: 'In Progress',
    agenda: 'Fire safety cert renewal & transport SOP',
  },
  {
    id: 3,
    title: 'AI Document Studio Walkthrough',
    date: '2025-07-25',
    time: '11:30 AM',
    attendees: ['Sneha Kapoor', 'Priya Sharma', 'Admin Team'],
    status: 'Completed',
    agenda: 'Training on circular generation workflow',
  },
  {
    id: 4,
    title: 'HR Policy Q&A with Staff',
    date: '2025-08-05',
    time: '3:30 PM',
    attendees: ['Rahul Mehta', 'All HODs'],
    status: 'Upcoming',
    agenda: 'Leave policy clarifications for 2025-26',
  },
]

/* ─── Admin / Connectors ─── */
export const connectors = [
  {
    id: 'gdrive',
    name: 'Google Drive',
    description: 'Sync shared drives and policy folders',
    status: 'Connected',
    lastSync: '28 Jul 2025, 9:14 AM',
    color: '#4285F4',
  },
  {
    id: 'onedrive',
    name: 'OneDrive',
    description: 'Microsoft 365 school tenant documents',
    status: 'Connected',
    lastSync: '28 Jul 2025, 8:02 AM',
    color: '#0078D4',
  },
]

export const connectedFolders = [
  {
    id: 1,
    name: 'HR / Policies',
    source: 'Google Drive',
    path: 'Shared drives/HR/Policies',
    lastSynced: '28 Jul 2025, 9:14 AM',
    docs: 34,
  },
  {
    id: 2,
    name: 'Admin / Certificates',
    source: 'Google Drive',
    path: 'Shared drives/Admin/Certificates',
    lastSynced: '28 Jul 2025, 9:14 AM',
    docs: 18,
  },
  {
    id: 3,
    name: 'Academic / SOPs',
    source: 'OneDrive',
    path: 'School Docs/Academic/SOPs',
    lastSynced: '28 Jul 2025, 8:02 AM',
    docs: 27,
  },
  {
    id: 4,
    name: 'Finance / Circulars',
    source: 'OneDrive',
    path: 'School Docs/Finance/Circulars',
    lastSynced: '28 Jul 2025, 8:02 AM',
    docs: 41,
  },
  {
    id: 5,
    name: 'Board Inspection Archive',
    source: 'Google Drive',
    path: 'Shared drives/Compliance/Board 2024',
    lastSynced: '27 Jul 2025, 6:30 PM',
    docs: 56,
  },
]

export const notifications = [
  {
    id: 1,
    title: 'Fire Safety Certificate expires in 18 days',
    time: '2 hrs ago',
    unread: true,
    type: 'warning',
  },
  {
    id: 2,
    title: 'New document synced: Leave Policy v3.1',
    time: '5 hrs ago',
    unread: true,
    type: 'info',
  },
  {
    id: 3,
    title: 'Evidence pack ready for review',
    time: 'Yesterday',
    unread: false,
    type: 'success',
  },
  {
    id: 4,
    title: '3 knowledge gaps marked critical',
    time: 'Yesterday',
    unread: false,
    type: 'alert',
  },
]

export const roles = [
  { id: 1, name: 'Principal', users: 1, permissions: 'Full access' },
  { id: 2, name: 'HOD', users: 8, permissions: 'Dept knowledge + generate' },
  { id: 3, name: 'Teacher', users: 32, permissions: 'Search + AI Chat' },
  { id: 4, name: 'Admin Staff', users: 6, permissions: 'Compliance + connectors' },
  { id: 5, name: 'Viewer', users: 4, permissions: 'Read-only search' },
]
