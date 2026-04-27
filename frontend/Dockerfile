# HyperFileLens Frontend (Vue 3 + Vite)
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm && pnpm install

# Copy source code
COPY . .

# Build the application
RUN pnpm build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/server.cjs ./
COPY --from=builder /app/package.json ./

# Install pnpm and production dependencies
RUN npm install -g pnpm && pnpm install --prod

# Expose port
EXPOSE 5000

# Start the server
CMD ["node", "server.cjs"]
