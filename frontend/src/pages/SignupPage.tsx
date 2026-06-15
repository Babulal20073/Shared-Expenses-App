import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import axios from 'axios'
import '../styles/Auth.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function SignupPage({ setUser }: { setUser: (u: any) => void }) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await axios.post(`${API_URL}/api/auth/signup`, {
        username,
        email,
        password,
        full_name: fullName
      })
      localStorage.setItem('token', response.data.access_token)
      setUser(response.data.user)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Signup failed. Please try again.')
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
          Join in. Split<br /><span>fairly, always.</span>
        </h2>
        <p className="auth-hero-sub">
          Create your free account and start tracking shared expenses with your flatmates or group — with smart CSV import and instant settlements.
        </p>
        <ul className="auth-feature-list">
          <li>Upload CSV ledgers with 12+ anomaly fixes</li>
          <li>Interactive duplicate conflict resolution</li>
          <li>Equal, Unequal, Share & Percentage splits</li>
          <li>One-click minimal settlement calculator</li>
        </ul>
      </div>

      {/* Form Right Panel */}
      <div className="auth-right">
        <div className="auth-card">
          <div className="auth-card-header">
            <div className="auth-card-icon">✨</div>
            <h1>Create account</h1>
            <p>Get started in under 30 seconds</p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="signup-username">Username</label>
              <input
                id="signup-username"
                type="text"
                placeholder="e.g. aisha"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
              />
            </div>

            <div className="form-group">
              <label htmlFor="signup-fullname">Full Name</label>
              <input
                id="signup-fullname"
                type="text"
                placeholder="e.g. Aisha Khan"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
              />
            </div>

            <div className="form-group">
              <label htmlFor="signup-email">Email Address</label>
              <input
                id="signup-email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label htmlFor="signup-password">Password</label>
              <input
                id="signup-password"
                type="password"
                placeholder="Min. 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>

            {error && (
              <div className="auth-error">
                <span>⚠️</span>
                <span>{error}</span>
              </div>
            )}

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              {loading ? 'Creating account…' : 'Create Account →'}
            </button>
          </form>

          <div className="auth-footer">
            Already have an account? <Link to="/login">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SignupPage
