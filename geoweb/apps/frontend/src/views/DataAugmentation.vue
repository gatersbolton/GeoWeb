<template>
  <div class="page">
    <div class="header">
      <h2>数据增强项目</h2>
      <p class="description">面向去伪影与去噪算法的可扩展入口</p>
    </div>

    <el-card class="card">
      <template #header>
        <div class="card-header">
          <span>算法选择与输入</span>
        </div>
      </template>

      <el-form label-width="120px" class="form">
        <el-form-item label="算法">
          <el-select v-model="algorithm" class="select" size="small">
            <el-option
              v-for="item in algorithms"
              :key="item.key"
              :label="item.label"
              :value="item.key"
            />
          </el-select>
          <span class="hint">{{ currentAlgorithm?.desc }}</span>
        </el-form-item>

        <el-form-item label="示例图片">
          <el-checkbox v-model="useDemo">使用默认示例图片</el-checkbox>
        </el-form-item>

        <el-form-item label="上传图片">
          <input
            type="file"
            accept="image/*"
            :disabled="useDemo"
            @change="onFileChange"
          />
          <div class="tip">支持 PNG/JPG，建议与算法示例类似的成像图片</div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="submit">
            {{ loading ? '处理中...' : '开始处理' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="result" class="card mt-16">
      <template #header>
        <div class="card-header">
          <span>处理结果</span>
        </div>
      </template>
      <div class="result">
        <div class="row"><b>算法：</b>{{ currentAlgorithm?.label }}</div>
        <div class="row"><b>会话ID：</b>{{ result.session_id }}</div>
        <div class="row"><b>来源：</b>{{ result.source }}</div>

        <div v-if="result.output_image" class="image-wrapper">
          <img :src="result.output_image" alt="去伪影结果" />
        </div>

        <div class="downloads">
          <el-button
            v-if="result.download_urls?.image"
            type="primary"
            plain
            @click="download(result.download_urls.image)"
          >
            下载图片
          </el-button>
          <el-button
            v-if="result.download_urls?.csv"
            type="success"
            plain
            @click="download(result.download_urls.csv)"
          >
            下载 CSV
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { runAugmentation } from '@/api/augmentation'

const algorithms = [
  {
    key: 'stick-and-pull',
    label: 'Stick & Pull 去伪影',
    desc: '修复 stick-and-pull 伪影，输出校正图像与速度曲线 CSV',
  },
]

const algorithm = ref(algorithms[0].key)
const useDemo = ref(false)
const fileRef = ref(null)
const loading = ref(false)
const result = ref(null)

const currentAlgorithm = computed(() => {
  return algorithms.find((item) => item.key === algorithm.value)
})

function onFileChange(e) {
  const files = e.target.files
  fileRef.value = files && files.length ? files[0] : null
}

async function submit() {
  if (!useDemo.value && !fileRef.value) {
    ElMessage.error('请选择图片或勾选“使用默认示例图片”')
    return
  }

  try {
    loading.value = true
    const fd = new FormData()
    fd.append('algorithm', algorithm.value)
    if (useDemo.value) {
      fd.append('use_demo', 'true')
    } else {
      fd.append('image_file', fileRef.value)
    }

    const data = await runAugmentation(fd)
    result.value = data
    ElMessage.success('处理完成')
  } catch (e) {
    const msg = e?.response?.data?.error || e?.message || '处理失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function download(urlPath) {
  const href = urlPath.startsWith('/api') ? urlPath : `/api${urlPath}`
  window.open(href, '_blank')
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
}
.header {
  text-align: center;
  margin-bottom: 16px;
}
.header h2 {
  margin-bottom: 6px;
  color: #303133;
}
.description {
  color: #606266;
  font-size: 13px;
}
.card {
  margin-bottom: 12px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.form {
  padding: 6px 4px;
}
.select {
  width: 240px;
}
.hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
.tip {
  color: #888;
  font-size: 12px;
  margin-top: 6px;
}
.mt-16 {
  margin-top: 16px;
}
.result {
  padding: 8px 4px;
}
.row {
  margin: 6px 0;
}
.image-wrapper {
  margin-top: 12px;
  padding: 12px;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  text-align: center;
}
.image-wrapper img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.downloads {
  margin-top: 12px;
}
.downloads > * {
  margin-right: 8px;
}
</style>
