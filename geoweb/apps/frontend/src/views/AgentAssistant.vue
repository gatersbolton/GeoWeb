<template>
  <div class="agent-page">
    <aside class="agent-side">
      <div class="side-header">
        <h2>ATV智脑</h2>
        <p>ATV 成像处理与解释助手</p>
      </div>

      <div class="quick-prompts">
        <div class="block-title">快捷提示</div>
        <el-button
          v-for="item in promptTemplates"
          :key="item"
          class="prompt-btn"
          text
          @click="applyPrompt(item)"
        >
          {{ item }}
        </el-button>
      </div>

      <div class="tools-panel">
        <div class="block-title">可用工具</div>
        <div v-if="toolItems.length" class="tool-list">
          <div
            v-for="tool in toolItems"
            :key="tool.tool_id"
            class="tool-item"
          >
            <div class="tool-top">
              <span class="tool-name">{{ tool.display_name }}</span>
              <el-tag :type="tool.status === 'active' ? 'success' : 'info'" size="small">
                {{ tool.status === 'active' ? '可用' : '规划中' }}
              </el-tag>
            </div>
            <p class="tool-desc">{{ tool.description }}</p>
          </div>
        </div>
        <div v-else class="tool-empty">工具加载中...</div>
      </div>
    </aside>

    <section class="agent-main">
      <header class="chat-header">
        <div>
          <h3>ATV智脑</h3>
          <p>面向钻孔声成像测井的对话式处理与解释助手</p>
        </div>
        <div class="header-actions">
          <el-tag :type="runtimeOnline ? 'success' : 'warning'" effect="dark">
            {{ runtimeOnline ? 'LLM在线' : 'LLM离线' }}
          </el-tag>
          <el-button @click="resetChat">新对话</el-button>
        </div>
      </header>

      <div ref="chatListRef" class="chat-list">
        <div
          v-for="(item, idx) in messages"
          :key="`${item.role}-${idx}`"
          class="chat-row"
          :class="item.role"
        >
          <div class="avatar">{{ item.role === 'user' ? '你' : 'ATV' }}</div>
          <div class="bubble">
            <div
              v-if="item.role === 'assistant'"
              class="bubble-content markdown-body"
              v-html="renderMarkdown(item.content)"
            />
            <template v-else>
              <div class="bubble-content user-plain">{{ item.content }}</div>
              <div v-if="item.attachmentName" class="user-attachment">
                附件: {{ item.attachmentName }}
              </div>
              <img
                v-if="item.previewImage"
                :src="item.previewImage"
                class="user-preview-image"
                alt="Uploaded input preview"
              />
            </template>
            <div
              v-if="item.decisionLog?.llm_error"
              class="llm-error"
            >
              在线调用失败：{{ item.decisionLog.llm_error }}
            </div>

            <div v-if="item.recommendation?.recommended_pipeline?.length" class="pipeline-panel">
              <div class="panel-label">推荐流程</div>
              <el-tag
                v-for="algo in item.recommendation.recommended_pipeline"
                :key="algo"
                class="algo-tag"
                effect="plain"
              >
                {{ algo }}
              </el-tag>
            </div>

            <div
              v-if="item.execution?.executed && getExecutionOutputs(item.execution).length"
              class="output-panel"
            >
              <div class="panel-label">
                {{ item.execution?.isSubtask ? '子任务结果' : '执行结果预览' }}
              </div>
              <div v-if="item.execution?.image_source === 'reused'" class="reuse-tip">
                本次执行复用了上一轮已上传输入。
              </div>
              <div
                v-for="output in getExecutionOutputs(item.execution)"
                :key="`${output.step_index || 0}-${output.algo_id || output.title || 'result'}`"
                class="result-card"
              >
                <div class="result-head">
                  <div>
                    <div class="result-title">{{ output.title || '执行结果' }}</div>
                    <div v-if="output.summary" class="result-summary">{{ output.summary }}</div>
                  </div>
                  <el-tag v-if="output.algo_id" size="small" effect="plain">
                    {{ output.algo_id }}
                  </el-tag>
                </div>
                <div class="metrics-row" v-if="metricEntries(output, item.execution).length">
                  <el-tag
                    v-for="entry in metricEntries(output, item.execution)"
                    :key="`${output.step_index || 0}-${entry.algoId}`"
                    size="small"
                    effect="plain"
                  >
                    {{ entry.algoId }}: {{ describeMetric(entry.metric) }}
                  </el-tag>
                </div>
                <div v-if="Array.isArray(output.warnings) && output.warnings.length" class="warn-row">
                  <el-alert
                    v-for="(warn, widx) in output.warnings"
                    :key="`${output.step_index || 0}-${widx}-${warn}`"
                    :title="warn"
                    type="warning"
                    :closable="false"
                    show-icon
                  />
                </div>
                <img :src="output.output_image" class="output-image" alt="Agent output" />
                <div class="download-actions">
                  <el-button
                    v-if="output.download_urls?.image"
                    type="primary"
                    plain
                    size="small"
                    @click="download(output.download_urls.image)"
                  >
                    下载图片
                  </el-button>
                  <el-button
                    v-if="output.download_urls?.npz"
                    type="success"
                    plain
                    size="small"
                    @click="download(output.download_urls.npz)"
                  >
                    下载 NPZ
                  </el-button>
                  <el-button
                    v-if="output.download_urls?.report"
                    plain
                    size="small"
                    @click="download(output.download_urls.report)"
                  >
                    下载报告
                  </el-button>
                  <el-button
                    v-if="output.download_urls?.recommendation"
                    plain
                    size="small"
                    @click="download(output.download_urls.recommendation)"
                  >
                    下载推荐
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <footer class="chat-input">
        <div class="upload-row">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*,.dlis"
            :on-change="onFileChange"
          >
            <el-button plain>上传 ATV 图像或 DLIS 文件</el-button>
          </el-upload>
          <span class="file-label" v-if="selectedFile">{{ selectedFile.name }}</span>
          <el-button
            v-if="selectedFile"
            text
            type="danger"
            @click="clearFile"
          >
            移除
          </el-button>
          <span class="runtime-note" v-if="runtimeInfo?.log_path">
            日志: {{ runtimeInfo.log_path }}
          </span>
          <span class="runtime-note" v-if="lastExecutionSessionId">
            已缓存输入会话: {{ lastExecutionSessionId }}
          </span>
        </div>

        <div class="input-row">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="输入问题，例如：先去除槽沟或偏心伪影，再做 4 倍超分增强；或解析 DLIS 并生成玫瑰图"
            @keydown.enter.prevent.exact="sendMessage"
          />
          <el-button type="primary" :loading="sending" @click="sendMessage">
            发送
          </el-button>
        </div>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { chatAgent, getAgentRuntime, listAgentTools } from '@/api/agent'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const messages = ref([
  {
    role: 'assistant',
    content: '我是 ATV智脑。你可以上传 ATV 图像或 DLIS 文件，告诉我需要去除槽沟伪影、去除去中心化伪影、增强清晰度、做超分，或者解析 DLIS 通道并生成 ATV/玫瑰图，我会按步骤调用工具并逐步返回结果。',
  },
])
const inputText = ref('')
const selectedFile = ref(null)
const sending = ref(false)
const chatListRef = ref(null)
const toolItems = ref([])
const runtimeInfo = ref(null)
const runtimeOnline = ref(false)
const lastExecutionSessionId = ref('')

const promptTemplates = [
  '帮我判断这张图像该用哪种去伪影算法',
  '帮我给它去除去中心化的伪影',
  '这张图有槽沟伪影，帮我用 GrooveMask 去掉',
  '先做 stick_pull 去伪影，再做增强',
  '直接做 4 倍超分增强',
  '解析这个 DLIS 文件并列出主要通道',
  '基于这个 DLIS 文件生成 ATV 图和玫瑰图',
]

function applyPrompt(text) {
  inputText.value = text
}

function onFileChange(file) {
  selectedFile.value = file?.raw || null
}

function clearFile() {
  selectedFile.value = null
}

function buildUserUploadPreview(file) {
  if (!file || !String(file.type || '').startsWith('image/')) {
    return ''
  }
  return URL.createObjectURL(file)
}

function toHistoryPayload() {
  return messages.value
    .filter((item) => (item.role === 'user' || item.role === 'assistant') && !item.excludeFromHistory)
    .map((item) => ({
      role: item.role,
      content: item.content,
    }))
}

function getExecutionOutputs(execution) {
  if (Array.isArray(execution?.outputs) && execution.outputs.length) {
    return execution.outputs
  }
  if (!execution?.output_image) {
    return []
  }
  const pipeline = Array.isArray(execution?.pipeline) ? execution.pipeline : []
  const lastAlgoId = pipeline[pipeline.length - 1] || 'result'
  return [
    {
      step_index: Array.isArray(execution?.step_reports) ? execution.step_reports.length || 1 : 1,
      algo_id: lastAlgoId,
      title: '执行结果',
      summary: '',
      warnings: extractWarnings(execution?.step_reports),
      output_image: execution.output_image,
      download_urls: execution.download_urls || {},
    },
  ]
}

function metricEntries(output, execution) {
  if (
    output?.algo_id
    && output?.quality_metrics
    && typeof output.quality_metrics === 'object'
    && Object.keys(output.quality_metrics).length
  ) {
    return [{ algoId: output.algo_id, metric: output.quality_metrics }]
  }
  if (
    !execution?.quality_metrics
    || typeof execution.quality_metrics !== 'object'
    || !Object.keys(execution.quality_metrics).length
  ) {
    return []
  }
  return Object.entries(execution.quality_metrics).map(([algoId, metric]) => ({
    algoId,
    metric,
  }))
}

function buildSubtaskExecution(
  parentExecution,
  subtask,
  { includeOverallDownloads = false, includeImageSource = false } = {},
) {
  const overallDownloads = includeOverallDownloads
    ? {
        report: parentExecution?.download_urls?.report,
        recommendation: parentExecution?.download_urls?.recommendation,
      }
    : {}
  return {
    executed: true,
    isSubtask: true,
    session_id: parentExecution?.session_id || '',
    source: parentExecution?.source || '',
    image_source: includeImageSource ? parentExecution?.image_source || '' : '',
    pipeline: subtask?.algo_id ? [subtask.algo_id] : [],
    step_reports: subtask?.step_report ? [subtask.step_report] : [],
    quality_metrics: subtask?.algo_id ? { [subtask.algo_id]: subtask.quality_metrics || {} } : {},
    output_image: subtask?.output_image || '',
    outputs: [subtask],
    download_urls: {
      ...(subtask?.download_urls || {}),
      ...overallDownloads,
    },
  }
}

function appendAssistantMessages(data) {
  const subtasks = Array.isArray(data?.execution?.subtasks) ? data.execution.subtasks : []
  const shouldSplitMessages = subtasks.length > 1

  messages.value.push({
    role: 'assistant',
    content: data.answer || '已完成处理。',
    recommendation: data.recommendation,
    execution: shouldSplitMessages ? null : data.execution,
    decisionLog: data.decision_log,
  })

  if (!shouldSplitMessages) {
    return
  }

  subtasks.forEach((subtask, index) => {
    messages.value.push({
      role: 'assistant',
      content: subtask.message || subtask.summary || `子任务 ${index + 1} 已完成。`,
      execution: buildSubtaskExecution(data.execution, subtask, {
        includeOverallDownloads: index === subtasks.length - 1,
        includeImageSource: index === 0,
      }),
      excludeFromHistory: true,
    })
  })
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text && !selectedFile.value) {
    ElMessage.warning('请输入问题或上传图像')
    return
  }
  const historyPayload = toHistoryPayload()
  const currentFile = selectedFile.value
  const previewImage = buildUserUploadPreview(currentFile)
  const attachmentName = currentFile?.name || ''
  const isDlisUpload = Boolean(currentFile && currentFile.name?.toLowerCase().endsWith('.dlis'))
  const defaultMessage = isDlisUpload ? '[上传 DLIS 文件进行分析]' : '[上传图像进行分析]'
  const defaultPrompt = isDlisUpload
    ? '请解析这个 DLIS 文件，列出主要通道并按需生成 ATV 图或玫瑰图'
    : '请分析这张图像，并给出去伪影或增强建议'

  messages.value.push({
    role: 'user',
    content: text || defaultMessage,
    attachmentName,
    previewImage,
  })
  inputText.value = ''
  scrollToBottom()

  try {
    sending.value = true
    const formData = new FormData()
    formData.append('message', text || defaultPrompt)
    formData.append('history_json', JSON.stringify(historyPayload))
    formData.append('execute_on_upload', 'true')
    if (currentFile) {
      formData.append('image_file', currentFile)
    } else if (lastExecutionSessionId.value) {
      formData.append('reuse_session_id', lastExecutionSessionId.value)
    }

    const data = await chatAgent(formData)
    appendAssistantMessages(data)
    if (data?.execution?.executed && data?.execution?.session_id) {
      lastExecutionSessionId.value = data.execution.session_id
    }
  } catch (error) {
    const errorMsg = error?.response?.data?.error || error?.message || '请求失败'
    messages.value.push({
      role: 'assistant',
      content: `处理失败：${errorMsg}`,
    })
    ElMessage.error(errorMsg)
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatListRef.value) {
      chatListRef.value.scrollTop = chatListRef.value.scrollHeight
    }
  })
}

function download(urlPath) {
  const href = urlPath.startsWith('/api') ? urlPath : `/api${urlPath}`
  window.open(href, '_blank')
}

function renderMarkdown(content) {
  const text = typeof content === 'string' ? content : ''
  const html = marked.parse(text, {
    breaks: true,
    gfm: true,
    mangle: false,
    headerIds: false,
  })
  return DOMPurify.sanitize(html)
}

function toMetric(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-'
  return value.toFixed(4)
}

function describeMetric(metric) {
  if (!metric || typeof metric !== 'object') return '-'
  if (typeof metric.sharpness_gain === 'number' && !Number.isNaN(metric.sharpness_gain)) {
    return `sharpness x${toMetric(metric.sharpness_gain)}`
  }
  if (typeof metric.mean_abs_delta === 'number' && !Number.isNaN(metric.mean_abs_delta)) {
    return `Δ=${toMetric(metric.mean_abs_delta)}`
  }
  return '-'
}

function extractWarnings(stepReports) {
  if (!Array.isArray(stepReports)) return []
  const warnings = []
  for (const step of stepReports) {
    const algo = step?.algo_id || 'unknown'
    const list = Array.isArray(step?.warnings) ? step.warnings : []
    for (const item of list) {
      warnings.push(`${algo}: ${item}`)
    }
  }
  return warnings
}

function resetChat() {
  messages.value = [
    {
      role: 'assistant',
      content: '新的对话已开始。你可以继续上传 ATV 图像或 DLIS 文件，并描述去伪影、增强、超分或 DLIS 可视化目标。',
    },
  ]
  selectedFile.value = null
  lastExecutionSessionId.value = ''
}

async function loadTools() {
  try {
    const data = await listAgentTools()
    toolItems.value = Array.isArray(data?.tools) ? data.tools : []
  } catch (error) {
    toolItems.value = []
  }
}

async function loadRuntime() {
  try {
    const data = await getAgentRuntime()
    runtimeInfo.value = data?.runtime || null
    runtimeOnline.value = Boolean(runtimeInfo.value?.llm_enabled)
  } catch (error) {
    runtimeInfo.value = null
    runtimeOnline.value = false
  }
}

onMounted(() => {
  loadTools()
  loadRuntime()
  scrollToBottom()
})
</script>

<style scoped>
.agent-page {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 16px;
  height: calc(100vh - 110px);
  min-height: 680px;
}

.agent-side {
  background: linear-gradient(160deg, #f7fbff 0%, #edf4ff 100%);
  border: 1px solid #dfe9f7;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.side-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1f2d3d;
}

.side-header p {
  margin: 6px 0 0;
  color: #5d6b7a;
  font-size: 13px;
}

.block-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}

.quick-prompts {
  margin-top: 18px;
}

.prompt-btn {
  display: block;
  width: 100%;
  text-align: left;
  justify-content: flex-start;
  margin-bottom: 6px;
  color: #1d4ed8;
}

.tools-panel {
  margin-top: 16px;
  flex: 1;
  overflow: auto;
}

.tool-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 8px;
}

.tool-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.tool-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.tool-desc {
  margin: 8px 0 0;
  font-size: 12px;
  color: #475569;
}

.tool-empty {
  color: #94a3b8;
  font-size: 12px;
}

.agent-main {
  display: flex;
  flex-direction: column;
  border: 1px solid #d9e3f0;
  border-radius: 12px;
  background: #f8fafc;
  min-height: 0;
}

.chat-header {
  padding: 14px 16px;
  border-bottom: 1px solid #dbe3ef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.chat-header h3 {
  margin: 0;
  color: #1e293b;
}

.chat-header p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 18px;
  background:
    radial-gradient(circle at 5% 0%, rgba(30, 64, 175, 0.06) 0, transparent 35%),
    radial-gradient(circle at 95% 20%, rgba(14, 116, 144, 0.07) 0, transparent 30%),
    #f8fafc;
}

.chat-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 14px;
}

.chat-row.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #1e3a8a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}

.chat-row.user .avatar {
  background: #0f766e;
}

.bubble {
  max-width: min(900px, 85%);
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 14px;
  padding: 12px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
}

.chat-row.user .bubble {
  background: #0f766e;
  border-color: #0f766e;
  color: #fff;
}

.bubble-content {
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
}

.user-plain {
  white-space: pre-wrap;
}

.user-attachment {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.88);
}

.user-preview-image {
  display: block;
  margin-top: 10px;
  max-width: min(420px, 100%);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
}

.markdown-body :deep(p) {
  margin: 0 0 8px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0 0 10px 20px;
  padding: 0;
}

.markdown-body :deep(code) {
  background: #e2e8f0;
  border-radius: 4px;
  padding: 2px 5px;
  font-size: 12px;
}

.chat-row.user .markdown-body :deep(code) {
  background: rgba(255, 255, 255, 0.28);
}

.markdown-body :deep(pre) {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #dbe3ef;
  padding: 6px 8px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f1f5f9;
  font-weight: 600;
}

.pipeline-panel,
.output-panel {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #d5deea;
}

.llm-error {
  margin-top: 8px;
  font-size: 12px;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 6px 8px;
}

.reuse-tip {
  margin-bottom: 8px;
  font-size: 12px;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 6px;
  padding: 6px 8px;
}

.chat-row.user .pipeline-panel,
.chat-row.user .output-panel {
  border-color: rgba(255, 255, 255, 0.35);
}

.panel-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
}

.chat-row.user .panel-label {
  color: rgba(255, 255, 255, 0.9);
}

.algo-tag {
  margin-right: 6px;
  margin-bottom: 6px;
}

.output-image {
  display: block;
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid #dbe3ef;
  background: #fff;
}

.download-actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.result-card {
  padding: 10px;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  background: #ffffff;
}

.result-card + .result-card {
  margin-top: 10px;
}

.result-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.result-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.result-summary {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.metrics-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.warn-row {
  display: grid;
  gap: 6px;
  margin-bottom: 8px;
}

.chat-input {
  border-top: 1px solid #dbe3ef;
  background: #ffffff;
  padding: 12px 14px;
}

.upload-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}

.file-label {
  font-size: 12px;
  color: #0f172a;
  max-width: 360px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.runtime-note {
  font-size: 12px;
  color: #64748b;
}

.input-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: end;
}

@media (max-width: 1080px) {
  .agent-page {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 600px;
  }

  .agent-side {
    max-height: 300px;
  }
}
</style>
