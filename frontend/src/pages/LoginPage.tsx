import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'
import '../styles/Auth.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function LoginPage({ setUser }: { setUser: (u: any) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await axios.post(`${API_URL}/api/auth/login`, { email, password })
      localStorage.setItem('token', response.data.access_token)
      setUser(response.data.user)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      {/* Hero Left Panel */}
      <div className="auth-left">
        <div className="auth-brand">
          <div className="auth-brand-icon">💸</div>
          <span className="auth-brand-name">SplitWise Pro</span>
        </div>
        <h2 className="auth-hero-headline">
          Track. Split.<br /><span>Stay balanced.</span>
        </h2>
        <p className="auth-hero-sub">
          A smarter way to manage shared expenses. Import CSV ledgers, resolve conflicts, and settle debts — all in one place.
        </p>
        <ul className="auth-feature-list">
          <li>Smart CSV import with anomaly detection</li>
          <li>Multi-currency support (INR, USD, EUR)</li>
          <li>Minimal settlement plan calculator</li>
          <li>Member active timeline management</li>
        </ul>
      </div>

      {/* Form Right Panel */}
      <div className="auth-right">
        <div className="auth-card">
          <div className="auth-card-header">
            <div className="auth-card-icon">🔐</div>
            <h1>Welcome back</h1>
            <p>Sign in to your account to continue</p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="login-email">Email Address</label>
              <input
                id="login-email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div className="auth-error">
                <span>⚠️</span>
                <span>{error}</span>
              </div>
            )}

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In →'}
            </button>
          </form>

          <div className="auth-footer">
            Don't have an account? <Link to="/signup">Create one free</Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
