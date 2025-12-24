import request from '@/utils/request'

export async function runAugmentation(formData) {
  const res = await request.post('/api/augmentation/run', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000,
  })
  return res.data
}
