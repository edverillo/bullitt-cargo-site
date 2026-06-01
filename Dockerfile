
# Stage 1 — build
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Override astro config for Coolify (no GitHub Pages base path)
RUN echo "import { defineConfig } from 'astro/config'; export default defineConfig({ site: 'https://bullit.lab.edrd.net' });" > astro.config.mjs

RUN npm run build

# Stage 2 — serve
FROM nginx:stable-alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# SPA-style fallback — serve index.html for unknown routes
RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  index index.html;\n  location / {\n    try_files $uri $uri/ /index.html;\n  }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
