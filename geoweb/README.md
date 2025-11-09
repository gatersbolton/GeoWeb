## GeoWeb 钻孔椭圆度 Web 应用

一个将课题组 Python 科学计算与可视化程序集成到易用 Web 界面的全栈项目。前端基于 Vue 3 + Vite + Element Plus，后端网关与用户模块基于 Spring Boot 3（WebFlux + MyBatis + MySQL），计算微服务基于 FastAPI，负责接入钻孔椭圆度算法与可视化输出。

### 架构总览
- 前端：Vue 3、Vite、Element Plus，开发时通过 Vite 代理将`/user`与`/api`请求转发到后端（8081），部分长耗时与进度轮询直接访问 Python 微服务（8000）。
- 后端：Spring Boot 3 + WebFlux 充当 API 网关与业务协调层；MyBatis + MySQL 实现基础用户模块；大文件上传与响应体大小做了放宽配置。
- 计算微服务：FastAPI + numpy/pandas/matplotlib 等，封装“钻孔椭圆度计算/可视化”算法（算法代码来自课题组既有仓库），暴露异步计算、进度、结果与下载接口。

### 目录结构
- `frontend/` 前端源码（Vue3 + Vite）
- `backend/` 后端（Spring Boot 3 + WebFlux + MyBatis）
- `python_service/` FastAPI 计算微服务
- `python/` 课题组算法及其依赖与演示数据（非本项目作者编写）
- `test_*.py` 集成/端到端测试脚本与示例输出

### 功能特性
- 上传 ATV 测井 CSV 数据，调用算法计算钻孔横截面椭圆度参数。
- 支持演示数据一键计算与可视化，便于无数据时快速体验。
- 支持可视化窗口选择与“预览/最终质量”两级渲染，快速交互。
- 进度监控：HTTP 轮询接口（默认）与 WebSocket（服务端已提供）。
- 结果下载：椭圆度参数、集中行程时间、孔径、截面方位等 CSV。
- 大文件上传能力：默认放宽至 500MB（后端配置）。

### 运行环境
- Node.js ≥ 16（建议 LTS）
- Java 17（Spring Boot 3 要求）
- Maven ≥ 3.8（项目已附带 `mvnw/mvnw.cmd` 便于免装本地 Maven）
- Python ≥ 3.10（FastAPI 与部分科学计算库建议 3.10+）
- 本地 MySQL 8（仅当需启用后端用户模块时；也可跳过用户模块）

### 快速开始
1) 启动 Python 计算微服务（默认端口 8000）
```
cd python_service
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 安装算法依赖（算法仓库自身需求）
pip install -r ../python/Borehole\ ellipticity/requirements.txt
python app.py
# 访问 http://localhost:8000/docs 查看 API 文档
```

2) 启动后端（默认端口 8081）
- 如需启用用户模块（`/user/*`），请先准备 MySQL：
  - 新建数据库：`geoweb_demo`
  - 在 `backend/src/main/resources/application.properties` 中配置用户名与密码（默认示例为 `root/996060`，请按需修改）
- 启动：
```
cd backend
./mvnw spring-boot:run  # Windows: mvnw.cmd spring-boot:run
```

3) 启动前端（Vite 开发服务器）
```
cd frontend
npm install
npm run dev
# 默认 http://localhost:5173
```

启动顺序建议：1) Python 微服务 → 2) Spring Boot → 3) 前端。

### 端口与代理
- 前端开发代理（见 `frontend/vite.config.js`）：
  - `/user` → `http://localhost:8081`
  - `/api` → `http://localhost:8081`
- Python 微服务：`http://localhost:8000`
- 注意：前端在长耗时异步计算与进度查询处，直接访问 Python 微服务（例如 `http://localhost:8000/borehole/calculate_async` 与 `/borehole/result/{sessionId}`）。其余计算/可视化多数经由后端转发（`/api/borehole/*`）。

### API 概览（选摘）
- 计算微服务（FastAPI，端口 8000）
  - POST `/borehole/calculate_async`
    - 表单字段：`rp`(float, 必填)、`vf`(float, 必填)、`wtt`(可选)、`beta`(可选)、`tt_file`/`wtt_file`/`mask_file`(可选，若传 `use_demo=true` 则无需上传)
    - 返回：`session_id`、`status`、`message`、`websocket_url`
  - GET `/borehole/progress/{session_id}`：获取进度（支持 HTTP 轮询）
  - WS `/ws/progress/{session_id}`：进度 WebSocket（服务端支持，前端默认用轮询）
  - GET `/borehole/result/{session_id}`：获取统计摘要与下载链接
  - POST `/borehole/visualize`：根据 session 与参数生成可视化（支持 `quality=preview|final` 与窗口 `zTop/lenZ`）
  - POST `/borehole/calculate`：同步计算版本（用于后端转发场景）
  - GET `/borehole/download/{session_id}/{filename}`：下载结果 CSV
  - POST `/process`：示例接口（上传 CSV，返回首列求和与折线图）

- 后端（Spring Boot，端口 8081）
  - POST `/api/borehole/calculate|visualize|process`：转发到 Python 服务
  - POST `/user/register|/user/login`、GET `/user/list`：基础用户模块（MyBatis + MySQL）

### 前端主要页面与交互
- `views/BoreholeEllipticity.vue`
  - Step1 计算：上传必需/可选 CSV、设置 `rp/vf/wtt/beta`，支持“演示数据”直跑
  - 进度监控：`components/ProgressMonitor.vue` 通过轮询 `GET /borehole/progress/{sessionId}` 展示进度与日志
  - Step2 结果：展示 `session_id`、下载链接
  - Step3/4 可视化：支持“演示可视化数据”、窗口滑条预览（预览/最终两级渲染）

### 配置与参数
- 后端上传限制（`backend/src/main/resources/application.properties`）：
  - `spring.servlet.multipart.max-file-size=500MB`
  - `spring.servlet.multipart.max-request-size=500MB`
- Python 微服务对外 URL（后端通过 `python.service.url` 指定，默认 `http://localhost:8000`）

### 测试与示例数据
- 示例数据位于 `python/Borehole ellipticity/data`
- 可用根目录下 `test_*.py` 进行接口与端到端试跑（示例）：
```
python test_complete_system.py
python test_demo_data.py
```

### 常见问题（FAQ）
- Q：为何部分请求直接打到 8000，而不是全部走 8081？
  - A：长耗时计算（异步启动/进度/结果）直接命中计算微服务可减少一跳与序列化，提升交互实时性；其余计算与可视化通过后端统一转发，便于鉴权与网关化治理。
- Q：未配置 MySQL 能否启动？
  - A：如不访问 `/user/*` 模块，建议暂时在本地配置好 MySQL 或将用户模块排除；当前后端默认会初始化数据源，若无数据库会导致启动失败（可自行改为 H2 或条件化装配）。
- Q：上传 CSV 很大怎么办？
  - A：后端已将单请求限制提升至 500MB；仍建议在浏览器端按需分块或进行格式检查，避免无效数据占用带宽与内存。

### 免责声明
- 计算与可视化算法均来自课题组既有 Python 项目，当前仓库仅做 Web 化集成与工程化封装；算法正确性与学术结论以原项目与论文为准。

### 许可证
本仓库未明确声明开源许可证；如需复用，请与作者与课题组确认相应授权。



