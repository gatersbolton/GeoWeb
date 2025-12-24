<template>
  <div class="profile-page">
    <el-card class="profile-card" shadow="hover" v-loading="loadingProfile">
      <template #header>
        <div class="card-header">
          <span>个人资料</span>
          <el-tag v-if="profileForm.username" type="success" effect="plain">已登录</el-tag>
        </div>
      </template>

      <el-descriptions class="profile-meta" :column="2" size="small" border>
        <el-descriptions-item label="账号ID">
          {{ profileMeta.id || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ profileMeta.createTime || '-' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <el-form
        ref="profileFormRef"
        :model="profileForm"
        :rules="profileRules"
        label-width="90px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="profileForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="profileForm.email" autocomplete="off" />
        </el-form-item>
        <el-form-item>
          <div class="form-actions">
            <el-button type="primary" :loading="savingProfile" @click="saveProfile">
              保存修改
            </el-button>
            <el-button :disabled="loadingProfile" @click="resetProfile">
              重置
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="profile-card" shadow="hover">
      <template #header>
        <span>修改密码</span>
      </template>
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
      >
        <el-form-item label="当前密码" prop="currentPassword">
          <el-input v-model="passwordForm.currentPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="passwordForm.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <div class="form-actions">
            <el-button type="primary" :loading="savingPassword" @click="savePassword">
              更新密码
            </el-button>
            <el-button @click="resetPassword">清空</el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getUserProfile, updateUserProfile, updateUserPassword } from '@/api/user'
import { clearUser, setUsername, useUserStore } from '@/utils/userStore'

const router = useRouter()
const { username } = useUserStore()

const loadingProfile = ref(false)
const savingProfile = ref(false)
const savingPassword = ref(false)

const profileFormRef = ref(null)
const passwordFormRef = ref(null)

const profileMeta = ref({
  id: '',
  createTime: ''
})

const profileForm = ref({
  id: null,
  username: '',
  email: ''
})

const originalProfile = ref(null)

const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const profileRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, message: '用户名至少 2 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ]
}

const passwordRules = {
  currentPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.value.newPassword) {
          callback(new Error('两次输入的密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function applyProfile(data) {
  profileForm.value = {
    id: data.id || null,
    username: data.username || '',
    email: data.email || ''
  }
  profileMeta.value = {
    id: data.id || '',
    createTime: formatDate(data.createTime)
  }
  originalProfile.value = { ...profileForm.value }
}

async function loadProfile() {
  const currentUsername = username.value || localStorage.getItem('username')
  if (!currentUsername) {
    ElMessage.warning('登录信息已过期，请重新登录')
    localStorage.removeItem('loggedIn')
    clearUser()
    router.push('/login')
    return
  }
  loadingProfile.value = true
  try {
    const res = await getUserProfile(currentUsername)
    if (!res.data || !res.data.username) {
      ElMessage.error('未获取到用户信息')
      return
    }
    applyProfile(res.data)
  } catch (error) {
    ElMessage.error('获取个人资料失败')
  } finally {
    loadingProfile.value = false
  }
}

function resetProfile() {
  if (originalProfile.value) {
    profileForm.value = { ...originalProfile.value }
  }
}

function resetPassword() {
  passwordForm.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
}

function saveProfile() {
  if (!profileFormRef.value) return
  profileFormRef.value.validate(async (valid) => {
    if (!valid) return
    savingProfile.value = true
    try {
      const res = await updateUserProfile(profileForm.value)
      if (res.data && res.data.success) {
        ElMessage.success(res.data.message || '个人资料更新成功')
        setUsername(profileForm.value.username)
        originalProfile.value = { ...profileForm.value }
      } else {
        ElMessage.error(res.data?.message || '更新失败')
      }
    } catch (error) {
      ElMessage.error('更新失败')
    } finally {
      savingProfile.value = false
    }
  })
}

function savePassword() {
  if (!passwordFormRef.value) return
  if (!profileForm.value.id) {
    ElMessage.error('缺少用户信息，无法更新密码')
    return
  }
  passwordFormRef.value.validate(async (valid) => {
    if (!valid) return
    if (passwordForm.value.currentPassword === passwordForm.value.newPassword) {
      ElMessage.warning('新密码不能与当前密码相同')
      return
    }
    savingPassword.value = true
    try {
      const res = await updateUserPassword({
        id: profileForm.value.id,
        currentPassword: passwordForm.value.currentPassword,
        newPassword: passwordForm.value.newPassword
      })
      if (res.data && res.data.success) {
        ElMessage.success(res.data.message || '密码更新成功')
        resetPassword()
      } else {
        ElMessage.error(res.data?.message || '更新失败')
      }
    } catch (error) {
      ElMessage.error('更新失败')
    } finally {
      savingPassword.value = false
    }
  })
}

onMounted(loadProfile)
</script>

<style scoped>
.profile-page {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.profile-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.profile-meta {
  margin-bottom: 12px;
}

.form-actions {
  display: flex;
  gap: 12px;
}
</style>
