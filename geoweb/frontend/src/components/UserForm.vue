<template>
  <el-dialog
    :title="isEdit ? '编辑用户' : '新增用户'"
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    width="400px"
  >
    <el-form :model="form" label-width="80px">
      <el-form-item label="用户名">
        <el-input v-model="form.username" autocomplete="off" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" autocomplete="off" type="password" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" autocomplete="off" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits } from 'vue'

const props = defineProps({
  visible: Boolean,
  formData: Object,
  isEdit: Boolean
})
const emit = defineEmits(['update:visible', 'submit'])

const form = ref({ username: '', password: '', email: '' })

watch(() => props.formData, (val) => {
  form.value = val ? { ...val } : { username: '', password: '', email: '' }
}, { immediate: true })

const close = () => {
  emit('update:visible', false)
}

const submit = () => {
  emit('submit', { ...form.value })
}
</script> 