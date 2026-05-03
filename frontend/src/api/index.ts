import client from './client'
import type {
  Professor, ProfessorDetail, Course, CourseListResponse, Review, SearchResult, UpvoteStatus, ReviewCreate, ReviewUpdate, Faculty,
  HomeStats, LeaderboardStats, SemesterOption,
} from '../types'

// ── Professors ─────────────────────────────────────────────────────────────

export interface ProfessorListParams {
  department?: string
  faculty?: Faculty
  q?: string
  semester?: string
  skip?: number
  limit?: number
}

export const getProfessors = (params: ProfessorListParams = {}) =>
  client.get<Professor[]>('/professors', { params }).then(r => r.data)

export async function getAllProfessors(
  params: Omit<ProfessorListParams, 'skip' | 'limit'> = {},
) {
  const limit = 200
  let skip = 0
  const items: Professor[] = []

  while (true) {
    const page = await getProfessors({ ...params, skip, limit })
    items.push(...page)

    if (page.length < limit) {
      return items
    }

    skip += page.length
  }
}

export const getProfessor = (id: number, params: { semester?: string } = {}) =>
  client.get<ProfessorDetail>(`/professors/${id}`, { params }).then(r => r.data)

export const getProfessorCourses = (id: number) =>
  client.get(`/professors/${id}/courses`).then(r => r.data)

export const getProfessorReviews = (id: number, params: { semester?: string } = {}) =>
  client.get<Review[]>(`/professors/${id}/reviews`, { params }).then(r => r.data)

// ── Courses ────────────────────────────────────────────────────────────────

export interface CourseListParams {
  department?: string
  faculty?: Faculty
  q?: string
  min_difficulty?: number
  max_difficulty?: number
  max_workload?: number
  semester?: string
  skip?: number
  limit?: number
}

export const getCoursesPage = (params: CourseListParams = {}) =>
  client.get<CourseListResponse>('/courses', { params }).then(r => r.data)

export async function getAllCourses(params: Omit<CourseListParams, 'skip' | 'limit'> = {}) {
  const limit = 200
  let skip = 0
  const items: Course[] = []

  while (true) {
    const page = await getCoursesPage({ ...params, skip, limit })
    items.push(...page.items)

    if (!page.has_more || page.items.length === 0) {
      return items
    }

    skip += page.items.length
  }
}

export const getCourse = (id: number, params: { semester?: string } = {}) =>
  client.get(`/courses/${id}`, { params }).then(r => r.data)

export const getCourseReviews = (id: number, params: { semester?: string } = {}) =>
  client.get<Review[]>(`/courses/${id}/reviews`, { params }).then(r => r.data)

// ── Reviews ────────────────────────────────────────────────────────────────
export const createReview = (data: ReviewCreate) =>
  client.post<Review>('/reviews', data).then(r => r.data)

export const updateReview = (reviewId: number, data: ReviewUpdate) =>
  client.put<Review>(`/reviews/${reviewId}`, data).then(r => r.data)

export const deleteReview = (reviewId: number) =>
  client.delete(`/reviews/${reviewId}`).then(r => r.data)

export const toggleUpvote = (reviewId: number) =>
  client.post<UpvoteStatus>(`/reviews/${reviewId}/upvote`).then(r => r.data)

export const toggleDownvote = (reviewId: number) =>
  client.post<UpvoteStatus>(`/reviews/${reviewId}/downvote`).then(r => r.data)

// ── Search ─────────────────────────────────────────────────────────────────
export const search = (q: string) =>
  client.get<SearchResult>('/search', { params: { q } }).then(r => r.data)

// ── Stats (HomePage aggregate) ─────────────────────────────────────────────
export const getHomeStats = () =>
  client.get<HomeStats>('/stats/home').then(r => r.data)

export const getLeaderboard = (params: { semester?: string; limit?: number } = {}) =>
  client.get<LeaderboardStats>('/stats/leaderboard', { params }).then(r => r.data)

export const getSemesters = () =>
  client.get<SemesterOption[]>('/stats/semesters').then(r => r.data)

// ── Auth ───────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string
  first_name: string | null
  last_name: string | null
  username: string
  email: string | null
  has_email: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export interface RegisterStartPayload {
  first_name: string
  last_name: string
  email: string
  password: string
}

export interface RegisterStartResponse {
  message: string
  expires_at: string
}

export interface OtpStartResponse {
  message: string
  expires_at: string
}

export interface MessageResponse {
  message: string
}

export const registerStart = (data: RegisterStartPayload) =>
  client.post<RegisterStartResponse>('/auth/register/start', data).then(r => r.data)

export const registerVerify = (data: { email: string; otp: string }) =>
  client.post<TokenResponse>('/auth/register/verify', data).then(r => r.data)

export const login = (data: { identifier: string; password: string }) =>
  client.post<TokenResponse>('/auth/login', data).then(r => r.data)

export const getMe = () => client.get<AuthUser>('/me').then(r => r.data)

export const forgotPassword = (data: { email: string }) =>
  client.post<OtpStartResponse>('/auth/password/forgot', data).then(r => r.data)

export const resetPassword = (data: { email: string; otp: string; new_password: string }) =>
  client.post<MessageResponse>('/auth/password/reset', data).then(r => r.data)

export const startEmailBind = (data: { email: string }) =>
  client.post<OtpStartResponse>('/auth/email/bind/start', data).then(r => r.data)

export const verifyEmailBind = (data: { email: string; otp: string }) =>
  client.post<MessageResponse>('/auth/email/bind/verify', data).then(r => r.data)
