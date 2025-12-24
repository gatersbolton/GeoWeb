import request from '@/utils/request'

// 运行地应力反演
export async function runStressInversion(formData) {
  const res = await request.post('/api/stressinv/run', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 1800000, // 30分钟，兼容同步接口的长耗时
  })
  return res.data
}

// 启动异步反演
export async function runStressInversionAsync(formData) {
  const res = await request.post('/api/stressinv/run_async', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 60000,
  })
  return res.data
}

// 查询进度
export async function getStressinvProgress(sessionId) {
  const res = await request.get(`/api/stressinv/progress/${sessionId}`, {
    timeout: 10000,
  })
  return res.data
}

// 获取结果（含下载链接）
export async function getStressinvResult(sessionId) {
  const res = await request.get(`/api/stressinv/result/${sessionId}`, {
    timeout: 10000,
  })
  return res.data
}


