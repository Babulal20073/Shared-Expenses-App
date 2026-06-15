import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import '../styles/Dashboard.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function DashboardPage({ user }: { user: any }) {
  const [groups, setGroups] = useState<any[]>([])
  const [showCreateGroup, setShowCreateGroup] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupDesc, setNewGroupDesc] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const token = localStorage.getItem('token')

  useEffect(() => {
    fetchGroups()
  }, [])

  const fetchGroups = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/groups`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setGroups(response.data)
    } catch (error) {
      console.error('Error fetching groups:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await axios.post(
        `${API_URL}/api/groups`,
        { name: newGroupName, description: newGroupDesc },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setNewGroupName('')
      setNewGroupDesc('')
      setShowCreateGroup(false)
      fetchGroups()
    } catch (error) {
      console.error('Error creating group:', error)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    window.location.reload()
  }

  const initials = (name: string) => name?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
  const displayName = user?.full_name || user?.username || 'User'

  if (loading) return (
    <div className="page-loading">
      <div className="spinner" />
      <span>Loading your groups…</span>
    </div>
  )

  return (
    <div className="dashboard">
      {/* ── Nav Header ── */}
      <header className="dashboard-header">
        <div className="dashboard-header-brand">
          <div className="header-logo">💸</div>
          <h1>SplitWise Pro</h1>
        </div>
        <div className="dashboard-header-right">
          <span className="header-welcome">Hi, {displayName.split(' ')[0]}!</span>
          <div className="header-avatar" title={displayName}>{initials(displayName)}</div>
          <button className="logout-btn" onClick={handleLogout}>Logout</button>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="dashboard-content">
        <div className="section-header">
          <div>
            <h2>Your Groups</h2>
            <p>{groups.length} shared expense group{groups.length !== 1 ? 's' : ''}</p>
          </div>
        </div>

        {groups.length === 0 ? (
          <div className="empty-groups">
            <span className="empty-groups-icon">🏠</span>
            <h3>No groups yet</h3>
            <p>Create a group and start splitting expenses with your flatmates or friends.</p>
            <button className="empty-create-btn" onClick={() => setShowCreateGroup(true)}>
              + Create your first group
            </button>
          </div>
        ) : (
          <div className="groups-grid">
            {groups.map((group) => (
              <div
                key={group.id}
                className="group-card"
                onClick={() => navigate(`/groups/${group.id}`)}
              >
                <div className="group-card-icon">🏠</div>
                <h3>{group.name}</h3>
                <p>{group.description || 'No description provided'}</p>
                <div className="group-card-footer">
                  <span className="group-created-date">
                    Created {new Date(group.created_at || Date.now()).toLocaleDateString()}
                  </span>
                  <span className="group-card-arrow">→</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* ── FAB ── */}
      <button
        id="create-group-fab"
        className="fab"
        onClick={() => setShowCreateGroup(true)}
        title="Create new group"
        aria-label="Create new group"
      >
        +
      </button>

      {/* ── Create Group Modal ── */}
      {showCreateGroup && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setShowCreateGroup(false) }}>
          <div className="modal-box">
            <div className="modal-header">
              <h2>Create New Group</h2>
              <button className="modal-close-btn" onClick={() => setShowCreateGroup(false)}>×</button>
            </div>

            <form onSubmit={handleCreateGroup}>
              <div className="modal-form-group">
                <label htmlFor="group-name">Group Name *</label>
                <input
                  id="group-name"
                  type="text"
                  placeholder="e.g. Spreetail Flatmates"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <div className="modal-form-group">
                <label htmlFor="group-desc">Description (optional)</label>
                <textarea
                  id="group-desc"
                  placeholder="What's this group for?"
                  value={newGroupDesc}
                  onChange={(e) => setNewGroupDesc(e.target.value)}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="modal-cancel-btn" onClick={() => setShowCreateGroup(false)}>
                  Cancel
                </button>
                <button type="submit" className="modal-create-btn">
                  Create Group →
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default DashboardPage
