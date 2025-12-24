import request from '@/utils/request'

export async function sumCsv(formData) {
  const res = await request.post('/api/csv/sum', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return res.data
} 