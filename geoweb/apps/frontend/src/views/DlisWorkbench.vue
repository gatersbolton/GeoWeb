<template>
  <div class="dlis-page">
    <section class="hero">
      <div>
        <p class="eyebrow">DLIS Visual Lab</p>
        <h2>DLIS 可视化工作台</h2>
        <p class="hero-copy">
          上传钻孔声成像测井的 `.dlis` 文件，浏览通道结构，生成 ATV 振幅图、走时图与方位玫瑰图。
        </p>
      </div>
      <div class="hero-meta">
        <div class="meta-pill">Web 可视化操作</div>
        <div class="meta-pill">Agent 可复用</div>
        <div class="meta-pill">支持 NPZ/PNG 下载</div>
      </div>
    </section>

    <section class="workbench">
      <el-card class="panel">
        <template #header>
          <div class="panel-head">
            <span>1. 上传与解析</span>
            <el-tag size="small" effect="plain">.dlis</el-tag>
          </div>
        </template>

        <el-form label-width="96px" class="form-grid">
          <el-form-item label="示例文件">
            <el-switch v-model="useDemo" active-text="使用内置样例" inactive-text="上传本地文件" />
          </el-form-item>

          <el-form-item label="上传文件">
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept=".dlis"
              :disabled="useDemo"
              :on-change="onFileChange"
            >
              <el-button plain :disabled="useDemo">选择 DLIS 文件</el-button>
            </el-upload>
            <span v-if="selectedFile" class="file-chip">{{ selectedFile.name }}</span>
            <el-button v-if="selectedFile && !useDemo" text type="danger" @click="clearFile">
              移除
            </el-button>
          </el-form-item>

          <el-form-item label="当前会话">
            <span class="session-text">{{ sessionId || '尚未解析' }}</span>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="inspecting" @click="inspectFile">
              {{ inspecting ? '解析中...' : '解析 DLIS 文件' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="panel">
        <template #header>
          <div class="panel-head">
            <span>2. 可视化参数</span>
            <el-tag size="small" effect="plain">自动推荐默认通道</el-tag>
          </div>
        </template>

        <el-form label-width="110px" class="form-grid">
          <el-form-item label="生成 ATV 图">
            <el-switch v-model="renderForm.generateAtv" />
          </el-form-item>
          <el-form-item label="生成玫瑰图">
            <el-switch v-model="renderForm.generateRose" />
          </el-form-item>

          <el-form-item label="振幅通道">
            <el-select
              v-model="renderForm.amplitudeChannelRef"
              filterable
              clearable
              class="wide"
              :disabled="!summary"
            >
              <el-option
                v-for="item in channelOptions"
                :key="item.channel_ref"
                :label="`${item.label} (${shapeText(item.shape)})`"
                :value="item.channel_ref"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="走时通道">
            <el-select
              v-model="renderForm.traveltimeChannelRef"
              filterable
              clearable
              class="wide"
              :disabled="!summary"
            >
              <el-option
                v-for="item in channelOptions"
                :key="item.channel_ref"
                :label="`${item.label} (${shapeText(item.shape)})`"
                :value="item.channel_ref"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="角度通道">
            <el-select
              v-model="renderForm.angleChannelRef"
              filterable
              clearable
              class="wide"
              :disabled="!summary"
            >
              <el-option
                v-for="item in channelOptions"
                :key="item.channel_ref"
                :label="`${item.label} (${shapeText(item.shape)})`"
                :value="item.channel_ref"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="深度范围(m)">
            <div class="inline-field">
              <el-input-number v-model="renderForm.depthMin" :precision="2" :step="0.5" />
              <span class="range-sep">~</span>
              <el-input-number v-model="renderForm.depthMax" :precision="2" :step="0.5" />
            </div>
          </el-form-item>

          <el-form-item label="像素放大">
            <el-input-number v-model="renderForm.pixelScale" :min="1" :max="8" />
          </el-form-item>
          <el-form-item label="Gamma">
            <el-input-number v-model="renderForm.gamma" :min="0.1" :max="3" :step="0.05" />
          </el-form-item>
          <el-form-item label="Clip Low">
            <el-input-number v-model="renderForm.clipLow" :min="0" :max="99" :step="0.5" />
          </el-form-item>
          <el-form-item label="Clip High">
            <el-input-number v-model="renderForm.clipHigh" :min="1" :max="100" :step="0.5" />
          </el-form-item>
          <el-form-item label="Rose Bins">
            <el-input-number v-model="renderForm.roseBins" :min="6" :max="180" />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" :loading="rendering" :disabled="!summary" @click="renderOutputs">
              {{ rendering ? '生成中...' : '生成可视化结果' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </section>

    <section v-if="summary" class="summary-grid">
      <el-card class="panel">
        <template #header>
          <div class="panel-head">
            <span>解析摘要</span>
            <el-tag size="small">{{ summary.file_name || 'DLIS 文件' }}</el-tag>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="默认振幅通道">
            {{ summary.defaults?.amplitude_channel_ref || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="默认走时通道">
            {{ summary.defaults?.traveltime_channel_ref || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="默认角度通道">
            {{ summary.defaults?.angle_channel_ref || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="深度范围">
            {{ depthRangeText(summary.defaults?.depth_min, summary.defaults?.depth_max) }}
          </el-descriptions-item>
          <el-descriptions-item label="帧数量">
            {{ summary.frames?.length || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="通道数量">
            {{ flatChannels.length }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="candidate-block">
          <div class="candidate-title">候选通道</div>
          <div class="candidate-row">
            <span class="candidate-label">振幅:</span>
            <el-tag
              v-for="item in topAmplitudeCandidates"
              :key="item.channel_ref"
              effect="plain"
              class="candidate-tag"
            >
              {{ item.channel_ref }}
            </el-tag>
          </div>
          <div class="candidate-row">
            <span class="candidate-label">走时:</span>
            <el-tag
              v-for="item in topTraveltimeCandidates"
              :key="item.channel_ref"
              effect="plain"
              class="candidate-tag"
            >
              {{ item.channel_ref }}
            </el-tag>
          </div>
          <div class="candidate-row">
            <span class="candidate-label">角度:</span>
            <el-tag
              v-for="item in topAngleCandidates"
              :key="item.channel_ref"
              effect="plain"
              class="candidate-tag"
            >
              {{ item.channel_ref }}
            </el-tag>
          </div>
        </div>
      </el-card>

      <el-card class="panel">
        <template #header>
          <div class="panel-head">
            <span>通道浏览</span>
            <span class="muted">前 60 个通道</span>
          </div>
        </template>
        <el-table :data="flatChannels.slice(0, 60)" height="360" size="small">
          <el-table-column prop="frame_name" label="Frame" min-width="90" />
          <el-table-column prop="channel_name" label="Channel" min-width="180" />
          <el-table-column prop="unit" label="Unit" width="90" />
          <el-table-column label="Shape" width="120">
            <template #default="{ row }">
              {{ shapeText(row.shape) }}
            </template>
          </el-table-column>
          <el-table-column label="特征" min-width="180">
            <template #default="{ row }">
              <el-tag v-if="row.is_amplitude_candidate" size="small" effect="plain" class="mini-tag">振幅</el-tag>
              <el-tag v-if="row.is_traveltime_candidate" size="small" effect="plain" class="mini-tag">走时</el-tag>
              <el-tag v-if="row.is_angle_candidate" size="small" effect="plain" class="mini-tag">角度</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <section v-if="outputs.length" class="results-section">
      <div class="results-header">
        <div>
          <h3>渲染结果</h3>
          <p>当前会话支持逐项预览和下载，结果会保留为 PNG + NPZ。</p>
        </div>
        <el-button
          v-if="downloadUrls?.manifest"
          plain
          @click="download(downloadUrls.manifest)"
        >
          下载 Manifest
        </el-button>
      </div>

      <div class="result-grid">
        <el-card v-for="item in outputs" :key="item.step_index" class="result-card">
          <template #header>
            <div class="panel-head">
              <span>{{ item.title }}</span>
              <el-tag size="small" effect="plain">{{ item.algo_id || item.kind }}</el-tag>
            </div>
          </template>

          <p class="result-summary">{{ item.summary }}</p>
          <div class="shape-note">形状: {{ shapeText(item.shape) }}</div>
          <img :src="item.output_image" :alt="item.title" class="result-image" />

          <div class="download-row">
            <el-button
              v-if="item.download_urls?.image"
              type="primary"
              plain
              size="small"
              @click="download(item.download_urls.image)"
            >
              下载图片
            </el-button>
            <el-button
              v-if="item.download_urls?.npz"
              type="success"
              plain
              size="small"
              @click="download(item.download_urls.npz)"
            >
              下载 NPZ
            </el-button>
          </div>
        </el-card>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { inspectDlis, renderDlis } from '@/api/dlis'

const useDemo = ref(false)
const selectedFile = ref(null)
const inspecting = ref(false)
const rendering = ref(false)
const sessionId = ref('')
const summary = ref(null)
const outputs = ref([])
const downloadUrls = ref(null)

const renderForm = ref({
  amplitudeChannelRef: '',
  traveltimeChannelRef: '',
  angleChannelRef: '',
  depthMin: null,
  depthMax: null,
  pixelScale: 2,
  clipLow: 1,
  clipHigh: 99,
  gamma: 0.85,
  roseBins: 36,
  generateAtv: true,
  generateRose: true,
})

const channelOptions = computed(() => summary.value?.channel_options || [])
const flatChannels = computed(() => {
  const frames = Array.isArray(summary.value?.frames) ? summary.value.frames : []
  return frames.flatMap((frame) => {
    const channels = Array.isArray(frame.channels) ? frame.channels : []
    return channels.map((item) => ({
      ...item,
      frame_name: frame.frame_name,
    }))
  })
})
const topAmplitudeCandidates = computed(() => (summary.value?.candidates?.amplitude || []).slice(0, 4))
const topTraveltimeCandidates = computed(() => (summary.value?.candidates?.traveltime || []).slice(0, 4))
const topAngleCandidates = computed(() => (summary.value?.candidates?.angle || []).slice(0, 4))

function onFileChange(file) {
  selectedFile.value = file?.raw || null
  sessionId.value = ''
  summary.value = null
  outputs.value = []
  downloadUrls.value = null
}

function clearFile() {
  selectedFile.value = null
}

function shapeText(shape) {
  if (!Array.isArray(shape) || !shape.length) return '-'
  return shape.join(' × ')
}

function depthRangeText(min, max) {
  if (typeof min !== 'number' || typeof max !== 'number') return '-'
  return `${min.toFixed(2)} m ~ ${max.toFixed(2)} m`
}

function applyDefaults(nextSummary) {
  const defaults = nextSummary?.defaults || {}
  renderForm.value = {
    ...renderForm.value,
    amplitudeChannelRef: defaults.amplitude_channel_ref || '',
    traveltimeChannelRef: defaults.traveltime_channel_ref || '',
    angleChannelRef: defaults.angle_channel_ref || '',
    depthMin: typeof defaults.depth_min === 'number' ? defaults.depth_min : null,
    depthMax: typeof defaults.depth_max === 'number' ? defaults.depth_max : null,
    pixelScale: defaults.pixel_scale || 2,
    clipLow: defaults.clip_low || 1,
    clipHigh: defaults.clip_high || 99,
    gamma: defaults.gamma || 0.85,
    roseBins: defaults.rose_bins || 36,
    generateAtv: true,
    generateRose: true,
  }
}

async function inspectFile() {
  if (!useDemo.value && !selectedFile.value) {
    ElMessage.warning('请先选择 DLIS 文件或启用内置样例')
    return
  }

  try {
    inspecting.value = true
    const formData = new FormData()
    if (useDemo.value) {
      formData.append('use_demo', 'true')
    } else if (selectedFile.value) {
      formData.append('dlis_file', selectedFile.value)
    }

    const data = await inspectDlis(formData)
    sessionId.value = data.session_id || ''
    summary.value = data.summary || null
    outputs.value = []
    downloadUrls.value = null
    if (summary.value) {
      applyDefaults(summary.value)
    }
    ElMessage.success('DLIS 文件解析完成')
  } catch (error) {
    const msg = error?.response?.data?.error || error?.message || 'DLIS 解析失败'
    ElMessage.error(msg)
  } finally {
    inspecting.value = false
  }
}

async function renderOutputs() {
  if (!summary.value && !sessionId.value) {
    ElMessage.warning('请先解析 DLIS 文件')
    return
  }
  if (!renderForm.value.generateAtv && !renderForm.value.generateRose) {
    ElMessage.warning('请至少选择一种输出')
    return
  }

  try {
    rendering.value = true
    const formData = new FormData()
    if (sessionId.value) {
      formData.append('session_id', sessionId.value)
    } else if (useDemo.value) {
      formData.append('use_demo', 'true')
    } else if (selectedFile.value) {
      formData.append('dlis_file', selectedFile.value)
    }

    formData.append('generate_atv', String(renderForm.value.generateAtv))
    formData.append('generate_rose', String(renderForm.value.generateRose))
    if (renderForm.value.amplitudeChannelRef) {
      formData.append('amplitude_channel_ref', renderForm.value.amplitudeChannelRef)
    }
    if (renderForm.value.traveltimeChannelRef) {
      formData.append('traveltime_channel_ref', renderForm.value.traveltimeChannelRef)
    }
    if (renderForm.value.angleChannelRef) {
      formData.append('angle_channel_ref', renderForm.value.angleChannelRef)
    }
    if (renderForm.value.depthMin !== null && renderForm.value.depthMin !== undefined) {
      formData.append('depth_min', String(renderForm.value.depthMin))
    }
    if (renderForm.value.depthMax !== null && renderForm.value.depthMax !== undefined) {
      formData.append('depth_max', String(renderForm.value.depthMax))
    }
    formData.append('pixel_scale', String(renderForm.value.pixelScale))
    formData.append('clip_low', String(renderForm.value.clipLow))
    formData.append('clip_high', String(renderForm.value.clipHigh))
    formData.append('gamma', String(renderForm.value.gamma))
    formData.append('rose_bins', String(renderForm.value.roseBins))

    const data = await renderDlis(formData)
    sessionId.value = data.session_id || sessionId.value
    summary.value = data.summary || summary.value
    outputs.value = Array.isArray(data.outputs) ? data.outputs : []
    downloadUrls.value = data.download_urls || null
    ElMessage.success('DLIS 可视化结果已生成')
  } catch (error) {
    const msg = error?.response?.data?.error || error?.message || 'DLIS 渲染失败'
    ElMessage.error(msg)
  } finally {
    rendering.value = false
  }
}

function download(urlPath) {
  const href = urlPath.startsWith('/api') ? urlPath : `/api${urlPath}`
  window.open(href, '_blank')
}
</script>

<style scoped>
.dlis-page {
  --ink: #172033;
  --muted: #66758a;
  --line: #d9e2ef;
  --accent: #c96e1e;
  --accent-soft: #fff2df;
  display: grid;
  gap: 18px;
}

.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 28px;
  border-radius: 18px;
  color: #fff7ef;
  background:
    radial-gradient(circle at 0% 0%, rgba(255, 211, 122, 0.3), transparent 38%),
    radial-gradient(circle at 100% 100%, rgba(255, 169, 77, 0.24), transparent 35%),
    linear-gradient(135deg, #281204 0%, #4d2505 45%, #1f1006 100%);
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 241, 217, 0.72);
}

.hero h2 {
  margin: 0;
  font-size: 28px;
}

.hero-copy {
  margin: 10px 0 0;
  max-width: 720px;
  color: rgba(255, 245, 230, 0.82);
  line-height: 1.7;
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.meta-pill {
  padding: 10px 12px;
  border: 1px solid rgba(255, 214, 158, 0.26);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #fff2df;
  font-size: 12px;
  white-space: nowrap;
}

.workbench,
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.panel {
  border-radius: 16px;
  border: 1px solid var(--line);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.form-grid {
  padding: 6px 2px;
}

.wide {
  width: 100%;
}

.file-chip {
  margin-left: 10px;
  color: var(--ink);
  font-size: 12px;
}

.session-text,
.muted {
  color: var(--muted);
  font-size: 12px;
}

.inline-field {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.range-sep {
  color: var(--muted);
}

.candidate-block {
  margin-top: 16px;
  padding: 14px;
  border-radius: 12px;
  background: linear-gradient(180deg, #fff8ee 0%, #fffdf8 100%);
}

.candidate-title {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.candidate-row + .candidate-row {
  margin-top: 8px;
}

.candidate-label {
  display: inline-block;
  min-width: 42px;
  color: var(--muted);
  font-size: 12px;
}

.candidate-tag,
.mini-tag {
  margin-right: 6px;
  margin-bottom: 6px;
}

.results-section {
  display: grid;
  gap: 14px;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.results-header h3 {
  margin: 0;
  color: var(--ink);
}

.results-header p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
}

.result-card {
  border-radius: 16px;
}

.result-summary {
  margin: 0 0 8px;
  color: var(--ink);
  line-height: 1.6;
}

.shape-note {
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--muted);
}

.result-image {
  display: block;
  width: 100%;
  border-radius: 12px;
  border: 1px solid #efe1cf;
  background: #fffaf4;
}

.download-row {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 1080px) {
  .hero,
  .workbench,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .hero {
    flex-direction: column;
  }

  .hero-meta {
    justify-content: flex-start;
  }
}
</style>
