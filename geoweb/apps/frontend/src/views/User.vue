<template>
  <div>
    <el-button type="primary" @click="openAdd">新增用户</el-button>
    <el-table :data="users" style="width: 100%; margin-top: 20px">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="password" label="密码" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <user-form
      v-model:visible="dialogVisible"
      :form-data="currentUser"
      :is-edit="isEdit"
      @submit="handleSubmit"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getUserList, addUser, updateUser, deleteUser } from '../api/user'
import UserForm from '../components/UserForm.vue'

const users = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const currentUser = ref({})

const fetchUsers = async () => {
  const res = await getUserList()
  users.value = res.data
}

onMounted(fetchUsers)

const openAdd = () => {
  isEdit.value = false
  currentUser.value = {}
  dialogVisible.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  currentUser.value = { ...row }
  dialogVisible.value = true
}

const handleSubmit = async (form) => {
  if (isEdit.value) {
    await updateUser(form)
  } else {
    await addUser(form)
  }
  dialogVisible.value = false
  fetchUsers()
}

const handleDelete = async (id) => {
  await deleteUser(id)
  fetchUsers()
}
</script> 