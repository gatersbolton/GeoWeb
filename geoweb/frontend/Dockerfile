FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN chmod +x node_modules/.bin/vite
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=build /app/dist/ /usr/share/nginx/html/
# nginx.conf 将由 docker-compose 挂载到 /etc/nginx/nginx.conf


