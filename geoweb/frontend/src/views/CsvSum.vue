<template>
  <div class="csv-container">
    <div class="left-panel">
      <h2>CSV处理</h2>
      <el-upload
        class="upload-demo"
        drag
        :auto-upload="false"
        :show-file-list="true"
        :on-change="handleChange"
        :before-upload="() => false"
        accept=".csv"
      >
        <i class="el-icon-upload"></i>
        <div class="el-upload__text">将CSV文件拖到此处，或<em>点击上传</em></div>
      </el-upload>
      <el-button
        type="primary"
        :disabled="!file"
        @click="handleUpload"
        class="upload-btn"
      >
        上传并处理
      </el-button>
    </div>

    <div class="right-panel">
      <div v-if="sum !== null" class="result">
        <el-alert :title="'求和结果：' + sum" type="success" show-icon />
      </div>
      <div v-if="plot" class="plot">
        <img :src="plot" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { sumCsv } from '@/api/csv'
import { ElMessage } from 'element-plus'

const file = ref(null)
const sum = ref(null)
const plot = ref(null)

function handleChange(uploadFile) {
  file.value = uploadFile.raw
  sum.value = null
}

async function handleUpload() {
  if (!file.value) return
  const formData = new FormData()
  formData.append('file', file.value)
  try {
    const res = await sumCsv(formData)
    sum.value = res.sum
    plot.value = res.plot
    ElMessage.success('处理成功')
  } catch (e) {
    ElMessage.error('上传或处理失败')
  }
}
</script>

<style scoped>
.csv-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  padding: 40px;
}

.left-panel {
  flex: 0 0 40%;
}

.right-panel {
  flex: 1;
}

.upload-demo {
  width: 100%;
}

.upload-btn {
  margin-top: 16px;
}

.result {
  font-size: 18px;
}

.plot img {
  max-width: 100%;
}
</style> 