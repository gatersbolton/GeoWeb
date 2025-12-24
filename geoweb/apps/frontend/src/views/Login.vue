<template>
  <div class="auth-container">
    <el-card class="auth-card" shadow="hover">
      <h2 class="title">欢迎回来</h2>
      <p class="subtitle">请登录以继续</p>
      <el-form :model="form" :rules="rules" ref="loginForm" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" autocomplete="off" placeholder="输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" autocomplete="off" placeholder="输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" @click="onSubmit" round>登录</el-button>
        </el-form-item>
      </el-form>
      <div class="footer">
        <span>还没有账户？</span>
        <el-button type="text" @click="goRegister">注册</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { loginUser } from '@/api/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loginForm = ref(null)
const form = ref({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const onSubmit = () => {
  loginForm.value.validate(async (valid) => {
    if (!valid) return
    try {
      const res = await loginUser(form.value)
      if (res.data === '登录成功') {
        ElMessage.success('登录成功')
        localStorage.setItem('loggedIn', 'true')
        router.push('/csv')
      } else {
        ElMessage.error(res.data || '登录失败')
      }
    } catch (e) {
      ElMessage.error('登录失败')
    }
  })
}

const goRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #3b82f6 0%, #9333ea 100%);
}

.auth-card {
  width: 420px;
  padding: 32px 36px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
}

.title {
  text-align: center;
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.subtitle {
  text-align: center;
  color: #6b7280;
  margin-bottom: 24px;
  font-size: 14px;
}

.login-btn {
  width: 100%;
  height: 42px;
  font-size: 16px;
}

.footer {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 12px;
  font-size: 14px;
  color: #6b7280;
}
</style> 