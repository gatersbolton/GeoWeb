import request from '@/utils/request'

export function getUserList() {
  return request.get('/user/list')
}

export function registerUser(data) {
  return request.post('/user/register', data)
}

export function loginUser(data) {
  return request.post('/user/login', data)
}

export function updateUser(data) {
  return request.put('/user/update', data)
}

export function deleteUser(id) {
  return request.delete(`/user/delete/${id}`)
}

export const addUser = registerUser; 

export function getUserProfile(username) {
  return request.get('/user/profile', { params: { username } })
}

export function updateUserProfile(data) {
  return request.put('/user/profile', data)
}

export function updateUserPassword(data) {
  return request.put('/user/password', data)
}
