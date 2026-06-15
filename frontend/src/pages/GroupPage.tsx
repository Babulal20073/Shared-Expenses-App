import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiService } from '../services/apiService'
import '../styles/Group.css'

interface Member {
  user_id: string
  username: string
  email: string
  full_name: string
  joined_at: string
  left_at: string | null
  is_active: boolean
}

interface ExpenseBreakdownItem {
  expense_id: string
  description: string
  amount: number
  currency: string
  amount_inr: number
  paid_by: string
  date: string
  your_share: number
  your_share_inr: number
  you_paid: boolean
  is_settlement: boolean
  notes: string | null
}

function GroupPage({ user }: { user: any }) {
  const { groupId } = useParams<{ groupId: string }>()
  const navigate = useNavigate()
  
  const [group, setGroup] = useState<any>(null)
  const [balances, setBalances] = useState<any[]>([])
  const [expenses, setExpenses] = useState<any[]>([])
  const [settlements, setSettlements] = useState<any[]>([])
  const [detailedMembers, setDetailedMembers] = useState<Member[]>([])
  const [activeTab, setActiveTab] = useState<'balances' | 'expenses' | 'settlements' | 'members'>('balances')
  const [loading, setLoading] = useState(true)

  // Breakdown Modal state
  const [selectedBreakdownMember, setSelectedBreakdownMember] = useState<any>(null)
  const [breakdownItems, setBreakdownItems] = useState<ExpenseBreakdownItem[]>([])
  const [showBreakdownModal, setShowBreakdownModal] = useState(false)

  // Settlement modal state
  const [showSettleModal, setShowSettleModal] = useState(false)
  const [settleSender, setSettleSender] = useState('')
  const [settleRecipient, setSettleRecipient] = useState('')
  const [settleAmount, setSettleAmount] = useState(0)
  const [settleDate, setSettleDate] = useState(new Date().toISOString().split('T')[0])
  const [settleNotes, setSettleNotes] = useState('')

  // Timeline Edit state
  const [editMemberId, setEditMemberId] = useState<string | null>(null)
  const [editJoinDate, setEditJoinDate] = useState('')
  const [editLeaveDate, setEditLeaveDate] = useState('')

  // CSV Import state
  const [showImport, setShowImport] = useState(false)
  const [importStep, setImportStep] = useState<'upload' | 'review' | 'success'>('upload')
  const [parsedExpenses, setParsedExpenses] = useState<any[]>([])
  const [parsedAnomalies, setParsedAnomalies] = useState<any[]>([])
  const [selectedRowIds, setSelectedRowIds] = useState<Set<string>>(new Set())
  const [duplicateResolution, setDuplicateResolution] = useState<Record<number, 'keep' | 'exclude'>>({})
  const [importLoading, setImportLoading] = useState(false)
  const [importReport, setImportReport] = useState<any>(null)

  useEffect(() => {
    if (groupId) {
      fetchGroupData()
    }
  }, [groupId])

  const fetchGroupData = async () => {
    if (!groupId) return
    setLoading(true)
    try {
      const [groupRes, balancesRes, expensesRes, settlementsRes, membersRes] = await Promise.all([
        apiService.getGroup(groupId),
        apiService.getBalances(groupId),
        apiService.getExpenses(groupId),
        apiService.getSettlementPlan(groupId),
        apiService.getMembersDetailed(groupId)
      ])

      setGroup(groupRes.data)
      setBalances(balancesRes.data)
      setExpenses(expensesRes.data)
      setSettlements(settlementsRes.data)
      setDetailedMembers(membersRes.data)
      
      // Default manual settlement dropdowns to first members
      if (membersRes.data.length >= 2) {
        setSettleSender(membersRes.data[0].user_id)
        setSettleRecipient(membersRes.data[1].user_id)
      }
    } catch (error) {
      console.error('Error fetching group data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle member breakdown click (Rohan's request)
  const handleMemberRowClick = async (member: any) => {
    if (!groupId) return
    try {
      const response = await apiService.getMemberBreakdown(groupId, member.user_id)
      setSelectedBreakdownMember(member)
      setBreakdownItems(response.data)
      setShowBreakdownModal(true)
    } catch (error) {
      console.error('Error fetching breakdown:', error)
    }
  }

  // Record Manual Payment
  const handleSettleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!groupId || !settleSender || !settleRecipient || settleAmount <= 0) return
    try {
      await apiService.recordSettlement(groupId, {
        from_user_id: settleSender,
        to_user_id: settleRecipient,
        amount: settleAmount,
        expense_date: settleDate,
        notes: settleNotes
      })
      setShowSettleModal(false)
      // Reset form
      setSettleAmount(0)
      setSettleNotes('')
      // Refresh
      fetchGroupData()
    } catch (error) {
      console.error('Error recording settlement:', error)
      alert('Failed to record settlement.')
    }
  }

  // Edit join/leave timeline
  const handleSaveTimeline = async (memberId: string) => {
    if (!groupId) return
    try {
      await apiService.updateMemberTimeline(groupId, memberId, {
        joined_at: new Date(editJoinDate).toISOString(),
        left_at: editLeaveDate ? new Date(editLeaveDate).toISOString() : null
      })
      setEditMemberId(null)
      fetchGroupData()
    } catch (error) {
      console.error('Error updating member timeline:', error)
      alert('Failed to update member timeline. Ensure date format is correct.')
    }
  }

  // Parse CSV
  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !groupId) return
    setImportLoading(true)
    try {
      const response = await apiService.parseCSV(groupId, file)
      const { parsed_expenses, anomalies } = response.data
      setParsedExpenses(parsed_expenses)
      setParsedAnomalies(anomalies)
      
      // Auto select all valid rows, group duplicates/conflicts
      const initialSelected = new Set<string>()
      const initialDupRes: Record<number, 'keep' | 'exclude'> = {}
      
      parsed_expenses.forEach((exp: any) => {
        if (exp.is_duplicate) {
          // Exclude duplicates by default
          initialDupRes[exp.csv_row_number] = 'exclude'
        } else {
          initialSelected.add(exp.id)
          initialDupRes[exp.csv_row_number] = 'keep'
        }
      })
      
      setSelectedRowIds(initialSelected)
      setDuplicateResolution(initialDupRes)
      setImportStep('review')
    } catch (error) {
      console.error('CSV Parsing Error:', error)
      alert('Failed to parse CSV. Please check formatting.')
    } finally {
      setImportLoading(false)
    }
  }

  // Toggle single row import inclusion
  const toggleRowSelection = (id: string, rowNum: number) => {
    const newSelected = new Set(selectedRowIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
      setDuplicateResolution(prev => ({ ...prev, [rowNum]: 'exclude' }))
    } else {
      newSelected.add(id)
      setDuplicateResolution(prev => ({ ...prev, [rowNum]: 'keep' }))
    }
    setSelectedRowIds(newSelected)
  }

  // Toggle duplicate resolution choice
  const setResolution = (exp: any, choice: 'keep' | 'exclude') => {
    setDuplicateResolution(prev => ({ ...prev, [exp.csv_row_number]: choice }))
    const newSelected = new Set(selectedRowIds)
    if (choice === 'keep') {
      newSelected.add(exp.id)
    } else {
      newSelected.delete(exp.id)
    }
    setSelectedRowIds(newSelected)
  }

  // Confirm Import (Submit Approved Rows to Backend)
  const confirmImport = async () => {
    if (!groupId) return
    setImportLoading(true)
    
    // Filter approved expenses
    const approvedExpenses = parsedExpenses.filter(exp => selectedRowIds.has(exp.id))
    
    // Map backend expected format
    const payload = {
      expenses: approvedExpenses.map(exp => ({
        description: exp.description,
        amount: exp.amount,
        currency: exp.currency,
        paid_by: exp.paid_by,
        split_type: exp.split_type,
        expense_date: exp.expense_date,
        split_with: exp.split_with,
        split_details: exp.split_details,
        notes: exp.notes,
        is_settlement: exp.is_settlement,
        csv_row_number: exp.csv_row_number
      })),
      anomalies: parsedAnomalies.map(a => ({
        row_number: a.row_number,
        field: a.field,
        issue: a.issue,
        original_value: a.original_value,
        action_taken: a.action_taken,
        severity: a.severity
      }))
    }

    try {
      const response = await apiService.importApprovedExpenses(groupId, payload)
      setImportReport(response.data)
      setImportStep('success')
    } catch (error) {
      console.error('Import confirmation error:', error)
      alert('Failed to finalize import.')
    } finally {
      setImportLoading(false)
    }
  }

  if (loading) return <div className="loading-container"><div className="loader"></div><p>Syncing ledger details...</p></div>

  const isCreator = group?.created_by === user?.id

  return (
    <div className="group-page">
      <header className="group-header">
        <div className="header-left">
          <button className="back-btn" onClick={() => navigate('/dashboard')}>← Back</button>
          <div className="title-section">
            <h1>{group?.name}</h1>
            <p className="group-desc">{group?.description || 'No description'}</p>
          </div>
        </div>
        <div className="header-right">
          <button className="settle-btn" onClick={() => setShowSettleModal(true)}>Record Settlement</button>
          <button className="import-btn" onClick={() => setShowImport(true)}>Import CSV</button>
        </div>
      </header>

      {/* Tabs */}
      <div className="tabs-nav">
        <button className={activeTab === 'balances' ? 'tab-btn active' : 'tab-btn'} onClick={() => setActiveTab('balances')}>Balances & Settlement Plan</button>
        <button className={activeTab === 'expenses' ? 'tab-btn active' : 'tab-btn'} onClick={() => setActiveTab('expenses')}>Expense History ({expenses.length})</button>
        <button className={activeTab === 'settlements' ? 'tab-btn active' : 'tab-btn'} onClick={() => setActiveTab('settlements')}>Settlements Log</button>
        <button className={activeTab === 'members' ? 'tab-btn active' : 'tab-btn'} onClick={() => setActiveTab('members')}>Group Members ({detailedMembers.length})</button>
      </div>

      <div className="group-content">
        
        {/* TAB 1: BALANCES & SETTLEMENT PLAN */}
        {activeTab === 'balances' && (
          <div className="dashboard-grid">
            <section className="balances-section glass-card">
              <h2>Balances</h2>
              <p className="helper-text">Click on any member to view their breakdown of dues (Rohan's view).</p>
              <div className="table-wrapper">
                <table className="interactive-table">
                  <thead>
                    <tr>
                      <th>Member</th>
                      <th>Owes (Share)</th>
                      <th>Owed (Paid)</th>
                      <th>Net Balance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {balances.map((balance) => {
                      const net = balance.net_balance
                      const isOwed = net < 0 // Negative net means owes < owed, i.e., they are owed back
                      return (
                        <tr key={balance.user_id} className="clickable-row" onClick={() => handleMemberRowClick(balance)}>
                          <td className="member-name-cell">
                            <strong>{balance.user_name}</strong>
                          </td>
                          <td className="amount-cell">₹{balance.owes_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                          <td className="amount-cell">₹{balance.owed_by_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                          <td className={`amount-cell net-cell ${isOwed ? 'owed-positive' : 'owes-negative'}`}>
                            {isOwed ? `Owed ₹${Math.abs(net).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : `Owes ₹${net.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="settlements-section glass-card">
              <h2>Settlement Plan (Aisha's View)</h2>
              <p className="helper-text">Optimized transactions to clear all group balances.</p>
              {settlements.length === 0 ? (
                <div className="settled-state">
                  <span className="party-popper">🎉</span>
                  <p>All group balances are settled! No payments required.</p>
                </div>
              ) : (
                <ul className="settlement-list">
                  {settlements.map((settlement, idx) => (
                    <li key={idx} className="settlement-card">
                      <div className="settlement-arrow">
                        <span className="from-user">{settlement.from_user}</span>
                        <span className="arrow">➔</span>
                        <span className="to-user">{settlement.to_user}</span>
                      </div>
                      <div className="settlement-val">₹{settlement.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}

        {/* TAB 2: EXPENSES LIST */}
        {activeTab === 'expenses' && (
          <section className="expenses-section glass-card">
            <h2>Expense History</h2>
            {expenses.filter(e => !e.is_settlement).length === 0 ? (
              <p className="empty-state">No shared expenses logged yet.</p>
            ) : (
              <div className="expenses-list">
                {expenses.filter(e => !e.is_settlement).map((expense) => (
                  <div key={expense.id} className="expense-item">
                    <div className="expense-left">
                      <span className="expense-icon">🛒</span>
                      <div>
                        <h4>{expense.description}</h4>
                        <p className="expense-meta">
                          Paid by <strong>{expense.paid_by_name || 'Group member'}</strong> on {new Date(expense.expense_date).toLocaleDateString()}
                          {expense.notes && <span className="notes-tag"> • {expense.notes}</span>}
                        </p>
                      </div>
                    </div>
                    <div className="expense-right">
                      <span className="currency-badge">{expense.currency}</span>
                      <span className="amount-text">
                        {expense.currency === 'USD' ? '$' : '₹'}
                        {expense.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </span>
                      {expense.currency !== 'INR' && (
                        <span className="converted-sub">
                          (₹{ExpenseService_get_inr_fallback(expense.amount, expense.currency).toLocaleString('en-IN', { minimumFractionDigits: 2 })})
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* TAB 3: SETTLEMENT LOG */}
        {activeTab === 'settlements' && (
          <section className="settlements-log-section glass-card">
            <h2>Settlements Log</h2>
            {expenses.filter(e => e.is_settlement).length === 0 ? (
              <p className="empty-state">No settlement payments recorded yet.</p>
            ) : (
              <div className="expenses-list">
                {expenses.filter(e => e.is_settlement).map((settlement) => (
                  <div key={settlement.id} className="expense-item settlement-log-item">
                    <div className="expense-left">
                      <span className="expense-icon">🤝</span>
                      <div>
                        <h4>{settlement.description}</h4>
                        <p className="expense-meta">
                          Recorded on {new Date(settlement.expense_date).toLocaleDateString()}
                          {settlement.notes && <span className="notes-tag"> • {settlement.notes}</span>}
                        </p>
                      </div>
                    </div>
                    <div className="expense-right">
                      <span className="settled-amount-text">
                        ₹{settlement.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* TAB 4: MEMBERS & TIMELINE PANEL */}
        {activeTab === 'members' && (
          <section className="members-section glass-card">
            <h2>Group Members Active Timelines</h2>
            <p className="helper-text">Manage member joined and left dates to adjust splitting eligibility (Sam & Meera's requests).</p>
            <div className="table-wrapper">
              <table className="members-table">
                <thead>
                  <tr>
                    <th>Full Name</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Active Join Date</th>
                    <th>Active Leave Date</th>
                    <th>Splitting Status</th>
                    {isCreator && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {detailedMembers.map((member) => {
                    const isEditing = editMemberId === member.user_id
                    return (
                      <tr key={member.user_id}>
                        <td><strong>{member.full_name}</strong></td>
                        <td>@{member.username}</td>
                        <td>{member.email}</td>
                        <td>
                          {isEditing ? (
                            <input
                              type="date"
                              value={editJoinDate}
                              className="timeline-date-input"
                              onChange={(e) => setEditJoinDate(e.target.value)}
                            />
                          ) : (
                            new Date(member.joined_at).toLocaleDateString()
                          )}
                        </td>
                        <td>
                          {isEditing ? (
                            <input
                              type="date"
                              value={editLeaveDate}
                              className="timeline-date-input"
                              onChange={(e) => setEditLeaveDate(e.target.value)}
                              placeholder="Ongoing"
                            />
                          ) : (
                            member.left_at ? new Date(member.left_at).toLocaleDateString() : 'Active Member (Ongoing)'
                          )}
                        </td>
                        <td>
                          <span className={`status-badge ${member.left_at ? 'inactive' : 'active'}`}>
                            {member.left_at ? 'Left Group' : 'Currently Active'}
                          </span>
                        </td>
                        {isCreator && (
                          <td>
                            {isEditing ? (
                              <div className="actions-wrapper">
                                <button className="save-btn" onClick={() => handleSaveTimeline(member.user_id)}>Save</button>
                                <button className="cancel-btn" onClick={() => setEditMemberId(null)}>Cancel</button>
                              </div>
                            ) : (
                              <button
                                className="edit-btn"
                                onClick={() => {
                                  setEditMemberId(member.user_id)
                                  setEditJoinDate(member.joined_at.split('T')[0])
                                  setEditLeaveDate(member.left_at ? member.left_at.split('T')[0] : '')
                                }}
                              >
                                Edit Timeline
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>

      {/* ===== MODAL 1: MEMBER DUES BREAKDOWN (Rohan's Request) ===== */}
      {showBreakdownModal && selectedBreakdownMember && (
        <div className="modal-overlay">
          <div className="modal-box breakdown-modal glass-card animate-slide">
            <header className="modal-header">
              <h3>Dues Breakdown for {selectedBreakdownMember.user_name}</h3>
              <button className="close-btn" onClick={() => setShowBreakdownModal(false)}>×</button>
            </header>
            <div className="modal-body">
              <div className="summary-cards">
                <div className="summary-card debt">
                  <span className="card-label">Total Share of Expenses</span>
                  <span className="card-value">₹{selectedBreakdownMember.owes_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="summary-card credit">
                  <span className="card-label">Total Amount Paid</span>
                  <span className="card-value">₹{selectedBreakdownMember.owed_by_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="summary-card net">
                  <span className="card-label">Net Balance</span>
                  <span className={`card-value ${selectedBreakdownMember.net_balance < 0 ? 'net-credit' : 'net-debt'}`}>
                    {selectedBreakdownMember.net_balance < 0 ? `Owed ₹${Math.abs(selectedBreakdownMember.net_balance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : `Owes ₹${selectedBreakdownMember.net_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
                  </span>
                </div>
              </div>

              <h4>Ledger Details</h4>
              <div className="table-wrapper">
                <table className="breakdown-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Payer</th>
                      <th>Total Expense</th>
                      <th>Your Share</th>
                      <th>Math Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {breakdownItems.map((item, idx) => {
                      const amountText = item.currency === 'USD' ? `$${item.amount}` : `₹${item.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                      const shareText = item.currency === 'USD' ? `$${item.your_share}` : `₹${item.your_share.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                      return (
                        <tr key={idx} className={item.is_settlement ? 'settlement-row' : ''}>
                          <td>{new Date(item.date).toLocaleDateString()}</td>
                          <td>
                            <strong>{item.description}</strong>
                            {item.is_settlement && <span className="settle-badge">Settlement Payment</span>}
                            {item.notes && <span className="notes-meta">({item.notes})</span>}
                          </td>
                          <td>{item.paid_by}</td>
                          <td>
                            {amountText}
                            {item.currency !== 'INR' && <div className="inr-converted-sub">(₹{item.amount_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })})</div>}
                          </td>
                          <td>
                            {item.you_paid ? (
                              <span className="credit-text">
                                +{shareText} Paid
                                {item.currency !== 'INR' && <div className="inr-converted-sub">(+₹{item.your_share_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })})</div>}
                              </span>
                            ) : (
                              <span className="debt-text">
                                -{shareText} Share
                                {item.currency !== 'INR' && <div className="inr-converted-sub">(-₹{item.your_share_inr.toLocaleString('en-IN', { minimumFractionDigits: 2 })})</div>}
                              </span>
                            )}
                          </td>
                          <td>{item.is_settlement ? 'Settlement' : item.you_paid ? 'Paid full' : 'Split share'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===== MODAL 2: RECORD SETTLEMENT MODAL ===== */}
      {showSettleModal && (
        <div className="modal-overlay">
          <div className="modal-box settle-modal glass-card animate-slide">
            <header className="modal-header">
              <h3>Record Settlement Payment</h3>
              <button className="close-btn" onClick={() => setShowSettleModal(false)}>×</button>
            </header>
            <form onSubmit={handleSettleSubmit} className="modal-body">
              <div className="form-group">
                <label>Who Paid? (Sender)</label>
                <select value={settleSender} onChange={(e) => setSettleSender(e.target.value)}>
                  {detailedMembers.map(m => (
                    <option key={m.user_id} value={m.user_id}>{m.full_name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Who Received? (Recipient)</label>
                <select value={settleRecipient} onChange={(e) => setSettleRecipient(e.target.value)}>
                  {detailedMembers.map(m => (
                    <option key={m.user_id} value={m.user_id} disabled={m.user_id === settleSender}>{m.full_name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Amount (₹ INR)</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  placeholder="0.00"
                  value={settleAmount || ''}
                  onChange={(e) => setSettleAmount(parseFloat(e.target.value))}
                />
              </div>

              <div className="form-group">
                <label>Date</label>
                <input
                  type="date"
                  required
                  value={settleDate}
                  onChange={(e) => setSettleDate(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Notes / Memo</label>
                <input
                  type="text"
                  placeholder="e.g. Paid back share of Feb Rent"
                  value={settleNotes}
                  onChange={(e) => setSettleNotes(e.target.value)}
                />
              </div>

              <div className="form-actions">
                <button type="button" className="secondary-btn" onClick={() => setShowSettleModal(false)}>Cancel</button>
                <button type="submit" className="primary-btn">Record Payment</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===== MODAL 3: INTERACTIVE MULTI-STEP CSV IMPORT (Meera's Request) ===== */}
      {showImport && (
        <div className="modal-overlay">
          <div className="modal-box import-modal glass-card animate-slide">
            <header className="modal-header">
              <h3>Import Expenses CSV Ledger</h3>
              <button className="close-btn" onClick={() => {
                setShowImport(false)
                setImportStep('upload')
                fetchGroupData()
              }}>×</button>
            </header>
            
            {importStep === 'upload' && (
              <div className="modal-body import-upload-step">
                <div className="upload-dropzone">
                  <span className="upload-icon">📥</span>
                  <p>Drag and drop or select your CSV file to begin parsing</p>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleCSVUpload}
                    disabled={importLoading}
                  />
                </div>
                {importLoading && <div className="loader-inline">Parsing ledger sheets...</div>}
              </div>
            )}

            {importStep === 'review' && (
              <div className="modal-body import-review-step">
                <div className="review-header">
                  <div className="stats">
                    <span className="stat-badge total">Total Rows: {parsedExpenses.length}</span>
                    <span className="stat-badge anomalies">Anomalies: {parsedAnomalies.length}</span>
                  </div>
                  <p className="helper-text">Verify parsed details. Red highlights represent duplicate double entries; adjust and click confirm below (Meera's Review screen).</p>
                </div>

                {/* Anomalies Log */}
                <div className="anomalies-log">
                  <h4>Anomalies Ingest Report ({parsedAnomalies.length})</h4>
                  <div className="anomalies-list-inner">
                    {parsedAnomalies.map((a, idx) => (
                      <div key={idx} className={`anomaly-item-card ${a.severity}`}>
                        <div className="anomaly-meta">
                          <span className="row-badge">Row {a.row_number}</span>
                          <span className="severity-badge">{a.severity.toUpperCase()}</span>
                          <span className="field-badge">{a.field}</span>
                        </div>
                        <p className="issue-desc"><strong>Issue:</strong> {a.issue}</p>
                        <p className="action-taken"><strong>Action Taken:</strong> {a.action_taken}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Parsed Entries Table */}
                <div className="parsed-table-wrapper">
                  <h4>Parsed Entries Review</h4>
                  <table className="parsed-review-table">
                    <thead>
                      <tr>
                        <th>Import</th>
                        <th>Row</th>
                        <th>Date</th>
                        <th>Description</th>
                        <th>Payer</th>
                        <th>Amount</th>
                        <th>Currency</th>
                        <th>Split Type</th>
                        <th>Participants</th>
                        <th>Conflict/Duplicate Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {parsedExpenses.map((exp) => {
                        const isDup = exp.is_duplicate || exp.is_conflict
                        const isSelected = selectedRowIds.has(exp.id)
                        return (
                          <tr key={exp.id} className={isDup ? 'duplicate-row-highlight' : ''}>
                            <td>
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleRowSelection(exp.id, exp.csv_row_number)}
                              />
                            </td>
                            <td>{exp.csv_row_number}</td>
                            <td>{new Date(exp.expense_date).toLocaleDateString()}</td>
                            <td>
                              <strong>{exp.description}</strong>
                              {exp.is_settlement && <span className="settle-badge">Settlement</span>}
                            </td>
                            <td>{exp.paid_by}</td>
                            <td>
                              {exp.amount.toLocaleString()}
                              {exp.currency !== 'INR' && <div className="inr-converted-sub">(₹{exp.amount_inr.toLocaleString()})</div>}
                            </td>
                            <td>{exp.currency}</td>
                            <td>{exp.split_type}</td>
                            <td>
                              <div className="participants-list">
                                {exp.split_with.map((name: string) => (
                                  <span key={name} className="participant-tag">{name}</span>
                                ))}
                              </div>
                            </td>
                            <td>
                              {exp.is_duplicate && (
                                <div className="dup-action-controls">
                                  <span className="warning-text">Duplicate of Row {exp.duplicate_of}</span>
                                  <div className="btn-toggle">
                                    <button
                                      type="button"
                                      className={duplicateResolution[exp.csv_row_number] === 'keep' ? 'small-btn active' : 'small-btn'}
                                      onClick={() => setResolution(exp, 'keep')}
                                    >
                                      Import
                                    </button>
                                    <button
                                      type="button"
                                      className={duplicateResolution[exp.csv_row_number] === 'exclude' ? 'small-btn active' : 'small-btn'}
                                      onClick={() => setResolution(exp, 'exclude')}
                                    >
                                      Exclude
                                    </button>
                                  </div>
                                </div>
                              )}
                              {exp.is_conflict && (
                                <div className="dup-action-controls">
                                  <span className="conflict-text">Conflict with Row {exp.conflict_with}</span>
                                  <div className="btn-toggle">
                                    <button
                                      type="button"
                                      className={duplicateResolution[exp.csv_row_number] === 'keep' ? 'small-btn active' : 'small-btn'}
                                      onClick={() => setResolution(exp, 'keep')}
                                    >
                                      Keep
                                    </button>
                                    <button
                                      type="button"
                                      className={duplicateResolution[exp.csv_row_number] === 'exclude' ? 'small-btn active' : 'small-btn'}
                                      onClick={() => setResolution(exp, 'exclude')}
                                    >
                                      Exclude
                                    </button>
                                  </div>
                                </div>
                              )}
                              {!exp.is_duplicate && !exp.is_conflict && <span className="ok-badge">OK</span>}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="form-actions">
                  <button type="button" className="secondary-btn" onClick={() => setImportStep('upload')}>Back</button>
                  <button type="button" className="primary-btn" onClick={confirmImport} disabled={importLoading}>
                    {importLoading ? 'Importing...' : `Confirm Import (${selectedRowIds.size} rows)`}
                  </button>
                </div>
              </div>
            )}

            {importStep === 'success' && (
              <div className="modal-body import-success-step">
                <div className="success-banner">
                  <span className="success-icon">✅</span>
                  <h3>Import Complete!</h3>
                  <p>Successfully processed ledger sheets and resolved database entities.</p>
                </div>
                <div className="import-summary-details">
                  <p><strong>Total rows imported:</strong> {importReport?.successful_imports || selectedRowIds.size}</p>
                  <p><strong>Report Log ID:</strong> <code>{importReport?.import_id || importReport?.report_id}</code></p>
                </div>
                <div className="form-actions">
                  <button
                    type="button"
                    className="primary-btn"
                    onClick={() => {
                      setShowImport(false)
                      setImportStep('upload')
                      fetchGroupData()
                    }}
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  )
}

// Fallback currency conversion helper for rendering
function ExpenseService_get_inr_fallback(amount: number, currency: string) {
  if (currency === 'USD') return amount * 84.5
  if (currency === 'EUR') return amount * 91.0
  return amount
}

export default GroupPage
