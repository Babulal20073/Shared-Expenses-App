import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import '../styles/Dashboard.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function DashboardPage({ user }) {
  const [groups, setGroups] = useState([])
  const [showCreateGroup, setShowCreateGroup] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
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
        { name: newGroupName },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setNewGroupName('')
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

  if (loading) return <div>Loading...</div>

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Shared Expenses</h1>
        <div>
          <span>Welcome, {user.full_name || user.username}</span>
          <button onClick={handleLogout}>Logout</button>
        </div>
      </header>

      <div className="dashboard-content">
        <section className="groups-section">
          <h2>Your Groups</h2>
          {groups.length === 0 ? (
            <p>No groups yet. Create one to get started!</p>
          ) : (
            <div className="groups-grid">
              {groups.map((group) => (
                <div
                  key={group.id}
                  className="group-card"
                  onClick={() => navigate(`/groups/${group.id}`)}
                >
                  <h3>{group.name}</h3>
                  <p>{group.description}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {showCreateGroup && (
          <div className="modal">
            <div className="modal-content">
              <h2>Create New Group</h2>
              <form onSubmit={handleCreateGroup}>
                <div className="form-group">
                  <label>Group Name</label>
                  <input
                    type="text"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                    required
                  />
                </div>
                <button type="submit">Create</button>
                <button
                  type="button"
                  onClick={() => setShowCreateGroup(false)}
                >
                  Cancel
                </button>
              </form>
            </div>
          </div>
        )}

        <button
          className="fab"
          onClick={() => setShowCreateGroup(true)}
          title="Create new group"
        >
          +
        </button>
      </div>
    </div>
  )
}

export default DashboardPage
