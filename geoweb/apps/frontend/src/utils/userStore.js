import { ref } from 'vue'

const username = ref(localStorage.getItem('username') || '')

export function useUserStore() {
  return { username }
}

export function setUsername(value) {
  const next = (value || '').trim()
  username.value = next
  if (next) {
    localStorage.setItem('username', next)
  } else {
    localStorage.removeItem('username')
  }
}

export function clearUser() {
  username.value = ''
  localStorage.removeItem('username')
}
