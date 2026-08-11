import { Link } from 'react-router-dom'
import { GraduationCap } from 'lucide-react'

const SECTIONS = {
  privacy: [
    {
      title: 'Data We Access',
      body: 'When you connect Google Drive or OneDrive, CEAP reads file metadata and downloads document contents to build a searchable knowledge base for your school. We only read files; we never modify or delete anything in your drives.',
    },
    {
      title: 'How We Use Data',
      body: 'Imported documents are indexed locally and used solely to power in-app search and AI assistance for your school. We do not sell, rent, or share personal data with third parties.',
    },
    {
      title: 'Storage & Retention',
      body: 'Extracted text is stored in our database and vector index. You can disconnect a source or delete imported documents at any time, which removes them from our systems.',
    },
    {
      title: 'Third-Party Services',
      body: 'OAuth connections use the official Microsoft Graph and Google Drive APIs. The Microsoft 365 and Google account names, emails, and tokens used to connect are only used to fetch your documents.',
    },
    {
      title: 'Contact',
      body: 'For privacy questions or data deletion requests, contact the school administrator at admin@ceap.school.',
    },
  ],
  terms: [
    {
      title: 'Acceptance of Terms',
      body: 'By using CEAP, you agree to these terms. CEAP is provided for internal school document management and knowledge retrieval.',
    },
    {
      title: 'Acceptable Use',
      body: 'You may use CEAP only for legitimate school administration purposes. You agree not to upload, import, or distribute content you are not authorized to share.',
    },
    {
      title: 'Connections to Third-Party Services',
      body: 'CEAP connects to your Google Drive or OneDrive only with your explicit consent. You control which folders and files are imported, and you may disconnect or remove them at any time.',
    },
    {
      title: 'No Warranty',
      body: 'CEAP is provided "as is" without warranty of any kind. We are not liable for damages arising from use of the service.',
    },
    {
      title: 'Changes',
      body: 'We may update these terms from time to time. Continued use of the service after changes constitutes acceptance of the revised terms.',
    },
  ],
}

export default function Legal({ type }) {
  const isPrivacy = type === 'privacy'
  const title = isPrivacy ? 'Privacy Policy' : 'Terms of Service'
  const sections = SECTIONS[type]

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="flex items-center gap-2 text-navy-700">
          <GraduationCap className="h-7 w-7" />
          <span className="text-lg font-semibold">CEAP</span>
        </div>
        <h1 className="mt-6 text-3xl font-bold tracking-tight text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-500">Effective date: August 11, 2026</p>

        <div className="mt-8 space-y-8">
          {sections.map((s) => (
            <section key={s.title}>
              <h2 className="text-lg font-semibold text-slate-900">{s.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.body}</p>
            </section>
          ))}
        </div>

        <p className="mt-10 border-t border-slate-200 pt-6 text-sm text-slate-500">
          <Link to="/login" className="font-medium text-navy-700 hover:underline">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  )
}
