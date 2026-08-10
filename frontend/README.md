# CEAP — CoAxn Enterprise AI Platform (Education Edition)

**Tagline:** The AI Operating System for Schools  
**Company:** CoAxn Technology

This is a **high-fidelity interactive prototype** (mock data only). It is **not** a school ERP / SIS / LMS clone. It is designed as an enterprise AI operating layer inspired by Microsoft Copilot, Notion AI, Glean, Atlassian, ServiceNow, and Salesforce Lightning.

## Run

```bash
cd ceap-education-platform
npm install
npm run dev
```

Open **http://localhost:5173**

### Demo login

- Email: `priya.sharma@greenwood.edu`
- Password: `demo123` (or any 4+ characters)

New emails go through **school onboarding**.

## Product architecture — 10 workspaces

| Workspace | Route | Purpose |
|-----------|-------|---------|
| Executive | `/` | Principal morning OS — briefing, KPIs, tasks, approvals, risk |
| Academic | `/academic` | Teaching & learning intelligence |
| Students | `/students` | Student 360 list + risk |
| Student 360 | `/students/:id` | Timeline, vault, fees, medical, AI plan |
| Admissions | `/admissions` | Pipeline kanban + AI scores |
| Finance | `/finance` | Revenue intelligence, defaulters, forecasts |
| HR | `/hr` | Workforce, leave approvals |
| Compliance | `/compliance` | Inspection readiness + evidence packs |
| Knowledge | `/knowledge` | Knowledge cards + relationships |
| School Memory | `/knowledge/memory` | Institutional decisions/meetings forever |
| AI Studio | `/ai` | Multi-agents + document types |
| Admin | `/admin` | Connectors, users, roles |

### Global operations

- **⌘K** — Command palette  
- **⌘J** / header **Copilot** — Persistent AI side panel  
- Tasks `/tasks` · Approvals `/approvals` · Calendar `/calendar`  
- Analytics `/analytics` · Workflows `/workflows`  
- Document Studio `/ai/studio` · Chat `/ai/chat`

## Design language

- Deep navy primary `#1E3A5F`
- Soft surfaces, cards, sparklines, insight banners
- Human-in-the-loop: AI never publishes alone
- Desktop-first, tablet usable

## Stack

React + Vite + Tailwind CSS v4 + React Router + Lucide icons · localStorage session
