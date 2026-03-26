FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_FASTAPI_BASE_URL=http://localhost:8000
ARG VITE_BRIDGE_BASE_URL=http://localhost:8080
ARG VITE_OBJECT_STORAGE_CONSOLE_URL=http://localhost:9001

ENV VITE_FASTAPI_BASE_URL=$VITE_FASTAPI_BASE_URL
ENV VITE_BRIDGE_BASE_URL=$VITE_BRIDGE_BASE_URL
ENV VITE_OBJECT_STORAGE_CONSOLE_URL=$VITE_OBJECT_STORAGE_CONSOLE_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
