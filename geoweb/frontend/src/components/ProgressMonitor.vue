<template>
  <div class="progress-monitor">
    <el-card v-if="visible" class="progress-card">
      <template #header>
        <div class="card-header">
          <span>处理进度</span>
          <el-button
            v-if="canClose"
            type="text"
            :icon="Close"
            @click="closeMonitor"
            class="close-btn"
          />
        </div>
      </template>
      
      <!-- 进度条 -->
      <div class="progress-section">
        <el-progress
          :percentage="progress"
          :status="progressStatus"
          :stroke-width="8"
          class="progress-bar"
        />
        <div class="progress-text">
          {{ currentMessage || '准备中...' }}
        </div>
      </div>
      
      <!-- 日志输出 -->
      <div class="log-section">
        <div class="log-header">
          <span>处理日志</span>
          <el-button 
            type="text" 
            size="small" 
            @click="clearLogs"
            :disabled="logs.length === 0"
          >
            清空
          </el-button>
        </div>
        <div class="log-container" ref="logContainer">
          <div
            v-for="(log, index) in logs"
            :key="index"
            class="log-entry"
            :class="log.type"
          >
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
          <div v-if="logs.length === 0" class="log-empty">
            暂无日志信息
          </div>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="action-section" v-if="showActions">
        <el-button
          v-if="status === 'completed'"
          type="primary"
          @click="viewResults"
        >
          查看结果
        </el-button>
        <el-button
          v-if="status === 'error'"
          type="danger"
          @click="retryCalculation"
        >
          重新计算
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { Close } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  },
  visible: {
    type: Boolean,
    default: true
  },
  autoConnect: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['close', 'completed', 'error', 'retry'])

// 状态管理
const progress = ref(0)
const currentMessage = ref('')
const status = ref('connecting') // connecting, running, completed, error
const logs = ref([])
const websocket = ref(null)
const logContainer = ref(null)

// 计算属性
const progressStatus = computed(() => {
  switch (status.value) {
    case 'completed': return 'success'
    case 'error': return 'exception'
    case 'running': return 'normal'
    default: return 'normal'
  }
})

const canClose = computed(() => {
  return status.value === 'completed' || status.value === 'error'
})

const showActions = computed(() => {
  return status.value === 'completed' || status.value === 'error'
})

// 方法
function startProgressPolling() {
  if (!props.sessionId) return
  
  addLog('开始监控计算进度...', 'info')
  status.value = 'running'
  
  let pollCount = 0
  
  const pollInterval = setInterval(async () => {
    try {
      const response = await axios.get(`http://localhost:8000/borehole/progress/${props.sessionId}`)
      if (response.data) {
        const prevMessage = currentMessage.value
        handleProgressUpdate(response.data)
        
        // 如果计算完成，停止轮询
        if (response.data.percentage === 100 || response.data.message.includes('完成')) {
          clearInterval(pollInterval)
          status.value = 'completed'
          emit('completed', response.data)
          return
        }
        
        // 如果在非进度阶段且消息没有变化，减少轮询频率
        if (isInNonProgressPhase.value && 
            response.data.message === prevMessage && 
            pollCount % 3 !== 0) {  // 每6秒轮询一次而不是每2秒
          pollCount++
          return
        }
      }
      pollCount++
    } catch (error) {
      if (error.response?.status === 404) {
        // 任务还没开始，继续轮询
        return
      }
      console.error('获取进度失败:', error)
      clearInterval(pollInterval)
      status.value = 'error'
      addLog('获取进度失败', 'error')
      emit('error', { message: '获取进度失败' })
    }
  }, 2000) // 基础轮询间隔2秒
  
  // 存储interval ID以便清理
  websocket.value = { close: () => clearInterval(pollInterval) }
}

const lastLoggedPercentage = ref(-1)
const lastLoggedMessage = ref('')
const isInNonProgressPhase = ref(false)

function handleProgressUpdate(data) {
  switch (data.type) {
    case 'progress':
      if (data.percentage !== null && data.percentage !== undefined) {
        progress.value = data.percentage
        isInNonProgressPhase.value = false
      }
      
      currentMessage.value = data.message
      
      // 检查是否进入非进度阶段（如Saving outputs）
      if (data.percentage === null && 
          (data.message.includes('Saving') || 
           data.message.includes('Loading') ||
           data.message.includes('generating'))) {
        isInNonProgressPhase.value = true
      }
      
      // 只在特定条件下添加日志，减少日志输出频率
      const shouldLog = (
        data.message !== lastLoggedMessage.value && (  // 消息内容有变化
          data.percentage === null ||  // 非百分比消息
          data.percentage === 100 ||   // 100%完成
          data.percentage - lastLoggedPercentage.value >= 10 ||  // 每10%记录一次
          data.message.includes('Loading') ||
          data.message.includes('Saving') ||
          data.message.includes('完成') ||
          data.message.includes('失败')
        )
      )
      
      if (shouldLog) {
        addLog(data.message, 'info')
        lastLoggedPercentage.value = data.percentage || lastLoggedPercentage.value
        lastLoggedMessage.value = data.message
      }
      break
      
    case 'completed':
      progress.value = 100
      status.value = 'completed'
      currentMessage.value = '处理完成！'
      isInNonProgressPhase.value = false
      addLog('处理完成！', 'success')
      emit('completed', data)
      break
      
    case 'error':
      status.value = 'error'
      currentMessage.value = '处理失败'
      isInNonProgressPhase.value = false
      addLog(data.message, 'error')
      emit('error', data)
      break
  }
  
  // 自动滚动到最新日志
  nextTick(() => {
    scrollToBottom()
  })
}

function addLog(message, type = 'info') {
  logs.value.push({
    message,
    type,
    timestamp: new Date().toISOString()
  })
}

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
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

function clearLogs() {
  logs.value = []
}

function closeMonitor() {
  if (websocket.value) {
    websocket.value.close()
  }
  emit('close')
}

function viewResults() {
  emit('completed')
}

function retryCalculation() {
  // 重置状态
  progress.value = 0
  currentMessage.value = ''
  status.value = 'connecting'
  logs.value = []
  
  // 重新连接
  if (websocket.value) {
    websocket.value.close()
  }
  
  emit('retry')
}

// 生命周期
onMounted(() => {
  if (props.autoConnect && props.sessionId) {
    startProgressPolling()
  }
})

onUnmounted(() => {
  if (websocket.value) {
    websocket.value.close()
  }
})

// 暴露方法给父组件
defineExpose({
  startProgressPolling,
  addLog
})
</script>

<style scoped>
.progress-monitor {
  margin: 20px 0;
}

.progress-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.close-btn {
  color: #909399;
  padding: 4px;
}

.close-btn:hover {
  color: #f56c6c;
}

.progress-section {
  margin-bottom: 20px;
}

.progress-bar {
  margin-bottom: 12px;
}

.progress-text {
  font-size: 14px;
  color: #606266;
  text-align: center;
}

.log-section {
  margin-bottom: 20px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.log-container {
  max-height: 200px;
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

.log-entry.info .log-message {
  color: #606266;
}

.log-entry.success .log-message {
  color: #67c23a;
}

.log-entry.warning .log-message {
  color: #e6a23c;
}

.log-entry.error .log-message {
  color: #f56c6c;
}

.log-empty {
  text-align: center;
  color: #c0c4cc;
  font-style: italic;
  padding: 20px 0;
}

.action-section {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

/* 滚动条样式 */
.log-container::-webkit-scrollbar {
  width: 6px;
}

.log-container::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.log-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>