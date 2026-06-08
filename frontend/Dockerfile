# HyperFileLens Frontend (Vue 3 + Vite)
FROM node:20-alpine as builder

ARG NPM_REGISTRY=https://registry.npmmirror.com

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies from the committed npm lockfile.
RUN npm ci --registry="$NPM_REGISTRY"

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine

ARG NPM_REGISTRY=https://registry.npmmirror.com

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/server.cjs ./
COPY --from=builder /app/package.json ./
COPY --from=builder /app/package-lock.json ./

# Install only production dependencies.
RUN npm ci --omit=dev --registry="$NPM_REGISTRY"

# Expose port
EXPOSE 5000

# Start the server
CMD ["node", "server.cjs"]
