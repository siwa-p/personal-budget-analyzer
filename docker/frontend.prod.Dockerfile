# Stage 1: Build the React app
FROM node:20-alpine AS builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
ARG VITE_COGNITO_USER_POOL_ID
ENV VITE_COGNITO_USER_POOL_ID=$VITE_COGNITO_USER_POOL_ID
ARG VITE_COGNITO_CLIENT_ID
ENV VITE_COGNITO_CLIENT_ID=$VITE_COGNITO_CLIENT_ID

RUN npm run build

# Stage 2: Export only dist files (for --output type=local)
FROM scratch AS dist
COPY --from=builder /app/dist /

# Stage 3: Serve with nginx (if containerized frontend is ever needed)
FROM nginx:alpine AS serve
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx.frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
