import request from '@/utils/request'

export async function inspectDlis(formData) {
  const res = await request.post('/api/dlis/inspect', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000,
  })
  return res.data
}

export async function renderDlis(formData) {
  const res = await request.post('/api/dlis/render', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 600000,
  })
  return res.data
}
