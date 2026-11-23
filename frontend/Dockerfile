FROM node:22-bookworm-slim AS build
WORKDIR /frontend
COPY package.json package-lock.json ./
RUN npm ci --include=optional --include=dev
COPY index.html tsconfig*.json vite.config.ts ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /frontend/dist /usr/share/nginx/html
