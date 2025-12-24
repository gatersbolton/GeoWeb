# apps/backend

Purpose
- Spring Boot 3 backend (WebFlux + MyBatis).
- API gateway for frontend and proxy to the Python service.

Contents
- src/main/java: controllers, config, domain code.
- src/main/resources: application.properties, mapper xml.
- Dockerfile and pom.xml: build and container setup.

Notes
- Uses MySQL; configure via environment or application.properties.
- Default port is 8081.
