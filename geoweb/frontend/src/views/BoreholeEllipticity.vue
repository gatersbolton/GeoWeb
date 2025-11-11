<template>
  <div class="borehole-container">
    <div class="header">
      <h2>钻孔椭圆度项目</h2>
      <p class="description">使用声学成像测井(ATV)数据计算钻孔横截面椭圆度</p>
    </div>

    <!-- 步骤指示器 -->
    <div class="steps-container">
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step title="计算参数设置" description="输入计算所需的参数和文件"></el-step>
        <el-step title="计算结果" description="查看计算结果并下载文件"></el-step>
        <el-step title="可视化参数设置" description="设置可视化参数"></el-step>
        <el-step title="可视化结果" description="查看生成的图表"></el-step>
      </el-steps>
    </div>

    <div class="content-wrapper">
      <!-- 步骤1: 计算参数设置 -->
      <div v-if="currentStep === 0" class="step-panel">
        <el-card class="card">
          <template #header>
            <span class="card-header">计算参数设置</span>
          </template>

          <!-- 演示数据选项 -->
          <div class="demo-option">
            <el-checkbox v-model="useDemo" @change="handleDemoToggle">
              使用默认演示数据（无需上传文件）
            </el-checkbox>
          </div>

          <!-- 文件上传区域 -->
          <div v-if="!useDemo" class="input-sections">
            <!-- 必需文件 -->
            <div class="input-column">
              <div class="section">
                <h4>必需文件 <span class="required">*</span></h4>
                <div class="upload-item">
                  <label>ATV行程时间日志 (TT_NM.csv)</label>
                  <el-upload
                    class="upload-demo"
                    drag
                    :auto-upload="false"
                    :show-file-list="true"
                    :on-change="handleTTChange"
                    :before-upload="() => false"
                    accept=".csv"
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">将CSV文件拖到此处，或<em>点击上传</em></div>
                  </el-upload>
                </div>
              </div>
            </div>

            <!-- 可选文件 -->
            <div class="input-column">
              <div class="section">
                <h4>可选文件</h4>
                <div class="upload-item">
                  <label>声学窗口行程时间日志 (WNDTIME.csv)</label>
                  <el-upload
                    class="upload-demo"
                    drag
                    :auto-upload="false"
                    :show-file-list="true"
                    :on-change="handleWTTChange"
                    :before-upload="() => false"
                    accept=".csv"
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">将CSV文件拖到此处，或<em>点击上传</em></div>
                  </el-upload>
                </div>

                <div class="upload-item">
                  <label>掩码文件 (用于排除部分数据)</label>
                  <el-upload
                    class="upload-demo"
                    drag
                    :auto-upload="false"
                    :show-file-list="true"
                    :on-change="handleMaskChange"
                    :before-upload="() => false"
                    accept=".csv"
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">将CSV文件拖到此处，或<em>点击上传</em></div>
                  </el-upload>
                </div>
              </div>
            </div>

            <!-- 参数设置 -->
            <div class="input-column">
              <div class="section">
                <h4>参数设置</h4>
                <el-form :model="calculateParams" label-width="140px" class="param-form">
                  <el-form-item label="ATV工具声学头半径 (m)">
                    <el-input-number
                      v-model="calculateParams.rp"
                      :precision="4"
                      :step="0.001"
                      :min="0"
                      placeholder="0.019"
                      size="small"
                    />
                  </el-form-item>

                  <el-form-item label="钻孔流体声速 (m/s)">
                    <el-input-number
                      v-model="calculateParams.vf"
                      :precision="0"
                      :step="10"
                      :min="0"
                      placeholder="1480"
                      size="small"
                    />
                  </el-form-item>

                  <el-form-item label="固定AWT值 (无AWT日志时)">
                    <el-input-number
                      v-model="calculateParams.wtt"
                      :precision="4"
                      :step="0.1"
                      placeholder="留空则使用AWT日志"
                      size="small"
                    />
                  </el-form-item>

                  <el-form-item label="单位转换乘数">
                    <el-input-number
                      v-model="calculateParams.beta"
                      :precision="4"
                      :step="0.1"
                      placeholder="留空则不转换"
                      size="small"
                    />
                  </el-form-item>
                </el-form>
              </div>
            </div>
          </div>

          <!-- 参数设置（演示模式） -->
          <div v-if="useDemo" class="demo-params">
            <el-form :model="calculateParams" label-width="140px" class="param-form">
              <el-form-item label="ATV工具声学头半径 (m)">
                <el-input-number
                  v-model="calculateParams.rp"
                  :precision="4"
                  :step="0.001"
                  :min="0"
                  size="small"
                />
              </el-form-item>

              <el-form-item label="钻孔流体声速 (m/s)">
                <el-input-number
                  v-model="calculateParams.vf"
                  :precision="0"
                  :step="10"
                  :min="0"
                  size="small"
                />
              </el-form-item>
            </el-form>
          </div>

          <el-button
            type="primary"
            size="large"
            :disabled="!useDemo && !files.tt || calculateProgress.processing"
            :loading="calculateProgress.processing"
            @click="handleCalculate"
            class="process-btn"
          >
            {{ calculateProgress.processing ? '计算中...' : '开始计算' }}
          </el-button>
        </el-card>

        <!-- 进度监控组件 -->
        <ProgressMonitor
          v-if="showProgressMonitor"
          :session-id="currentSessionId"
          :visible="showProgressMonitor"
          @close="closeProgressMonitor"
          @completed="onCalculationCompleted"
          @error="onCalculationError"
          @retry="retryCalculation"
        />
      </div>

      <!-- 步骤2: 计算结果 -->
      <div v-if="currentStep === 1" class="step-panel">
        <el-card class="card">
          <template #header>
            <span class="card-header">计算结果</span>
          </template>

          <div v-if="calculateResult" class="calculation-result">
            <div class="result-summary">
              <h4>计算完成</h4>
              <p>Session ID: {{ calculateResult.session_id }}</p>
              <p>处理的数据点数: {{ calculateResult.summary?.data_points || 'N/A' }}</p>
            </div>

            <!-- 下载计算结果文件 -->
            <div class="download-section">
              <h4>下载计算结果文件</h4>
              <div class="download-links">
                <el-button
                  v-for="(url, key) in calculateResult.download_urls"
                  :key="key"
                  type="primary"
                  link
                  @click="downloadFile(url, key + '.csv')"
                  class="download-btn"
                >
                  <el-icon><Document /></el-icon>
                  {{ key.replace(/_/g, ' ') }}.csv
                </el-button>
              </div>
            </div>

            <div class="step-actions">
              <el-button @click="currentStep = 0">返回参数设置</el-button>
              <el-button type="primary" @click="currentStep = 2">继续可视化</el-button>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 步骤3: 可视化参数设置 -->
      <div v-if="currentStep === 2" class="step-panel">
        <el-card class="card">
          <template #header>
            <span class="card-header">可视化参数设置</span>
          </template>

          <!-- 可视化演示数据选项 -->
          <div class="demo-option">
            <el-checkbox v-model="useVizDemo" @change="handleVizDemoToggle">
              使用默认可视化演示数据（包含振幅、倾斜角、方位角数据）
            </el-checkbox>
          </div>

          <!-- 可视化文件上传 -->
          <div v-if="!useVizDemo" class="viz-input-sections">
            <div class="input-column">
              <div class="section">
                <h4>可视化数据文件（可选）</h4>
                <div class="upload-item">
                  <label>声学振幅文件 (AMP.csv)</label>
                  <el-upload
                    class="upload-demo"
                    drag
                    :auto-upload="false"
                    :show-file-list="true"
                    :on-change="handleAmpChange"
                    :before-upload="() => false"
                    accept=".csv"
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">将CSV文件拖到此处，或<em>点击上传</em></div>
                  </el-upload>
                </div>

                <div class="upload-item">
                  <label>倾斜角文件 (TILT.csv)</label>
                  <el-upload
                    class="upload-demo"
                    drag
                    :auto-upload="false"
                    :show-file-list="true"
                    :on-change="handleIncChange"
                    :before-upload="() => false"
                    accept=".csv"
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">将CSV文件拖到此处，或<em>点击上传</em></div>
                  </el-upload>
                </div>

                <div class="upload-item">
                  <label>方位角文件 (AZIMUTH.csv)</label>
                  <el-upload
                    class="upload-demo"
                    drag
                    :auto-upload="false"
                    :show-file-list="true"
                    :on-change="handleAziChange"
                    :before-upload="() => false"
                    accept=".csv"
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">将CSV文件拖到此处，或<em>点击上传</em></div>
                  </el-upload>
                </div>
              </div>
            </div>

            <div class="input-column">
              <div class="section">
                <h4>可视化参数</h4>
                <el-form :model="visualizeParams" label-width="120px" class="param-form">
                  <el-form-item label="深度间隔 (dz)">
                    <el-input-number
                      v-model="visualizeParams.dz"
                      :precision="2"
                      :step="0.1"
                      placeholder="自动计算"
                      size="small"
                    />
                  </el-form-item>

                  <el-form-item label="深度窗口 (lenZ)">
                    <el-input-number
                      v-model="visualizeParams.lenZ"
                      :precision="0"
                      :step="1"
                      :min="1"
                      size="small"
                    />
                  </el-form-item>

                  <el-form-item label="振幅色图">
                    <el-select v-model="visualizeParams.cmapAmp" size="small">
                      <el-option label="灰度" value="gray"></el-option>
                      <el-option label="热力图" value="hot"></el-option>
                      <el-option label="彩虹" value="viridis"></el-option>
                    </el-select>
                  </el-form-item>

                  <el-form-item label="半径色图">
                    <el-select v-model="visualizeParams.cmapRad" size="small">
                      <el-option label="反向灰度" value="gray_r"></el-option>
                      <el-option label="蓝色" value="Blues"></el-option>
                      <el-option label="红色" value="Reds"></el-option>
                    </el-select>
                  </el-form-item>
                </el-form>
              </div>
            </div>
          </div>

          <!-- 可视化参数（演示模式） -->
          <div v-if="useVizDemo" class="demo-params">
            <el-form :model="visualizeParams" label-width="120px" class="param-form">
              <el-form-item label="深度间隔 (dz)">
                <el-input-number
                  v-model="visualizeParams.dz"
                  :precision="2"
                  :step="0.1"
                  placeholder="自动计算"
                  size="small"
                />
              </el-form-item>

              <el-form-item label="深度窗口 (lenZ)">
                <el-input-number
                  v-model="visualizeParams.lenZ"
                  :precision="0"
                  :step="1"
                  :min="1"
                  size="small"
                />
              </el-form-item>

              <el-form-item label="振幅色图">
                <el-select v-model="visualizeParams.cmapAmp" size="small">
                  <el-option label="灰度" value="gray"></el-option>
                  <el-option label="热力图" value="hot"></el-option>
                  <el-option label="彩虹" value="viridis"></el-option>
                </el-select>
              </el-form-item>

              <el-form-item label="半径色图">
                <el-select v-model="visualizeParams.cmapRad" size="small">
                  <el-option label="反向灰度" value="gray_r"></el-option>
                  <el-option label="蓝色" value="Blues"></el-option>
                  <el-option label="红色" value="Reds"></el-option>
                </el-select>
              </el-form-item>
            </el-form>
          </div>

          <div class="step-actions">
            <el-button @click="currentStep = 1">返回计算结果</el-button>
            <el-button
              type="primary"
              :loading="visualizeProgress.processing"
              @click="handleVisualize"
            >
              {{ visualizeProgress.processing ? '生成图表中...' : '生成可视化' }}
            </el-button>
          </div>
        </el-card>
      </div>

      <!-- 步骤4: 可视化结果 -->
      <div v-if="currentStep === 3" class="step-panel">
        <el-card class="card">
          <template #header>
            <span class="card-header">可视化结果</span>
          </template>

          <div v-if="visualizeResult" class="visualization-result">
            <div class="visualization-layout">
              <!-- 左侧纵向深度滑条 -->
              <div class="depth-slider">
              <div class="slider-wrapper" v-if="meta && meta.zMin !== undefined && meta.zMax !== undefined" :style="{'--depthPct': depthPct + '%'}">
                  <el-slider
                    vertical
                    v-model="sliderValue"
                    :min="0"
                    :max="maxDepth"
                    :step="meta.dz || 0.1"
                    height="70vh"
                    :format-tooltip="formatDepthTooltip"
                    @input="onDepthInput"
                    @change="onDepthChange"
                  />
                </div>
                <div v-else class="depth-slider-placeholder">加载深度范围...</div>
              </div>

              <!-- 右侧主要图表展示区域 -->
              <div class="plots-grid">
                <!-- 椭圆度参数图（随窗口动态刷新） -->
                <div v-if="visualizeResult.ellipticity_plot" class="result-section wide-plot">
                  <h4>
                    椭圆度参数随深度变化
                    <small v-if="windowInfo">（{{ windowInfo.zTop.toFixed(2) }} - {{ windowInfo.zBottom.toFixed(2) }} m）</small>
                  </h4>
                  <div class="plot-container" :class="{ preview: isPreview }">
                    <div v-if="previewLoading" class="loading-hint">预览渲染中...</div>
                    <img :src="visualizeResult.ellipticity_plot" alt="椭圆度参数图表" />
                  </div>
                </div>

                <!-- 方向分布图并排显示（可选择保持全局，不随窗口变化） -->
                <div class="plots-row">
                  <div v-if="visualizeResult.polar_plot" class="result-section half-plot">
                    <h4>椭圆主轴方向分布（全局）</h4>
                    <div class="plot-container">
                      <img :src="visualizeResult.polar_plot" alt="极坐标方向图" />
                    </div>
                  </div>

                  <div v-if="visualizeResult.orientation_plot" class="result-section half-plot">
                    <h4>椭圆轴方位角极坐标分布（全局）</h4>
                    <div class="plot-container">
                      <img :src="visualizeResult.orientation_plot" alt="椭圆轴方位角极坐标分布图" />
                    </div>
                  </div>
                </div>

                <div v-if="visualizeResult.atv_imaging_plot" class="result-section wide-plot">
                  <h4>ATV成像数据可视化</h4>
                  <div class="plot-container">
                    <img :src="visualizeResult.atv_imaging_plot" alt="ATV成像数据" />
                  </div>
                </div>
              </div>
            </div>

            <div class="step-actions">
              <el-button @click="currentStep = 2">返回参数设置</el-button>
              <el-button @click="resetWorkflow">重新开始</el-button>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { UploadFilled, Document } from '@element-plus/icons-vue'
import { calculateBoreholeEllipticity, visualizeBoreholeEllipticity } from '@/api/borehole'
import { ElMessage } from 'element-plus'
import ProgressMonitor from '@/components/ProgressMonitor.vue'
import axios from 'axios'

let pendingController = null
function cancelPending() {
  if (pendingController) {
    pendingController.abort()
    pendingController = null
  }
}

// 当前步骤
const currentStep = ref(0)

// 是否使用演示数据
const useDemo = ref(false)

// 是否使用可视化演示数据
const useVizDemo = ref(false)

// 文件数据
const files = reactive({
  tt: null,      // 必需的行程时间文件
  wtt: null,     // 可选的声学窗口时间文件
  mask: null,    // 可选的掩码文件
  amp: null,     // 可视化：声学振幅文件
  inc: null,     // 可视化：倾斜角文件
  azi: null      // 可视化：方位角文件
})

// 计算参数
const calculateParams = reactive({
  rp: 0.019,     // ATV工具声学头半径
  vf: 1480,      // 钻孔流体声速
  wtt: null,     // 固定AWT值
  beta: null     // 单位转换乘数
})

// 可视化参数
const visualizeParams = reactive({
  dz: null,      // 深度间隔
  lenZ: 5,       // 深度窗口
  cmapAmp: 'gray',   // 振幅色图
  cmapRad: 'gray_r'  // 半径色图
})

// 深度窗口与元数据
const meta = reactive({ zMin: null, zMax: null, dz: null })
const zTop = ref(null)
const isPreview = ref(false)
const windowInfo = ref(null)
const previewLoading = ref(false)
// 深度映射：将真实深度 depth（0 在顶部）与 EP 控件值分离
const maxDepth = ref(0)        // 允许的最大相对深度（= zMax - zMin - lenZ）
const depth = ref(0)           // 真实相对深度（0 at top）
const sliderValue = ref(0)     // 控件值 = maxDepth - depth
const depthPct = computed(() => {
  if (!maxDepth.value || maxDepth.value <= 0) return 0
  return (depth.value / maxDepth.value) * 100
})

function formatDepthTooltip(v) {
  if (v == null) return ''
  // 将 EP 竖向滑块的值（上=最大，下=最小）映射为真实“绝对深度 zTop”
  const md = Number(maxDepth.value) || 0
  const d  = md - Number(v || 0)                 // 真实“相对深度”（上=0）
  const nd = d < 0 ? 0 : (d > md ? md : d)       // clamp 到 [0, maxDepth]
  const z0 = (meta.zMin != null) ? Number(meta.zMin) : 0
  const zAbs = z0 + nd                           // 绝对深度 = zMin + 相对深度
  return `${zAbs.toFixed(2)} m`
}

// 工具函数：钳制
function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v))
}

// 当滑块值变化时（用户拖动） -> 更新真实深度 depth 与 zTop
watch(sliderValue, (sv) => {
  const md = Number(maxDepth.value) || 0
  const d = clamp(md - Number(sv), 0, md)   // 约定：sliderValue = maxDepth - depth
  if (d !== depth.value) depth.value = d
  if (meta.zMin != null) {
    const zt = Number(meta.zMin) + d
    if (zt !== zTop.value) {
      zTop.value = zt
      windowInfo.value = { zTop: zt, zBottom: zt + Number(visualizeParams.lenZ) }
    }
  }
})

// 当 zTop（例如服务端回写或其他操作）变化时 -> 反向更新 depth 与 sliderValue
watch([zTop, maxDepth, () => meta.zMin], () => {
  if (zTop.value == null || meta.zMin == null) return
  const md = Number(maxDepth.value) || 0
  const d = clamp(Number(zTop.value) - Number(meta.zMin), 0, md)
  if (d !== depth.value) depth.value = d
  const sv = md - d
  if (sv !== sliderValue.value) sliderValue.value = sv
})

// 使用 CSS 旋转实现上浅下深，滑条数值与 zTop 保持一致

// 处理状态
const calculateProgress = reactive({
  processing: false
})

const visualizeProgress = reactive({
  processing: false
})

// 结果数据
const calculateResult = ref(null)
const visualizeResult = ref(null)

// 进度监控相关
const showProgressMonitor = ref(false)
const currentSessionId = ref('')

// 演示数据切换
function handleDemoToggle() {
  if (useDemo.value) {
    // 清空文件选择
    Object.keys(files).forEach(key => {
      files[key] = null
    })
  }
}

// 可视化演示数据切换
function handleVizDemoToggle() {
  if (useVizDemo.value) {
    // 清空可视化文件选择
    files.amp = null
    files.inc = null
    files.azi = null
  }
}

// 文件上传处理函数
function handleTTChange(uploadFile) {
  files.tt = uploadFile.raw
  ElMessage.success(`TT文件已选择: ${uploadFile.name}`)
}

function handleWTTChange(uploadFile) {
  files.wtt = uploadFile.raw
  ElMessage.success(`WTT文件已选择: ${uploadFile.name}`)
}

function handleMaskChange(uploadFile) {
  files.mask = uploadFile.raw
  ElMessage.success(`掩码文件已选择: ${uploadFile.name}`)
}

function handleAmpChange(uploadFile) {
  files.amp = uploadFile.raw
  ElMessage.success(`振幅文件已选择: ${uploadFile.name}`)
}

function handleIncChange(uploadFile) {
  files.inc = uploadFile.raw
  ElMessage.success(`倾斜角文件已选择: ${uploadFile.name}`)
}

function handleAziChange(uploadFile) {
  files.azi = uploadFile.raw
  ElMessage.success(`方位角文件已选择: ${uploadFile.name}`)
}

// 执行计算
async function handleCalculate() {
  if (!useDemo.value && !files.tt) {
    ElMessage.error('请上传ATV行程时间日志文件或选择使用演示数据')
    return
  }

  calculateProgress.processing = true

  try {
    const formData = new FormData()

    // 添加文件（如果不使用演示数据）
    if (!useDemo.value) {
      formData.append('tt_file', files.tt)
      if (files.wtt) formData.append('wtt_file', files.wtt)
      if (files.mask) formData.append('mask_file', files.mask)
    } else {
      formData.append('use_demo', 'true')
    }

    // 添加参数
    formData.append('rp', calculateParams.rp)
    formData.append('vf', calculateParams.vf)

    if (calculateParams.wtt !== null) {
      formData.append('wtt', calculateParams.wtt)
    }

    if (calculateParams.beta !== null) {
      formData.append('beta', calculateParams.beta)
    }

    // 调用异步计算API
    const response = await axios.post('http://localhost:8000/borehole/calculate_async', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    if (response.data.session_id) {
      currentSessionId.value = response.data.session_id
      showProgressMonitor.value = true
      ElMessage.success('计算已开始，请查看进度监控')
    } else {
      throw new Error('未获取到session_id')
    }
  } catch (error) {
    console.error('启动计算失败:', error)
    ElMessage.error('启动计算失败，请检查参数设置')
    calculateProgress.processing = false
  }
}

// 执行可视化
async function handleVisualize() {
  if (!calculateResult.value?.session_id) {
    ElMessage.error('请先完成计算步骤')
    return
  }

  visualizeProgress.processing = true
  let vizLoadingMsg = null

  try {
    const formData = new FormData()
    formData.append('session_id', calculateResult.value.session_id)

    // 添加可视化文件（如果不使用演示数据）
    if (!useVizDemo.value) {
      if (files.amp) formData.append('amp_file', files.amp)
      if (files.inc) formData.append('inc_file', files.inc)
      if (files.azi) formData.append('azi_file', files.azi)
    } else {
      formData.append('use_viz_demo', 'true')
    }

    // 添加可视化参数
    if (visualizeParams.dz !== null) {
      formData.append('dz', visualizeParams.dz)
    }
    formData.append('lenZ', visualizeParams.lenZ)
    formData.append('cmapAmp', visualizeParams.cmapAmp)
    formData.append('cmapRad', visualizeParams.cmapRad)

    // 初次渲染采用 final 质量，并获取元信息
    formData.append('quality', 'final')

    // 持续提示
    vizLoadingMsg = ElMessage({ message: '正在生成可视化图表，请稍候...', type: 'info', duration: 0, showClose: true })
    const res = await visualizeBoreholeEllipticity(formData)
    visualizeResult.value = res

    // 初始化元数据与滑条
    if (res.meta) {
      meta.zMin = res.meta.zMin
      meta.zMax = res.meta.zMax
      meta.dz = res.meta.dz
      const win = res.meta.window
      if (win && win.zTop != null) {
        zTop.value = win.zTop
        windowInfo.value = { zTop: win.zTop, zBottom: win.zBottom }
      } else {
        zTop.value = meta.zMin
        windowInfo.value = { zTop: meta.zMin, zBottom: meta.zMin + visualizeParams.lenZ }
      }
      // 初始化 maxDepth / depth / sliderValue
      if (meta.zMin != null && meta.zMax != null) {
        const span = Number(meta.zMax) - Number(meta.zMin) - Number(visualizeParams.lenZ)
        maxDepth.value = span > 0 ? span : 0
        depth.value = (zTop.value != null && meta.zMin != null) ? (Number(zTop.value) - Number(meta.zMin)) : 0
        if (depth.value < 0) depth.value = 0
        if (depth.value > maxDepth.value) depth.value = maxDepth.value
        sliderValue.value = maxDepth.value - depth.value
      }
    }

    currentStep.value = 3
    ElMessage.success('可视化生成完成！')
  } catch (error) {
    console.error('可视化失败:', error)
    ElMessage.error('可视化生成失败，请检查参数设置')
  } finally {
    if (vizLoadingMsg && typeof vizLoadingMsg.close === 'function') vizLoadingMsg.close()
    visualizeProgress.processing = false
  }
}

// 滑动预览请求（节流/取消）
let previewTimer = null
async function requestPreview() {
  if (!calculateResult.value?.session_id || zTop.value == null) return
  const formData = new FormData()
  formData.append('session_id', calculateResult.value.session_id)
  formData.append('lenZ', visualizeParams.lenZ)
  formData.append('cmapAmp', visualizeParams.cmapAmp)
  formData.append('cmapRad', visualizeParams.cmapRad)
  formData.append('quality', 'preview')
  formData.append('zTop', zTop.value)
  if (visualizeParams.dz !== null) formData.append('dz', visualizeParams.dz)

  try {
    cancelPending()
    pendingController = new AbortController()
    previewLoading.value = true
    const res = await axios.post('/api/borehole/visualize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      signal: pendingController.signal,
      timeout: 300000,
    })
    if (res?.data) {
      visualizeResult.value.ellipticity_plot = res.data.ellipticity_plot
      if (res.data.meta?.window) {
        windowInfo.value = res.data.meta.window
        // 同步后端修正回来的 window（若后端对 zTop 进行了边界修正）
        if (typeof res.data.meta.window.zTop === 'number') {
          const serverZTop = Number(res.data.meta.window.zTop)
          if (!Number.isNaN(serverZTop)) {
            zTop.value = serverZTop
          }
        }
      }
      isPreview.value = true
    }
  } catch (e) {
    if (e.name !== 'CanceledError' && e.message !== 'canceled') {
      console.warn('预览请求失败', e)
    }
  }
  finally {
    previewLoading.value = false
  }
}

function onDepthInput() {
  // 节流 200ms
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(() => {
    // sliderValue -> depth -> zTop 已通过 watch 同步，这里直接请求预览
    requestPreview()
  }, 200)
}

async function onDepthChange() {
  // 释放后请求最终质量版本
  isPreview.value = false
  if (!calculateResult.value?.session_id || zTop.value == null) return
  const formData = new FormData()
  formData.append('session_id', calculateResult.value.session_id)
  formData.append('lenZ', visualizeParams.lenZ)
  formData.append('cmapAmp', visualizeParams.cmapAmp)
  formData.append('cmapRad', visualizeParams.cmapRad)
  formData.append('quality', 'final')
  formData.append('zTop', zTop.value)
  if (visualizeParams.dz !== null) formData.append('dz', visualizeParams.dz)

  try {
    const res = await visualizeBoreholeEllipticity(formData)
    if (res) {
      visualizeResult.value.ellipticity_plot = res.ellipticity_plot
      if (res.meta?.window) windowInfo.value = res.meta.window
    }
  } catch (e) {
    console.warn('最终渲染失败', e)
  }
}

// 下载文件
function downloadFile(url, filename) {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// 进度监控事件处理
function closeProgressMonitor() {
  showProgressMonitor.value = false
  calculateProgress.processing = false
}

async function onCalculationCompleted(data) {
  try {
    // 获取计算结果
    const response = await axios.get(`http://localhost:8000/borehole/result/${currentSessionId.value}`)
    calculateResult.value = response.data
    currentStep.value = 1
    calculateProgress.processing = false
    showProgressMonitor.value = false
    ElMessage.success('计算完成！')
  } catch (error) {
    console.error('获取计算结果失败:', error)
    ElMessage.error('获取计算结果失败')
    calculateProgress.processing = false
  }
}

function onCalculationError(data) {
  calculateProgress.processing = false
  showProgressMonitor.value = false
  ElMessage.error(`计算失败: ${data.message || '未知错误'}`)
}

function retryCalculation() {
  showProgressMonitor.value = false
  calculateProgress.processing = false
  // 可以在这里重新触发计算
  handleCalculate()
}




// 重置工作流
function resetWorkflow() {
  currentStep.value = 0
  calculateResult.value = null
  visualizeResult.value = null
  useDemo.value = false
  useVizDemo.value = false
  showProgressMonitor.value = false
  currentSessionId.value = ''

  // 清空文件
  Object.keys(files).forEach(key => {
    files[key] = null
  })

  // 重置参数
  calculateParams.rp = 0.019
  calculateParams.vf = 1480
  calculateParams.wtt = null
  calculateParams.beta = null

  visualizeParams.dz = null
  // 新增：取消预览与滑条状态重置
  cancelPending()
  meta.zMin = null
  meta.zMax = null
  meta.dz = null
  zTop.value = null
  windowInfo.value = null
  isPreview.value = false

  visualizeParams.lenZ = 5
  visualizeParams.cmapAmp = 'gray'
  visualizeParams.cmapRad = 'gray_r'
}
</script>

<style scoped>
.borehole-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h2 {
  color: #303133;
  margin-bottom: 10px;
}

.description {
  color: #606266;
  font-size: 14px;
}

.steps-container {
  margin-bottom: 30px;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.step-panel {
  width: 100%;
}

.card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  font-weight: 600;
  color: #303133;
}

.demo-option {
  margin-bottom: 25px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.input-sections, .viz-input-sections {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 25px;
  align-items: flex-start;
  margin-bottom: 25px;
}

.demo-params {
  margin-bottom: 25px;
}

.input-column {
  min-width: 0;
}

.section {
  margin-bottom: 25px;
}

.section h4 {
  color: #303133;
  margin-bottom: 15px;
  font-size: 16px;
}

.required {
  color: #f56c6c;
}

.upload-item {
  margin-bottom: 20px;
}

.upload-item label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.upload-demo {
  width: 100%;
}

:deep(.el-upload-dragger) {
  padding: 20px;
}

.param-form {
  margin-top: 10px;
}

.process-btn {
  width: 100%;
  margin-top: 20px;
}

.calculation-result, .visualization-result {
  padding: 20px 0;
}
.visualization-result { width: 100%; }
.plots-grid { width: 100%; }

.result-summary {
  background-color: #f0f9ff;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.result-summary h4 {
  color: #303133;
  margin-bottom: 10px;
}

.visualization-layout {
  display: grid;
  grid-template-columns: 56px 1fr;
  gap: 12px;
  align-items: flex-start;
}
.depth-slider {
  display: flex;
  align-items: center;
  justify-content: center;
}
.depth-slider :deep(.el-slider) {
  margin: 0;
}
.slider-wrapper { /* 使用 CSS 变量实现上半段着色 */ }
.depth-slider :deep(.el-slider.is-vertical .el-slider__bar) {
  background: transparent !important;
}
.depth-slider :deep(.el-slider.is-vertical .el-slider__runway) {
  background: linear-gradient(
    to bottom,
    #1677ff 0%,
    #1677ff var(--depthPct),
    #e8f1ff var(--depthPct),
    #e8f1ff 100%
  ) !important;
}
.plot-container img {
  max-width: 100%;
  height: auto;
  display: block;
}

.download-section {
  margin-bottom: 30px;
  border-top: 1px solid #e4e7ed;
  padding-top: 20px;
}

.download-section h4 {
  color: #303133;
  margin-bottom: 15px;
  font-size: 16px;
  font-weight: 600;
}

.download-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.download-btn {
  margin-right: 10px;
  margin-bottom: 10px;
}

.result-section {
  margin-bottom: 30px;
}

.result-section h4 {
  color: #303133;
  margin-bottom: 15px;
  font-size: 16px;
  font-weight: 600;
}

.plot-container {
  text-align: center;
  margin-bottom: 15px;
  background: #fafafa;
  border-radius: 8px;
  padding: 15px;
  border: 1px solid #e4e7ed;
}

.plot-container img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background: white;
}

.step-actions {
  margin-top: 20px;
  text-align: center;
}

.step-actions .el-button {
  margin: 0 10px;
}

@media (max-width: 1200px) {
  .input-sections, .viz-input-sections {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}

@media (max-width: 768px) {
  .borehole-container {
    padding: 15px;
  }

  .content-wrapper {
    gap: 20px;
  }

.visualization-layout {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 16px;
}
.depth-slider {
  display: flex;
  align-items: center;
  justify-content: center;
}
.depth-slider-placeholder {
  writing-mode: vertical-rl;
  color: #999;
}
.plot-container.preview img { opacity: 0.8; filter: saturate(0.8); }


  .input-sections, .viz-input-sections {
    gap: 15px;
  }

  .param-form .el-form-item {
    margin-bottom: 16px;
  }

  .param-form .el-form-item__label {
    font-size: 13px;
  }

  .step-actions .el-button {
    margin: 5px;
  }
}
.loading-hint {
  position: absolute;
  top: 8px;
  right: 12px;
  background: rgba(0,0,0,0.5);
  color: #fff;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}
</style>