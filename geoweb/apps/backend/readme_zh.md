# apps/backend

用途
- Spring Boot 3 后端（WebFlux + MyBatis）。
- 作为前端网关并转发到 Python 服务。

内容
- src/main/java: 控制器、配置、业务代码。
- src/main/resources: application.properties、mapper xml。
- Dockerfile 与 pom.xml: 构建与容器配置。

说明
- 依赖 MySQL，可通过环境变量或配置文件调整。
- 默认端口为 8081。
