import axios from 'axios'

// 创建 axios 实例，可根据需要自定义
const request = axios.create({
  baseURL: '/', // 根据后端地址调整
  timeout: 10000,
})

export default request 