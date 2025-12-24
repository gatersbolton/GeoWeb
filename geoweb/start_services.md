# 钻孔椭圆度项目启动指南

## 概述

这个项目包含了前端Vue3界面、后端SpringBoot服务和Python数据处理服务三个部分，实现了钻孔椭圆度数据的web可视化分析。

## 功能特性

### 输入功能
- ✅ **必需文件上传**: ATV行程时间日志(TT_NM.csv)
- ✅ **可选文件上传**: 
  - 声学窗口行程时间日志(WNDTIME.csv)
  - 掩码文件(用于排除部分数据)
- ✅ **参数配置**:
  - ATV工具声学头半径 (默认: 0.019m)
  - 钻孔流体声速 (默认: 1480 m/s)
  - 固定AWT值 (可选)
  - 单位转换乘数 (可选)

### 输出功能
- ✅ **椭圆度参数图**: 主轴方位角、椭圆度比例、拟合误差
- ✅ **钻孔横截面图**: 多个深度的椭圆拟合结果
- ✅ **钻孔半径分析图**: 半径随深度变化及分布统计
- ✅ **结果文件下载**: CSV格式的处理结果

## 启动步骤

### 1. 启动Python服务 (端口: 8000)

```bash
cd apps/python-service
pip install -r requirements.txt
uvicorn python_service.app:app --reload
```

### 2. 启动后端SpringBoot服务 (端口: 8081)

```bash
cd apps/backend
./mvnw spring-boot:run
# 或者在Windows上使用
mvnw.cmd spring-boot:run
```

### 3. 启动前端开发服务器 (端口: 3000)

```bash
cd apps/frontend
npm install
npm run dev
```

## 访问地址

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8081
- **Python服务**: http://localhost:8000

## 使用流程

1. 打开前端界面 http://localhost:3000
2. 登录系统 (如果需要)
3. 点击侧边栏 "钻孔椭圆度项目" 菜单
4. 上传必需的TT文件和可选的辅助文件
5. 配置处理参数
6. 点击 "开始处理" 按钮
7. 查看生成的图表结果
8. 下载处理结果文件

## API端点

### 后端SpringBoot
- `POST /api/borehole/process` - 处理钻孔椭圆度数据

### Python服务
- `POST /borehole/process` - 椭圆度数据处理核心算法

## 技术栈

- **前端**: Vue3 + Element Plus + Vite
- **后端**: SpringBoot + MyBatis + MySQL
- **Python服务**: FastAPI + Pandas + Matplotlib + NumPy
- **数据处理**: 椭圆拟合算法 + 声学成像测井数据分析

## 注意事项

1. 确保所有三个服务都正常启动
2. MySQL数据库需要正确配置 (如果使用用户系统)
3. 上传的CSV文件应该符合ATV测井数据格式
4. **文件大小限制**：单个文件不超过500MB
5. 处理大文件时可能需要等待较长时间
6. Python服务目前使用模拟数据进行演示，实际项目中需要集成真实的椭圆拟合算法

## 常见问题解决

### 文件上传失败 - "Maximum upload size exceeded"

**问题**: 上传文件时提示文件过大
**解决方案**: 
1. 检查文件大小是否超过500MB限制
2. 如果需要处理更大文件，可以修改以下配置：
   - 后端: `apps/backend/src/main/resources/application.properties` 中的 `spring.servlet.multipart.max-file-size`
   - 前端: `apps/frontend/src/views/BoreholeEllipticity.vue` 中的 `MAX_FILE_SIZE` 常量
   - Python服务: `apps/python-service/python_service/app.py` 中的文件大小检查

### 图表中文显示为方框

**问题**: 生成的图表中中文标题和标签显示为方框
**原因**: 系统缺少中文字体支持
**解决方案**:
1. **Windows系统**:
   - 进入 `设置` → `时间和语言` → `语言`
   - 添加中文语言包（如果未安装）
   - 或下载安装"微软雅黑"、"黑体"等中文字体到 `C:\Windows\Fonts\` 目录
2. **Linux系统**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei
   
   # CentOS/RHEL
   sudo yum install wqy-microhei-fonts wqy-zenhei-fonts
   ```
3. **重启Python服务**: 安装字体后需要重启Python服务以生效
4. **备用方案**: 系统会自动检测字体可用性，如无中文字体则使用英文标签

### 处理超时
**问题**: 大文件处理时间过长导致超时
**解决方案**:
1. 前端API超时时间已设置为5分钟
2. 如需处理更大文件，可增加 `apps/frontend/src/api/borehole.js` 中的 `timeout` 值

### 快速重启服务
如果遇到配置问题，可以使用快速重启脚本：
```bash
# Windows用户
./restart_services.bat

# 手动重启
cd apps/python-service && uvicorn python_service.app:app --reload
cd apps/backend && ./mvnw spring-boot:run  
cd apps/frontend && npm run dev
```

## 文件结构

```
├── apps/
│   ├── frontend/           # Vue3前端项目
│   ├── backend/            # SpringBoot后端项目
│   └── python-service/     # Python数据处理服务
└── packages/
    └── compute/
        └── borehole-ellipticity/
``` 
