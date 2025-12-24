import request from '@/utils/request'

// 计算钻孔椭圆度
export async function calculateBoreholeEllipticity(formData) {
  const res = await request.post('/api/borehole/calculate', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000, // 5分钟超时，因为处理可能需要较长时间
  })
  return res.data
}

// 生成可视化图表
export async function visualizeBoreholeEllipticity(formData) {
  const res = await request.post('/api/borehole/visualize', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000, // 5分钟超时，因为处理可能需要较长时间
  })
  return res.data
}

// 兼容旧的API调用（暂时保留）
export async function processBoreholeEllipticity(formData) {
  const res = await request.post('/api/borehole/process', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000, // 5分钟超时，因为处理可能需要较长时间
  })
  return res.data
} 