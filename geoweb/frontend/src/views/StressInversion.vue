<template>
  <div class="page">
    <el-card class="card">
      <template #header>
        <div class="card-header">
          <span>地应力反演项目</span>
        </div>
      </template>

      <div class="section">
        <el-form label-width="120px">
          <el-form-item label="模式">
            <el-radio-group v-model="mode">
              <el-radio label="global">全局反演</el-radio>
              <el-radio label="depthwise">分段反演</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item v-if="mode==='depthwise'" label="窗口厚度 dz">
            <el-input-number v-model="dz" :min="1" :step="1" />
            <span class="ml-8">单位同CSV深度</span>
          </el-form-item>

          <el-form-item v-if="mode==='global'" label="采样跨距">
            <el-input-number v-model="sampleStride" :min="1" :step="1" />
          </el-form-item>

          <el-form-item label="示例数据">
            <el-checkbox v-model="useDemo">使用默认演示数据</el-checkbox>
          </el-form-item>

          <el-form-item label="上传CSV">
            <input type="file" accept=".csv" :disabled="useDemo" @change="onFileChange" />
            <div class="tip">
              需要“椭圆参数+井轨迹拼接”的CSV（如：ellipticity_parameters_outlier_filtered_dz0.025m_borehole_trajectory.csv）
            </div>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="loading" @click="submit">开始反演</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <el-card v-if="result" class="card mt-16">
      <template #header>
        <div class="card-header">
          <span>反演结果</span>
        </div>
      </template>

      <div class="section">
        <div class="row"><b>会话ID：</b>{{ result.session_id }}</div>
        <div class="row"><b>模式：</b>{{ result.mode }}</div>
        <div v-if="result.summary?.best" class="row">
          <b>最佳候选(Top-1)：</b>
          <span>a={{ result.summary.best.a.toFixed(2) }}，b={{ result.summary.best.b.toFixed(2) }}，
            c={{ result.summary.best.c.toFixed(2) }}，phi={{ result.summary.best.phi.toFixed(3) }}，
            s3={{ result.summary.best.s3.toFixed(3) }}，RMSE={{ result.summary.best.rmse.toFixed(3) }}</span>
        </div>
        <div v-if="result.summary?.window_count" class="row">
          <b>窗口数量：</b>{{ result.summary.window_count }}（dz={{ result.summary.dz }}）
        </div>

        <div class="downloads mt-12">
          <el-button v-if="result.download_urls?.result_mat" @click="download(result.download_urls.result_mat)" type="success" plain>
            下载 MAT
          </el-button>
          <el-button v-if="result.download_urls?.result_json" @click="download(result.download_urls.result_json)" type="info" plain>
            下载 JSON
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card v-if="sessionId" class="card mt-16">
      <template #header>
        <div class="card-header">
          <span>处理进度</span>
        </div>
      </template>
      <div class="section">
        <div class="log-container" ref="logContainer">
          <div
            v-for="(log, index) in logs"
            :key="index"
            class="log-entry"
          >
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
          <div v-if="logs.length === 0" class="log-empty">
            等待任务开始...
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount, nextTick } from 'vue'
import { runStressInversionAsync, getStressinvProgress, getStressinvResult } from '@/api/stressinv'
import { ElMessage } from 'element-plus'

const mode = ref('global')
const dz = ref(25)
const sampleStride = ref(5)
const useDemo = ref(true)
const fileRef = ref(null)
const loading = ref(false)
const result = ref(null)
const sessionId = ref(null)
let progressTimer = null
const logs = ref([])
const logContainer = ref(null)
const lastMessage = ref('')

function onFileChange(e) {
  const files = e.target.files
  fileRef.value = files && files.length ? files[0] : null
}

async function submit() {
  try {
    loading.value = true
    const fd = new FormData()
    fd.append('mode', mode.value)
    if (mode.value === 'depthwise') {
      fd.append('dz', String(dz.value ?? 25))
    } else {
      fd.append('sample_stride', String(sampleStride.value ?? 1))
    }
    if (useDemo.value) {
      fd.append('use_demo', 'true')
    } else {
      if (!fileRef.value) {
        ElMessage.error('请选择需要上传的CSV文件或勾选“使用默认演示数据”')
        return
      }
      fd.append('ellip_traj_file', fileRef.value)
    }
    // 启动异步任务
    const start = await runStressInversionAsync(fd)
    sessionId.value = start.session_id
    result.value = null
    logs.value = []
    lastMessage.value = ''
    ElMessage.success('任务已启动')

    // 轮询进度，每4秒
    if (progressTimer) {
      clearInterval(progressTimer)
    }
    progressTimer = setInterval(async () => {
      if (!sessionId.value) return
      try {
        const p = await getStressinvProgress(sessionId.value)
        // 仅当消息本身变化时才更新
        const baseMsg = p?.message || ''
        if (baseMsg && baseMsg !== lastMessage.value) {
          const text = p.percentage != null
            ? `${baseMsg}（${Math.round(p.percentage)}%）`
            : baseMsg
          addLog(text)
          lastMessage.value = baseMsg
        }
        if (p.percentage === 100) {
          // 获取结果
          const data = await getStressinvResult(sessionId.value)
          result.value = data
          clearInterval(progressTimer)
          progressTimer = null
          addLog('反演完成！')
          ElMessage.success('反演完成')
          sessionId.value = null
          lastMessage.value = ''
        }
      } catch (err) {
        // 404 表示还没有进度或任务未注册；忽略
      }
    }, 4000)
  } catch (e) {
    const msg = e?.response?.data?.error || e?.message || '反演失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function download(urlPath) {
  // 后端实际服务以 /api 前缀代理
  const href = `/api${urlPath}`
  window.open(href, '_blank')
}

function addLog(message) {
  logs.value.push({
    message,
    timestamp: new Date().toISOString()
  })
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

function formatTime(timestamp) {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onBeforeUnmount(() => {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
})
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
}
.card {
  margin-bottom: 12px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section {
  padding: 8px 4px;
}
.row {
  margin: 6px 0;
}
.tip {
  color: #888;
  font-size: 12px;
  margin-top: 6px;
}
.ml-8 {
  margin-left: 8px;
}
.mt-12 {
  margin-top: 12px;
}
.mt-16 {
  margin-top: 16px;
}
.downloads > * {
  margin-right: 8px;
}

.log-container {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px;
  background: #fafafa;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
}
.log-entry {
  display: flex;
  margin-bottom: 4px;
  line-height: 1.4;
}
.log-time {
  color: #909399;
  margin-right: 8px;
  min-width: 60px;
}
.log-message {
  flex: 1;
  word-break: break-all;
}
.log-empty {
  text-align: center;
  color: #c0c4cc;
  font-style: italic;
  padding: 20px 0;
}
</style>


