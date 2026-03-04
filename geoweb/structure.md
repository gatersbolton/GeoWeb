geoweb/
  apps/
    backend/                 # 现有 Java 后端服务
    frontend/                # 现有前端
    python-service/          # 现有 Python API 服务
  packages/
    compute/
      borehole-ellipticity/  # 现有 python/Borehole ellipticity
      stress-inversion/      # 现有 python/BoreholeEllipStressInv
    geo-core/                # 领域模型/通用算法（含 ATV 去伪影与 Agent）
      algorithms/
        artifacts/           # 去伪影算法（stick_pull/decentralization）
        enhancement/         # 增强算法（super_resolution）
        agents/              # ATV 专家 Agent（recommend/chat/tool registry）
        api/                 # FastAPI 路由（jobs/algorithms/agent）
    shared-utils/            # 语言无关工具（校验规则、常量、示例数据格式）
  libs/
    python/                  # 可复用 Python 库（供 python-service & compute 调用）
    java/                    # 可复用 Java 库（供 backend 调用）
    frontend/                # 共享前端组件/样式（如设计系统）
  data/
    samples/                 # 示例数据/CSV（如 borehole_radius.csv）
    fixtures/                # 测试数据
  infra/
    docker/                  # docker-compose/镜像定义
    deploy/                  # 现有 deploy 内容
  docs/
    architecture/            # 架构说明
    api/                     # API 规范（OpenAPI 等）
    compute/                 # 计算模块说明/输入输出约定
  tools/
    scripts/                 # 开发脚本（格式化、数据转换等）
  outputs/
    test/                    # test_output 等运行产物（可 gitignore）
