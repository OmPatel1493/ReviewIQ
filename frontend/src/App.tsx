import type { ReactNode } from 'react'
import { Route, Routes } from 'react-router-dom'
import DashboardLayout from '@/components/DashboardLayout'
import DashboardPage from '@/pages/DashboardPage'
import {
  AskCard,
  BackendCard,
  ReviewCard,
  RoadmapCard,
  SearchCard,
} from '@/components/cards'

function ToolPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
      {children}
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route index element={<DashboardPage />} />
        <Route
          path="search"
          element={
            <ToolPage title="Semantic search">
              <SearchCard />
            </ToolPage>
          }
        />
        <Route
          path="review"
          element={
            <ToolPage title="AI pull-request review">
              <ReviewCard />
            </ToolPage>
          }
        />
        <Route
          path="ask"
          element={
            <ToolPage title="Ask AI">
              <AskCard />
            </ToolPage>
          }
        />
        <Route
          path="status"
          element={
            <ToolPage title="System status">
              <div className="grid gap-6 md:grid-cols-2">
                <BackendCard />
                <RoadmapCard />
              </div>
            </ToolPage>
          }
        />
        <Route path="*" element={<DashboardPage />} />
      </Route>
    </Routes>
  )
}
