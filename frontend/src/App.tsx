import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect, type ReactNode } from 'react'
import Navbar from './components/Navbar'
import LandingPage from './pages/LandingPage'
import HomePage from './pages/HomePage'
import ProfessorsPage from './pages/ProfessorsPage'
import ProfessorDetailPage from './pages/ProfessorDetailPage'
import CoursesPage from './pages/CoursesPage'
import CourseDetailPage from './pages/CourseDetailPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import BindEmailPage from './pages/BindEmailPage'
import GuidelinesPage from './pages/GuidelinesPage'
import { AuthProvider, useAuth } from './contexts/AuthContext'

function ScrollToTop() {
  const location = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [location.pathname, location.search])

  return null
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div className="py-20 text-center text-gray-400">Yükleniyor...</div>
  }

  if (!user) {
    const from = `${location.pathname}${location.search}${location.hash}`
    return <Navigate to="/login" replace state={{ from }} />
  }

  return children
}

function HomeOrLanding() {
  const { user, loading } = useAuth()
  if (loading) return <div className="py-20 text-center text-gray-400">Yükleniyor...</div>
  return user ? <HomePage /> : <LandingPage />
}

function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="py-20 text-center text-gray-400">Yükleniyor...</div>
  }

  if (user) {
    return <Navigate to="/" replace />
  }

  return children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-cream flex flex-col">
          <ScrollToTop />
          <Navbar />
          <main className="flex-1 pb-16">
            <Routes>
              <Route
                path="/login"
                element={(
                  <RedirectIfAuthenticated>
                    <LoginPage />
                  </RedirectIfAuthenticated>
                )}
              />
              <Route
                path="/register"
                element={(
                  <RedirectIfAuthenticated>
                    <RegisterPage />
                  </RedirectIfAuthenticated>
                )}
              />
              <Route
                path="/forgot-password"
                element={(
                  <RedirectIfAuthenticated>
                    <ForgotPasswordPage />
                  </RedirectIfAuthenticated>
                )}
              />
              <Route
                path="/"
                element={<HomeOrLanding />}
              />
              <Route
                path="/professors"
                element={(
                  <RequireAuth>
                    <ProfessorsPage />
                  </RequireAuth>
                )}
              />
              <Route
                path="/professors/:id"
                element={(
                  <RequireAuth>
                    <ProfessorDetailPage />
                  </RequireAuth>
                )}
              />
              <Route
                path="/courses"
                element={(
                  <RequireAuth>
                    <CoursesPage />
                  </RequireAuth>
                )}
              />
              <Route
                path="/courses/:id"
                element={(
                  <RequireAuth>
                    <CourseDetailPage />
                  </RequireAuth>
                )}
              />
              <Route
                path="/account/bind-email"
                element={(
                  <RequireAuth>
                    <BindEmailPage />
                  </RequireAuth>
                )}
              />
              <Route
                path="/guidelines"
                element={(
                  <RequireAuth>
                    <GuidelinesPage />
                  </RequireAuth>
                )}
              />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}
