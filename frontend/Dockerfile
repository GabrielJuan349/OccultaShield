FROM node:22-slim AS builder

WORKDIR /app

# Install generic dependencies provided by Bun in previous attempt? 
# We need to npm install based on package.json.
# Since package-lock.json might be missing (we only saw bun.lock), we might need to rely on bun.lock or just install from package.json.
# Installing bun in node image to restore deps? Or just use npm. 
# Problem: bun.lock is not npm compatible.
# Better approach: Use oven/bun as builder, BUT use node to run the build command? No, bun image has node.
# Wait, oven/bun image is minimal.
# Let's try: Use `oven/bun` but ensure we run `node` for the build? 
# Actually, the error `Cannot find module` usually happens when `bun` runtime executes the CLI's internal bundle code which expects Node behavior for virtual modules.

# REVISED PLAN:
# Use `node:22` as builder. 
# Allow it to install dependencies using `npm install` (generates package-lock on fly).
# Copy source. Build.
# Runtime: `oven/bun`.

COPY package.json ./
# If bun.lock exists, we can try to use it with a tool or just ignore it and npm install. 
# Ignoring bun.lock risk: version drift. 
# Safe bet: `npm install`.

RUN npm install -g @angular/cli
RUN npm install

COPY . .

RUN ng build

# Production stage
FROM oven/bun:1

WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

EXPOSE 4000
CMD ["bun", "run", "serve:ssr"]
