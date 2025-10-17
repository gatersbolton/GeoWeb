<template>
  <div class="auth-container">
    <el-card class="auth-card">
      <h2 class="title">注册</h2>
      <el-form :model="form" :rules="rules" ref="registerForm" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" autocomplete="off" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" autocomplete="off" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="onSubmit">注册</el-button>
          <el-button @click="goLogin">返回登录</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { registerUser } from '@/api/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const registerForm = ref(null)
const form = ref({
  username: '',
  password: '',
  email: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
}

const onSubmit = () => {
  registerForm.value.validate(async (valid) => {
    if (!valid) return
    try {
      const res = await registerUser(form.value)
      if (res.data === '注册成功') {
        ElMessage.success('注册成功，请登录')
        router.push('/login')
      } else {
        ElMessage.error(res.data || '注册失败')
      }
    } catch (e) {
      ElMessage.error('注册失败')
    }
  })
}

const goLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #f5f5f5;
}

.auth-card {
  width: 360px;
}

.title {
  text-align: center;
  margin-bottom: 20px;
}
</style> 