# 钻孔椭圆度应力反演 Web 应用开发方案

## 📋 目录
1. [系统架构](#系统架构)
2. [技术栈](#技术栈)
3. [核心功能模块](#核心功能模块)
4. [实施步骤](#实施步骤)
5. [API接口设计](#api接口设计)
6. [前端页面设计](#前端页面设计)
7. [关键技术点](#关键技术点)

---

## 🏗️ 系统架构

### 整体架构
```
┌─────────────────────────────────────────────────────────┐
│                    Vue 3 前端                            │
│  ┌──────────────┬──────────────┬──────────────────┐    │
│  │ 文件上传模块 │ 参数配置模块 │ 结果可视化模块   │    │
│  │ - ATV数据    │ - 深度区间   │ - 3D应力图      │    │
│  │ - 椭圆度数据 │ - 反演参数   │ - 深度剖面图    │    │
│  │              │ - 任务管理   │ - 数据表格      │    │
│  └──────────────┴──────────────┴──────────────────┘    │
└────────────────────┬────────────────────────────────────┘
                     │ REST API (JSON)
┌────────────────────▼────────────────────────────────────┐
│              Spring Boot 后端 (Java)                     │
│  ┌──────────────┬──────────────┬──────────────────┐    │
│  │ 文件管理     │ 任务调度     │ 结果处理         │    │
│  │ - 上传下载   │ - 异步任务   │ - MAT文件解析    │    │
│  │ - 格式验证   │ - 进度监控   │ - 数据转换JSON   │    │
│  │ - 存储管理   │ - 任务队列   │ - 缓存管理       │    │
│  └──────────────┴──────────────┴──────────────────┘    │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/WebSocket
┌────────────────────▼────────────────────────────────────┐
│            Python 服务层 (Flask/FastAPI)                 │
│  ┌──────────────┬──────────────┬──────────────────┐    │
│  │ 椭圆度计算   │ MATLAB引擎   │ 数据预处理       │    │
│  │ - Python实现 │ - 应力反演   │ - CSV处理        │    │
│  │ - 异常过滤   │ - MAT导出    │ - 格式转换       │    │
│  │ - 重采样     │              │                  │    │
│  └──────────────┴──────────────┴──────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

### 前端
- **框架**: Vue 3 + Vite
- **UI库**: Element Plus / Ant Design Vue
- **图表**: 
  - ECharts（2D图表、深度剖面）
  - Three.js（3D应力可视化）
  - D3.js（玫瑰图、极坐标图）
- **状态管理**: Pinia
- **HTTP**: Axios
- **实时通信**: WebSocket（进度监控）

### 后端
- **主框架**: Spring Boot 2.7+
- **数据库**: MySQL（任务管理）+ Redis（缓存）
- **文件处理**: Apache POI（CSV）、JMatio（MAT文件读取）
- **异步任务**: Spring @Async + 线程池
- **WebSocket**: Spring WebSocket

### Python服务
- **框架**: Flask 或 FastAPI
- **科学计算**: NumPy, Pandas, SciPy
- **MATLAB集成**: 
  - **方案1**: MATLAB Engine API for Python
  - **方案2**: Octave（开源替代）
  - **方案3**: 将MATLAB代码转为Python
- **MAT文件**: scipy.io.loadmat / savemat

---

## 🎯 核心功能模块

### 1. 数据上传与管理
```
功能：
├── ATV原始数据上传（5个CSV文件）
├── 椭圆度数据上传（已处理的CSV）
├── 文件格式验证
├── 数据预览
└── 历史数据管理
```

### 2. 椭圆度计算模块
```
功能：
├── 参数配置
│   ├── ATV工具半径
│   ├── 流体声速
│   ├── 深度范围
│   └── 输出目录
├── 椭圆度计算
│   ├── 最小二乘拟合
│   ├── 进度实时显示
│   └── 结果预览
└── 数据处理
    ├── 异常值过滤
    ├── 深度重采样
    └── 轨迹拼接
```

### 3. 应力反演模块（核心）
```
功能：
├── 反演配置
│   ├── 全局反演 / 局部反演
│   ├── 深度窗口（局部反演）
│   ├── 最大迭代次数
│   ├── NaN阈值
│   └── 搜索参数范围
├── 任务执行
│   ├── 异步任务提交
│   ├── 实时进度监控（WebSocket）
│   ├── 任务取消
│   └── 错误处理
└── 结果管理
    ├── MAT文件存储
    ├── 结果解析
    └── JSON格式转换
```

### 4. 结果可视化模块
```
功能：
├── 应力方位可视化
│   ├── 3D应力方向图
│   ├── 玫瑰图（方位角分布）
│   └── 立体投影图
├── 深度剖面图
│   ├── 欧拉角-深度曲线
│   ├── 应力比-深度曲线
│   ├── RMSE-深度曲线
│   └── 椭圆度参数剖面
├── 数据表格
│   ├── 最优解参数表
│   ├── Top40结果列表
│   └── 可导出Excel/CSV
└── 对比分析
    ├── 多深度区间对比
    └── 不同参数组合对比
```

---

## 📝 实施步骤

### Phase 1: 基础架构搭建（1-2周）

#### 1.1 后端基础
```java
// Spring Boot 项目结构
com.geoweb.stressinv
├── controller
│   ├── FileController.java          // 文件上传下载
│   ├── EllipticityController.java   // 椭圆度计算
│   ├── StressInversionController.java // 应力反演
│   └── WebSocketController.java     // 实时进度
├── service
│   ├── FileService.java
│   ├── EllipticityService.java
│   ├── StressInversionService.java
│   └── PythonServiceClient.java     // Python服务调用
├── entity
│   ├── BoreholeData.java
│   ├── EllipticityResult.java
│   ├── StressInversionTask.java
│   └── StressInversionResult.java
├── dto
│   ├── EllipticityRequest.java
│   └── StressInversionRequest.java
└── util
    ├── MatFileParser.java           // MAT文件解析
    └── CsvUtils.java
```

#### 1.2 Python服务
```python
# Flask 应用结构
python_service/
├── app.py                           # 主应用
├── services/
│   ├── ellipticity_service.py      # 椭圆度计算
│   ├── matlab_service.py           # MATLAB调用
│   └── data_processor.py           # 数据处理
├── utils/
│   ├── csv_handler.py
│   └── mat_handler.py
└── config.py
```

#### 1.3 前端基础
```
frontend/src/
├── views/
│   ├── StressInversion/
│   │   ├── DataUpload.vue          // 数据上传页
│   │   ├── EllipticityCalc.vue     // 椭圆度计算页
│   │   ├── StressInvConfig.vue     // 反演配置页
│   │   └── ResultView.vue          // 结果展示页
├── components/
│   ├── FileUploader.vue
│   ├── ProgressMonitor.vue
│   ├── StressVisualization/
│   │   ├── StressRoseDiagram.vue   // 玫瑰图
│   │   ├── Stress3DView.vue        // 3D可视化
│   │   └── DepthProfile.vue        // 深度剖面
│   └── DataTable.vue
├── api/
│   └── stressInversion.js
└── store/
    └── stressInvModule.js
```

### Phase 2: 核心功能开发（3-4周）

#### 2.1 文件上传与验证
```javascript
// 前端文件上传
const uploadFiles = async (files) => {
  const formData = new FormData();
  formData.append('ttFile', files.ttFile);
  formData.append('ampFile', files.ampFile);
  formData.append('azimuthFile', files.azimuthFile);
  formData.append('tiltFile', files.tiltFile);
  formData.append('wndtimeFile', files.wndtimeFile);
  
  const response = await axios.post('/api/files/upload-atv-data', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      updateProgress(progress);
    }
  });
  return response.data;
};
```

```java
// 后端文件处理
@PostMapping("/upload-atv-data")
public ResponseEntity<FileUploadResponse> uploadATVData(
    @RequestParam("ttFile") MultipartFile ttFile,
    @RequestParam("ampFile") MultipartFile ampFile,
    @RequestParam("azimuthFile") MultipartFile azimuthFile,
    @RequestParam("tiltFile") MultipartFile tiltFile,
    @RequestParam("wndtimeFile") MultipartFile wndtimeFile) {
    
    // 验证文件格式
    validateCsvFiles(ttFile, ampFile, azimuthFile, tiltFile, wndtimeFile);
    
    // 保存文件
    String taskId = UUID.randomUUID().toString();
    String uploadDir = fileService.saveFiles(taskId, files);
    
    return ResponseEntity.ok(new FileUploadResponse(taskId, uploadDir));
}
```

#### 2.2 椭圆度计算（调用Python）
```java
// Spring Boot 调用 Python 服务
@Service
public class EllipticityService {
    
    @Autowired
    private RestTemplate restTemplate;
    
    public String calculateEllipticity(EllipticityRequest request) {
        String pythonServiceUrl = "http://localhost:5000/api/calculate-ellipticity";
        
        // 构建请求
        HttpEntity<EllipticityRequest> entity = new HttpEntity<>(request);
        
        // 调用Python服务
        ResponseEntity<TaskResponse> response = restTemplate.postForEntity(
            pythonServiceUrl, entity, TaskResponse.class);
        
        return response.getBody().getTaskId();
    }
    
    @Async
    public void monitorTask(String taskId, WebSocketSession session) {
        // 轮询Python服务获取进度
        while (!isTaskComplete(taskId)) {
            TaskProgress progress = getTaskProgress(taskId);
            sendProgressUpdate(session, progress);
            Thread.sleep(1000);
        }
    }
}
```

```python
# Python Flask 服务
from flask import Flask, request, jsonify
import sys
sys.path.append('./python/Borehole ellipticity')
from borehole_ellipticity import calculate_ellipticity

app = Flask(__name__)

@app.route('/api/calculate-ellipticity', methods=['POST'])
def calculate_ellipticity_endpoint():
    data = request.json
    
    # 提取参数
    fp_tt = data['fp_tt']
    fp_wtt = data.get('fp_wtt')
    rp = data['rp']
    vf = data['vf']
    dir_out = data['dir_out']
    
    # 异步执行计算
    task_id = str(uuid.uuid4())
    executor.submit(run_ellipticity_calculation, 
                   task_id, fp_tt, fp_wtt, rp, vf, dir_out)
    
    return jsonify({'task_id': task_id, 'status': 'processing'})

def run_ellipticity_calculation(task_id, fp_tt, fp_wtt, rp, vf, dir_out):
    try:
        # 调用椭圆度计算函数
        result = calculate_ellipticity(fp_tt, fp_wtt, rp, vf, dir_out)
        
        # 更新任务状态
        update_task_status(task_id, 'completed', result)
    except Exception as e:
        update_task_status(task_id, 'failed', str(e))
```

#### 2.3 MATLAB应力反演集成

**方案A: 使用MATLAB Engine API**
```python
# Python调用MATLAB
import matlab.engine

class MatlabStressInversion:
    def __init__(self):
        self.eng = matlab.engine.start_matlab()
        self.eng.addpath('./python/BoreholeEllipStressInv/V1.0/stressinv')
    
    def global_inversion(self, input_file, output_file):
        """全局应力反演"""
        try:
            # 调用MATLAB函数
            self.eng.stressinv_ellipticity(
                input_file, 
                output_file, 
                nargout=0
            )
            return True
        except Exception as e:
            raise Exception(f"MATLAB execution failed: {str(e)}")
    
    def local_inversion(self, input_file, output_file, dz=25, nan_thres=0.5):
        """局部应力反演"""
        self.eng.stressinv_ellipticity_depthwise(
            input_file,
            output_file,
            float(dz),
            float(nan_thres),
            nargout=0
        )
        return True
    
    def __del__(self):
        self.eng.quit()
```

**方案B: 将MATLAB转为Python（推荐）**
```python
# 纯Python实现应力反演
import numpy as np
from scipy.optimize import minimize
from concurrent.futures import ProcessPoolExecutor

class StressInversionPython:
    """Python实现的应力反演算法"""
    
    def __init__(self, max_iteration=100):
        self.max_iteration = max_iteration
        
    def neighborhood_algorithm(self, data, progress_callback=None):
        """邻域算法搜索最优应力状态"""
        # 初始化搜索范围
        a_range = np.linspace(0, 360, 8)
        b_range = np.linspace(-90, 0, 4)
        c_range = np.linspace(0, 90, 4)
        phi_range = np.linspace(0, 1, 5)
        S3_range = np.linspace(0, 1, 5)
        
        best_results = []
        
        for iteration in range(self.max_iteration):
            # 生成参数组合
            param_combinations = self._generate_combinations(
                a_range, b_range, c_range, phi_range, S3_range
            )
            
            # 并行计算RMSE
            rmse_results = self._parallel_compute_rmse(
                param_combinations, data
            )
            
            # 选择最优40组
            top40_indices = np.argsort(rmse_results)[:40]
            best_results = param_combinations[top40_indices]
            
            # 缩小搜索范围（邻域算法核心）
            a_range, b_range, c_range, phi_range, S3_range = \
                self._update_search_range(best_results)
            
            # 报告进度
            if progress_callback:
                progress_callback(iteration, self.max_iteration)
            
            # 收敛判断
            if self._is_converged(a_range):
                break
        
        return self._format_results(best_results, rmse_results)
    
    def _compute_rmse(self, params, data):
        """计算RMSE"""
        a, b, c, phi, S3 = params
        
        # 计算理论椭圆轴方位角
        predicted_azimuths = []
        for i in range(len(data)):
            azimuth = self._ellipse_axis_orientation(
                phi, S3, [a, b, c],
                data[i]['btilt'], data[i]['bazi']
            )
            predicted_azimuths.append(azimuth)
        
        # 计算RMSE
        measured = data['azimuth_major']
        predicted = np.array(predicted_azimuths)
        rmse = np.sqrt(np.mean((measured - predicted)**2))
        
        return rmse
    
    def _ellipse_axis_orientation(self, phi, S3, euler, btilt, bazi):
        """计算椭圆轴方位角（核心物理模型）"""
        # 实现椭圆轴方位计算公式
        # 这部分需要根据EllipAxisOrien.m转换
        pass
```

#### 2.4 MAT文件解析为JSON
```java
// 使用JMatio库解析MAT文件
import com.jmatio.io.MatFileReader;
import com.jmatio.types.*;

@Service
public class MatFileParser {
    
    public StressInversionResult parseGlobalResult(String matFilePath) {
        try {
            MatFileReader reader = new MatFileReader(matFilePath);
            
            // 读取Rank_Top40
            MLDouble rankTop40 = (MLDouble) reader.getMLArray("Rank_Top40");
            double[][] top40Data = rankTop40.getArray();
            
            // 转换为JSON对象
            List<StressState> top40States = new ArrayList<>();
            for (int i = 0; i < top40Data.length; i++) {
                StressState state = new StressState();
                state.setEulerA(top40Data[i][0]);
                state.setEulerB(top40Data[i][1]);
                state.setEulerC(top40Data[i][2]);
                state.setPhi(top40Data[i][3]);
                state.setS3(top40Data[i][4]);
                state.setRmse(top40Data[i][5]);
                top40States.add(state);
            }
            
            // 读取其他数据...
            MLDouble aRange = (MLDouble) reader.getMLArray("a_range");
            MLDouble rmseStore = (MLDouble) reader.getMLArray("RMSE_store");
            
            return new StressInversionResult(top40States, ...);
            
        } catch (IOException e) {
            throw new RuntimeException("Failed to parse MAT file", e);
        }
    }
    
    public List<DepthStressResult> parseLocalResult(String matFilePath) {
        MatFileReader reader = new MatFileReader(matFilePath);
        
        // param是结构数组
        MLStructure param = (MLStructure) reader.getMLArray("param");
        
        List<DepthStressResult> results = new ArrayList<>();
        for (int i = 0; i < param.getM(); i++) {
            MLDouble zmid = (MLDouble) param.getField("zmid", i);
            MLDouble rankTop40 = (MLDouble) param.getField("Rank_Top40", i);
            
            // 解析每个深度的结果
            DepthStressResult result = new DepthStressResult();
            result.setDepth(zmid.get(0));
            result.setStressStates(parseStressStates(rankTop40));
            results.add(result);
        }
        
        return results;
    }
}
```

### Phase 3: 可视化开发（2-3周）

#### 3.1 应力玫瑰图（D3.js）
```vue
<template>
  <div ref="roseDiagram" class="rose-diagram"></div>
</template>

<script setup>
import * as d3 from 'd3';
import { ref, onMounted } from 'vue';

const props = defineProps({
  azimuths: Array  // 方位角数据
});

const roseDiagram = ref(null);

onMounted(() => {
  drawRoseDiagram();
});

function drawRoseDiagram() {
  const width = 400;
  const height = 400;
  const radius = Math.min(width, height) / 2 - 40;
  
  const svg = d3.select(roseDiagram.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .append('g')
    .attr('transform', `translate(${width/2},${height/2})`);
  
  // 统计方位角分布
  const bins = d3.bin()
    .domain([0, 360])
    .thresholds(d3.range(0, 360, 10))
    (props.azimuths);
  
  // 绘制玫瑰图
  const arc = d3.arc()
    .innerRadius(0)
    .outerRadius(d => {
      const scale = d3.scaleLinear()
        .domain([0, d3.max(bins, b => b.length)])
        .range([0, radius]);
      return scale(d.length);
    })
    .startAngle(d => (d.x0 * Math.PI) / 180)
    .endAngle(d => (d.x1 * Math.PI) / 180);
  
  svg.selectAll('path')
    .data(bins)
    .enter()
    .append('path')
    .attr('d', arc)
    .attr('fill', '#3498db')
    .attr('stroke', 'white')
    .attr('stroke-width', 1);
}
</script>
```

#### 3.2 3D应力方向可视化（Three.js）
```vue
<template>
  <div ref="stress3D" class="stress-3d-view"></div>
</template>

<script setup>
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

const props = defineProps({
  stressState: Object  // {eulerA, eulerB, eulerC, phi}
});

function create3DStress() {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(75, width/height, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer();
  
  // 绘制主应力方向箭头
  const { eulerA, eulerB, eulerC } = props.stressState;
  
  // S1 主应力（红色箭头）
  const s1Arrow = new THREE.ArrowHelper(
    getStressDirection(eulerA, eulerB, eulerC, 1),
    new THREE.Vector3(0, 0, 0),
    2,
    0xff0000
  );
  scene.add(s1Arrow);
  
  // S2 中间应力（绿色箭头）
  const s2Arrow = new THREE.ArrowHelper(
    getStressDirection(eulerA, eulerB, eulerC, 2),
    new THREE.Vector3(0, 0, 0),
    1.5,
    0x00ff00
  );
  scene.add(s2Arrow);
  
  // S3 最小应力（蓝色箭头）
  const s3Arrow = new THREE.ArrowHelper(
    getStressDirection(eulerA, eulerB, eulerC, 3),
    new THREE.Vector3(0, 0, 0),
    1,
    0x0000ff
  );
  scene.add(s3Arrow);
  
  // 添加坐标轴和网格
  const axesHelper = new THREE.AxesHelper(3);
  scene.add(axesHelper);
  
  // 添加控制器
  const controls = new OrbitControls(camera, renderer.domElement);
  
  animate();
}
</script>
```

#### 3.3 深度剖面图（ECharts）
```vue
<template>
  <div ref="depthProfile" style="width: 100%; height: 600px"></div>
</template>

<script setup>
import * as echarts from 'echarts';
import { ref, onMounted, watch } from 'vue';

const props = defineProps({
  depthData: Array  // [{depth, eulerA, eulerB, eulerC, phi, rmse}, ...]
});

const depthProfile = ref(null);
let chart = null;

onMounted(() => {
  chart = echarts.init(depthProfile.value);
  updateChart();
});

function updateChart() {
  const option = {
    title: { text: '应力参数-深度剖面图' },
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['欧拉角A', '欧拉角B', '欧拉角C', '应力比φ', 'RMSE']
    },
    grid: {
      left: '10%',
      right: '10%'
    },
    xAxis: [
      {
        type: 'value',
        name: '欧拉角 (度)',
        position: 'top'
      },
      {
        type: 'value',
        name: '应力比 / RMSE',
        position: 'top',
        offset: 80
      }
    ],
    yAxis: {
      type: 'value',
      name: '深度 (米)',
      inverse: true  // 深度向下
    },
    series: [
      {
        name: '欧拉角A',
        type: 'line',
        data: props.depthData.map(d => [d.eulerA, d.depth]),
        xAxisIndex: 0
      },
      {
        name: '欧拉角B',
        type: 'line',
        data: props.depthData.map(d => [d.eulerB, d.depth]),
        xAxisIndex: 0
      },
      {
        name: '欧拉角C',
        type: 'line',
        data: props.depthData.map(d => [d.eulerC, d.depth]),
        xAxisIndex: 0
      },
      {
        name: '应力比φ',
        type: 'line',
        data: props.depthData.map(d => [d.phi, d.depth]),
        xAxisIndex: 1
      },
      {
        name: 'RMSE',
        type: 'line',
        data: props.depthData.map(d => [d.rmse, d.depth]),
        xAxisIndex: 1
      }
    ]
  };
  
  chart.setOption(option);
}

watch(() => props.depthData, updateChart);
</script>
```

### Phase 4: 优化与部署（1周）

#### 4.1 性能优化
- **后端缓存**: Redis缓存计算结果
- **异步处理**: 大任务使用消息队列（RabbitMQ）
- **文件存储**: MinIO对象存储
- **数据库优化**: 索引优化、分页查询

#### 4.2 实时进度监控
```java
// WebSocket实现
@Component
public class TaskProgressWebSocket {
    
    private static Map<String, WebSocketSession> sessions = new ConcurrentHashMap<>();
    
    @OnOpen
    public void onOpen(Session session, @PathParam("taskId") String taskId) {
        sessions.put(taskId, session);
    }
    
    public void sendProgress(String taskId, TaskProgress progress) {
        WebSocketSession session = sessions.get(taskId);
        if (session != null && session.isOpen()) {
            session.sendMessage(new TextMessage(JSON.toJSONString(progress)));
        }
    }
}
```

---

## 🔌 API接口设计

### 1. 文件管理接口
```
POST   /api/files/upload-atv-data       # 上传ATV原始数据
POST   /api/files/upload-ellipticity    # 上传椭圆度数据
GET    /api/files/{taskId}/list         # 获取任务文件列表
GET    /api/files/download/{fileId}     # 下载文件
DELETE /api/files/{fileId}              # 删除文件
```

### 2. 椭圆度计算接口
```
POST   /api/ellipticity/calculate       # 开始椭圆度计算
GET    /api/ellipticity/task/{taskId}   # 获取任务状态
POST   /api/ellipticity/filter-outliers # 异常值过滤
POST   /api/ellipticity/resample        # 深度重采样
POST   /api/ellipticity/concat-trajectory # 拼接轨迹
```

### 3. 应力反演接口
```
POST   /api/stress-inversion/global     # 全局应力反演
POST   /api/stress-inversion/local      # 局部应力反演
GET    /api/stress-inversion/task/{taskId} # 获取任务状态
GET    /api/stress-inversion/result/{taskId} # 获取反演结果
DELETE /api/stress-inversion/task/{taskId} # 取消任务
```

### 4. 结果查询接口
```
GET    /api/results/{taskId}/summary    # 获取结果摘要
GET    /api/results/{taskId}/top40      # 获取最优40组结果
GET    /api/results/{taskId}/depth/{depth} # 获取特定深度结果
GET    /api/results/{taskId}/export     # 导出结果（Excel）
```

### 接口示例

#### 请求: 全局应力反演
```json
POST /api/stress-inversion/global

{
  "inputFile": "/uploads/task123/ellipticity_with_trajectory.csv",
  "outputFile": "/results/task123/stress_inv_global.mat",
  "maxIteration": 100,
  "searchRanges": {
    "eulerA": {"min": 0, "max": 360, "interval": 45},
    "eulerB": {"min": -90, "max": 0, "interval": 22.5},
    "eulerC": {"min": 0, "max": 90, "interval": 22.5},
    "phi": {"min": 0, "max": 1, "interval": 0.25},
    "S3": {"min": 0, "max": 1, "interval": 0.25}
  }
}
```

#### 响应
```json
{
  "code": 200,
  "message": "Task submitted successfully",
  "data": {
    "taskId": "task-uuid-123",
    "status": "processing",
    "estimatedTime": "5-10 minutes"
  }
}
```

#### 获取结果
```json
GET /api/stress-inversion/result/task-uuid-123

{
  "code": 200,
  "data": {
    "taskId": "task-uuid-123",
    "status": "completed",
    "result": {
      "bestStressState": {
        "eulerA": 123.45,
        "eulerB": -67.89,
        "eulerC": 34.56,
        "phi": 0.67,
        "S3": 0.23,
        "rmse": 1.23
      },
      "top40States": [
        {
          "eulerA": 123.45,
          "eulerB": -67.89,
          "eulerC": 34.56,
          "phi": 0.67,
          "S3": 0.23,
          "rmse": 1.23
        },
        // ... 39 more
      ],
      "convergenceHistory": [
        {"iteration": 1, "bestRmse": 5.67},
        {"iteration": 2, "bestRmse": 3.45},
        // ...
      ]
    }
  }
}
```

---

## 🎨 前端页面设计

### 页面流程
```
主页
  ├── 1. 数据上传页
  │     ├── ATV原始数据上传
  │     └── 已有椭圆度数据上传
  │
  ├── 2. 椭圆度计算页（可选）
  │     ├── 参数配置
  │     ├── 计算进度监控
  │     └── 结果预览
  │
  ├── 3. 应力反演配置页
  │     ├── 选择反演类型（全局/局部）
  │     ├── 设置反演参数
  │     └── 提交任务
  │
  └── 4. 结果展示页
        ├── 应力状态可视化
        ├── 深度剖面图
        ├── 数据表格
        └── 导出功能
```

### 界面布局建议
```
┌─────────────────────────────────────────────────────┐
│  钻孔椭圆度应力反演系统                [用户] [退出]│
├─────────────────────────────────────────────────────┤
│ [数据上传] [椭圆度计算] [应力反演] [结果查看]        │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│  任务列表    │         主内容区                     │
│              │                                      │
│ □ Task-001   │  ┌────────────────────────────┐    │
│ □ Task-002   │  │                            │    │
│ ■ Task-003   │  │    可视化图表              │    │
│ □ Task-004   │  │                            │    │
│              │  └────────────────────────────┘    │
│              │                                      │
│              │  ┌────────────────────────────┐    │
│  进度监控    │  │    参数配置/数据表格        │    │
│  ████░░ 60%  │  └────────────────────────────┘    │
│              │                                      │
└──────────────┴──────────────────────────────────────┘
```

---

## 🔑 关键技术点

### 1. MATLAB集成方案选择

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| MATLAB Engine API | 直接使用现有代码 | 需要MATLAB授权 | ⭐⭐⭐ |
| Octave替代 | 开源免费 | 兼容性问题 | ⭐⭐ |
| 转为Python | 无依赖、性能好 | 开发工作量大 | ⭐⭐⭐⭐⭐ |

**推荐**: 优先采用**转为Python**方案，核心算法不复杂。

### 2. 大文件处理
- 分块上传（前端Chunk Upload）
- 断点续传
- 压缩传输

### 3. 长时间任务处理
- 异步任务队列
- WebSocket实时进度
- 任务可取消/暂停

### 4. 结果数据存储
```
数据库（MySQL）: 任务元数据、状态
├── task_id
├── status
├── create_time
└── result_summary

文件系统: MAT文件、CSV文件
└── /data/
    └── tasks/
        └── {task_id}/
            ├── input/
            ├── output/
            └── results/
```

---

## 📦 部署方案

### Docker部署
```yaml
# docker-compose.yml
version: '3.8'

services:
  # Spring Boot后端
  backend:
    build: ./backend
    ports:
      - "8080:8080"
    environment:
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/geoweb
      - PYTHON_SERVICE_URL=http://python-service:5000
    depends_on:
      - mysql
      - redis
  
  # Python服务
  python-service:
    build: ./python_service
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
  
  # Vue前端（Nginx）
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
  
  # MySQL
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: geoweb
  
  # Redis
  redis:
    image: redis:7
```

---

## 📊 预期效果

1. **用户友好**: 图形化界面，无需编程知识
2. **高效计算**: 异步处理，支持多任务并行
3. **实时反馈**: WebSocket进度监控
4. **丰富可视化**: 3D应力图、深度剖面、玫瑰图
5. **数据管理**: 历史任务管理、结果导出

---

## 🚀 开发周期估算

| 阶段 | 时间 | 人员 |
|------|------|------|
| 基础架构 | 1-2周 | 全栈1人 |
| 核心功能 | 3-4周 | 后端1人 + Python1人 |
| 可视化 | 2-3周 | 前端1人 |
| 测试优化 | 1周 | 全员 |
| **总计** | **7-10周** | **2-3人** |

---

## 📞 后续支持

如需详细的代码实现或技术支持，请联系：
- Email: wangguangyu@mail.ustc.edu.cn
- 项目文档: [查看README](./readme_zh.html)


