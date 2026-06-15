import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import '../styles/Group.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function GroupPage({ user }) {
  const { groupId } = useParams<{ groupId: string }>()
  const [group, setGroup] = useState(null)
  const [balances, setBalances] = useState([])
  const [expenses, setExpenses] = useState([])
  const [settlements, setSettlements] = useState([])
  const [showImport, setShowImport] = useState(false)
  const [loading, setLoading] = useState(true)

  const token = localStorage.getItem('token')

  useEffect(() => {
    fetchGroupData()
  }, [groupId])

  const fetchGroupData = async () => {
    try {
      const [groupRes, balancesRes, expensesRes, settlementsRes] = await Promise.all([
        axios.get(`${API_URL}/api/groups/${groupId}`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/groups/${groupId}/balances`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/groups/${groupId}/expenses`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/groups/${groupId}/balances/settlement`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ])

      setGroup(groupRes.data)
      setBalances(balancesRes.data)
      setExpenses(expensesRes.data)
      setSettlements(settlementsRes.data)
    } catch (error) {
      console.error('Error fetching group data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      await axios.post(
        `${API_URL}/api/groups/${groupId}/import-csv`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      )
      setShowImport(false)
      fetchGroupData()
    } catch (error) {
      console.error('Error importing CSV:', error)
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div className="group-page">
      <header className="group-header">
        <h1>{group?.name}</h1>
        <button onClick={() => window.history.back()}>Back</button>
      </header>

      <div className="group-content">
        <section className="balances-section">
          <h2>Balances</h2>
          <div className="balances-table">
            <table>
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Owes</th>
                  <th>Owed</th>
                  <th>Net</th>
                </tr>
              </thead>
              <tbody>
                {balances.map((balance) => (
                  <tr key={balance.user_id}>
                    <td>{balance.user_name}</td>
                    <td>₹{balance.owes_amount}</td>
                    <td>₹{balance.owed_by_amount}</td>
                    <td className={balance.net_balance > 0 ? 'owes' : 'owed'}>
                      ₹{Math.abs(balance.net_balance)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="settlements-section">
          <h2>Settlement Plan</h2>
          {settlements.length === 0 ? (
            <p>All settled!</p>
          ) : (
            <ul>
              {settlements.map((settlement, idx) => (
                <li key={idx}>
                  {settlement.from_user} pays ₹{settlement.amount} to {settlement.to_user}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="expenses-section">
          <h2>Recent Expenses ({expenses.length})</h2>
          {expenses.length === 0 ? (
            <p>No expenses yet</p>
          ) : (
            <div className="expenses-list">
              {expenses.map((expense) => (
                <div key={expense.id} className="expense-item">
                  <div>
                    <h4>{expense.description}</h4>
                    <p className="date">
                      {new Date(expense.expense_date).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="amount">₹{expense.amount}</div>
                </div>
              ))}
            </div>
          )}
        </section>

        {showImport && (
          <div className="modal">
            <div className="modal-content">
              <h2>Import Expenses CSV</h2>
              <input
                type="file"
                accept=".csv"
                onChange={handleImport}
              />
              <button onClick={() => setShowImport(false)}>Cancel</button>
            </div>
          </div>
        )}

        <button
          className="fab"
          onClick={() => setShowImport(true)}
          title="Import CSV"
        >
          📤
        </button>
      </div>
    </div>
  )
}

export default GroupPage
