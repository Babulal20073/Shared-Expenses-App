import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const getToken = () => localStorage.getItem('token')

export const apiService = {
  // Auth
  login: (email: string, password: string) =>
    axios.post(`${API_URL}/api/auth/login`, { email, password }),

  signup: (userData: any) =>
    axios.post(`${API_URL}/api/auth/signup`, userData),

  getCurrentUser: () =>
    axios.get(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    }),

  // Groups
  getGroups: () =>
    axios.get(`${API_URL}/api/groups`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    }),

  getGroup: (groupId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    }),

  createGroup: (data: any) =>
    axios.post(`${API_URL}/api/groups`, data, {
      headers: { Authorization: `Bearer ${getToken()}` }
    }),

  // Expenses
  getExpenses: (groupId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}/expenses`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    }),

  // Balances
  getBalances: (groupId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}/balances`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    }),

  getSettlementPlan: (groupId: string) =>
    axios.get(`${API_URL}/api/groups/${groupId}/balances/settlement`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    }),

  // Import
  importCSV: (groupId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return axios.post(`${API_URL}/api/groups/${groupId}/import-csv`, formData, {
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}
