// API client for backend communication

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// TODO: Implement API calls when backend is ready
const api = {
  // Convert PDF files to structured JSON
  async convertFiles(files) {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    const response = await fetch(`${API_BASE_URL}/convert`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return await response.json()
  },

  // Health check endpoint
  async healthCheck() {
    const response = await fetch(`${API_BASE_URL}/health`)
    return await response.json()
  },
}

export default api
