<template>
  <div class="page">
    <div class="header">
      <h2>数据增强项目</h2>
      <p class="description">统一接入 GeoWeb 去伪影算法，可视化查看主结果与辅助产物</p>
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

        <el-form-item label="适用场景">
          <div class="scene-copy">{{ currentAlgorithm?.scene }}</div>
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
          <div class="tip">支持 PNG/JPG/TIFF，建议上传展开后的钻孔声成像图像</div>
        </el-form-item>

        <div class="param-block">
          <div class="param-title">参数配置</div>

          <template v-if="algorithm === 'stick-and-pull'">
            <el-form-item label="Power">
              <el-input-number v-model="stickPullForm.power" :min="0.1" :max="4" :step="0.1" />
            </el-form-item>
            <el-form-item label="平滑窗口">
              <el-input-number v-model="stickPullForm.smoothWindow" :min="3" :max="301" :step="2" />
            </el-form-item>
            <el-form-item label="有效阈值">
              <el-input-number v-model="stickPullForm.validThreshold" :min="0" :max="1" :step="0.01" />
            </el-form-item>
            <el-form-item label="最小有效比例">
              <el-input-number v-model="stickPullForm.minValidFraction" :min="0" :max="1" :step="0.01" />
            </el-form-item>
          </template>

          <template v-else-if="algorithm === 'groovemask'">
            <el-form-item label="工作模式">
              <el-select v-model="grooveMaskForm.mode" size="small" class="select">
                <el-option label="清理修复" value="clean" />
                <el-option label="仅检测" value="detect-only" />
              </el-select>
            </el-form-item>
            <el-form-item label="后端">
              <el-select v-model="grooveMaskForm.backend" size="small" class="select">
                <el-option label="标准 GrooveMask" value="groovemask_inpaint" />
                <el-option label="Fourier Soft Notch" value="fourier_soft_notch" />
                <el-option label="Variational Decompose" value="variational_decompose" />
              </el-select>
            </el-form-item>
            <el-form-item label="条纹极性">
              <el-select v-model="grooveMaskForm.polarity" size="small" class="select">
                <el-option label="暗槽" value="dark" />
                <el-option label="亮槽" value="bright" />
                <el-option label="自动判断" value="auto" />
              </el-select>
            </el-form-item>
            <el-form-item label="自动裁边">
              <el-switch v-model="grooveMaskForm.autoCrop" />
            </el-form-item>
            <el-form-item label="环向拼接">
              <el-switch v-model="grooveMaskForm.wrapX" />
            </el-form-item>
            <el-form-item label="Tau Sigma">
              <el-input-number v-model="grooveMaskForm.tauSigma" :min="0.5" :max="8" :step="0.1" />
            </el-form-item>
            <el-form-item label="最小宽度">
              <el-input-number v-model="grooveMaskForm.wMin" :min="1" :max="20" />
            </el-form-item>
            <el-form-item label="最大宽度">
              <el-input-number v-model="grooveMaskForm.wMax" :min="2" :max="40" />
            </el-form-item>
            <el-form-item label="持续阈值">
              <el-input-number v-model="grooveMaskForm.persistMin" :min="0.1" :max="1" :step="0.01" />
            </el-form-item>
            <el-form-item label="X 膨胀">
              <el-input-number v-model="grooveMaskForm.dilateX" :min="0" :max="12" />
            </el-form-item>
            <el-form-item label="插值上下文">
              <el-input-number v-model="grooveMaskForm.interpContext" :min="2" :max="48" />
            </el-form-item>
            <el-form-item label="修复半径">
              <el-input-number v-model="grooveMaskForm.inpaintRadius" :min="1" :max="12" />
            </el-form-item>
            <el-form-item
              v-if="grooveMaskForm.backend === 'fourier_soft_notch'"
              label="Notch 强度"
            >
              <el-input-number v-model="grooveMaskForm.notchStrength" :min="0" :max="1" :step="0.05" />
            </el-form-item>
            <el-form-item
              v-if="grooveMaskForm.backend === 'variational_decompose'"
              label="变分迭代"
            >
              <el-input-number v-model="grooveMaskForm.variationalIters" :min="5" :max="200" :step="5" />
            </el-form-item>
          </template>
        </div>

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
        <div class="row"><b>工具：</b>{{ result.algo_id }}</div>

        <div v-if="metricTags.length" class="metric-row">
          <el-tag
            v-for="item in metricTags"
            :key="item.label"
            effect="plain"
            class="metric-tag"
          >
            {{ item.label }}: {{ item.value }}
          </el-tag>
        </div>

        <div v-if="result.run_report?.warnings?.length" class="warning-row">
          <el-alert
            v-for="warn in result.run_report.warnings"
            :key="warn"
            :title="warn"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>

        <div class="result-grid">
          <div
            v-for="item in resultOutputs"
            :key="`${item.key}-${item.file_name}`"
            class="result-card"
          >
            <div class="result-head">
              <div class="result-title">{{ item.title }}</div>
              <el-tag size="small" effect="plain">{{ item.kind }}</el-tag>
            </div>

            <img
              v-if="item.output_image"
              :src="item.output_image"
              :alt="item.title"
              class="result-image"
            />
            <div v-else class="file-only-card">
              <div class="file-name">{{ item.file_name }}</div>
            </div>

            <el-button
              type="primary"
              plain
              size="small"
              @click="download(item.download_url)"
            >
              下载
            </el-button>
          </div>
        </div>

        <div class="downloads">
          <el-button
            v-if="result.download_urls?.image"
            type="primary"
            plain
            @click="download(result.download_urls.image)"
          >
            下载主图
          </el-button>
          <el-button
            v-if="result.download_urls?.npz"
            type="success"
            plain
            @click="download(result.download_urls.npz)"
          >
            下载 NPZ
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { runAugmentation } from '@/api/augmentation'

const algorithms = [
  {
    key: 'stick-and-pull',
    label: 'Stick & Pull 去伪影',
    desc: '修复 stick-and-pull 伪影，输出校正图像与速度曲线',
    scene: '适合纵向拉伸、提放速度不稳引起的轴向畸变类伪影',
  },
  {
    key: 'groovemask',
    label: 'GrooveMask 槽沟去伪影',
    desc: '针对稳定器槽沟/竖槽类伪影，返回掩膜、叠加图和差异热力图',
    scene: '适合展开图中沿深度方向持续出现的窄槽、稳定器槽、沟槽条纹',
  },
]

const algorithm = ref(algorithms[0].key)
const useDemo = ref(false)
const fileRef = ref(null)
const loading = ref(false)
const result = ref(null)

const stickPullForm = ref({
  power: 1.6,
  smoothWindow: 31,
  validThreshold: 0.02,
  minValidFraction: 0.75,
})

const grooveMaskForm = ref({
  mode: 'clean',
  backend: 'groovemask_inpaint',
  polarity: 'dark',
  autoCrop: true,
  wrapX: true,
  tauSigma: 2.5,
  wMin: 2,
  wMax: 10,
  persistMin: 0.7,
  dilateX: 2,
  interpContext: 12,
  inpaintRadius: 2,
  notchStrength: 0.85,
  variationalIters: 30,
})

const currentAlgorithm = computed(() => algorithms.find((item) => item.key === algorithm.value))
const resultOutputs = computed(() => Array.isArray(result.value?.outputs) ? result.value.outputs : [])
const metricTags = computed(() => {
  const metrics = result.value?.quality_metrics
  if (!metrics || typeof metrics !== 'object') return []
  return Object.entries(metrics)
    .filter(([, value]) => typeof value === 'number' && Number.isFinite(value))
    .slice(0, 8)
    .map(([label, value]) => ({
      label,
      value: typeof value === 'number' ? value.toFixed(4) : String(value),
    }))
})

function onFileChange(e) {
  const files = e.target.files
  fileRef.value = files && files.length ? files[0] : null
}

function buildConfig() {
  if (algorithm.value === 'stick-and-pull') {
    return {
      advanced: {
        power: stickPullForm.value.power,
        smooth_window: stickPullForm.value.smoothWindow,
        valid_threshold: stickPullForm.value.validThreshold,
        min_valid_fraction: stickPullForm.value.minValidFraction,
      },
    }
  }

  return {
    safe: {
      mode: grooveMaskForm.value.mode,
      backend: grooveMaskForm.value.backend,
      polarity: grooveMaskForm.value.polarity,
      auto_crop: grooveMaskForm.value.autoCrop,
      wrap_x: grooveMaskForm.value.wrapX,
    },
    advanced: {
      tau_sigma: grooveMaskForm.value.tauSigma,
      w_min: grooveMaskForm.value.wMin,
      w_max: grooveMaskForm.value.wMax,
      persist_min: grooveMaskForm.value.persistMin,
      dilate_x: grooveMaskForm.value.dilateX,
      interp_context: grooveMaskForm.value.interpContext,
      inpaint_radius: grooveMaskForm.value.inpaintRadius,
      notch_strength: grooveMaskForm.value.notchStrength,
      variational_iters: grooveMaskForm.value.variationalIters,
    },
  }
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
    fd.append('config_json', JSON.stringify(buildConfig()))
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
  width: 260px;
}

.hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.scene-copy {
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}

.tip {
  color: #888;
  font-size: 12px;
  margin-top: 6px;
}

.param-block {
  margin: 8px 0 16px;
  padding: 14px 14px 2px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fafbfd;
}

.param-title {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
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

.metric-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.metric-tag {
  margin-right: 0;
}

.warning-row {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.result-card {
  padding: 14px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fff;
}

.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.result-title {
  font-weight: 600;
  color: #303133;
}

.result-image {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  background: #fafafa;
  margin-bottom: 12px;
}

.file-only-card {
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
  background: #fafafa;
}

.file-name {
  font-size: 13px;
  color: #606266;
  word-break: break-all;
  text-align: center;
  padding: 0 12px;
}

.downloads {
  margin-top: 16px;
}

.downloads > * {
  margin-right: 8px;
}
</style>
