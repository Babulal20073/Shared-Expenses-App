import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const getToken = () => localStorage.getItem('token')

const getHeaders = (contentType = 'application/json') => ({
  headers: {
    Authorization: `Bearer ${getToken()}`,
    'Content-Type': contentType
  }
})

export const apiService = {
  // Auth
  login: (email: string, password: string) =>
    axios.post(`${API_URL}/api/auth/login`, { email, password }),

  signup: (userData: any) =>
    axios.post(`${API_URL}/api/auth/signup`, userData),

  getCurrentUser: () =>
    axios.get(`${API_URL}/api/auth/me`, getHeaders()),

  // Groups
  getGroups: () =>
    axios.get(`${API_URL}/api/groups`, getHeaders()),

  getGroup: (groupId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}`, getHeaders()),

  createGroup: (data: any) =>
    axios.post(`${API_URL}/api/groups`, data, getHeaders()),

  getMembersDetailed: (groupId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}/members-detailed`, getHeaders()),

  updateMemberTimeline: (groupId: string, userId: string, data: { joined_at: string; left_at: string | null }) =>
    axios.put(`${API_URL}/api/groups/${groupId}/members/${userId}/timeline`, data, getHeaders()),

  // Expenses
  getExpenses: (groupId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}/expenses`, getHeaders()),

  getMemberBreakdown: (groupId: string, userId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}/members/${userId}/breakdown`, getHeaders()),

  // Balances
  getBalances: (groupId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}/balances`, getHeaders()),

  getSettlementPlan: (groupId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}/balances/settlement`, getHeaders()),

  recordSettlement: (groupId: string, data: { from_user_id: string; to_user_id: string; amount: number; expense_date: string; notes?: string }) =>
    axios.post(`${API_URL}/api/groups/${groupId}/settlements`, data, getHeaders()),

  // Import
  parseCSV: (groupId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return axios.post(`${API_URL}/api/groups/${groupId}/parse-csv`, formData, getHeaders('multipart/form-data'))
  },

  importApprovedExpenses: (groupId: string, data: { expenses: any[]; anomalies: any[] }) =>
    axios.post(`${API_URL}/api/groups/${groupId}/import-csv`, data, getHeaders())
}
