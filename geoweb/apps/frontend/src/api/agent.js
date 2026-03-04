import request from '@/utils/request'

export async function listAgentTools() {
  const res = await request.get('/api/agent/tools')
  return res.data
}

export async function getAgentRuntime() {
  const res = await request.get('/api/agent/runtime')
  return res.data
}

export async function recommendAgent(payload) {
  const res = await request.post('/api/agent/recommend', payload, {
    timeout: 60000,
  })
  return res.data
}

export async function chatAgent(formData) {
  const res = await request.post('/api/agent/chat', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 600000,
  })
  return res.data
}
