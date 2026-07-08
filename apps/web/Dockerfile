# syntax=docker/dockerfile:1
#
# Built from the repository root (see the compose file) so pnpm can resolve the
# workspace packages this app depends on (@dcip/ui, @dcip/shared, @dcip/types).

# --- Builder -----------------------------------------------------------------
FROM node:20-slim AS builder
ENV PNPM_HOME=/pnpm
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /repo

# Copy workspace manifests first for dependency-layer caching.
COPY package.json pnpm-workspace.yaml turbo.json tsconfig.base.json ./
COPY packages ./packages
COPY apps/web ./apps/web

RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --filter @dcip/web... --frozen-lockfile=false

# Build only the web app (and its workspace deps).
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN pnpm --filter @dcip/web build

# --- Runtime: static files served by NGINX -----------------------------------
FROM nginx:1.27-alpine AS runtime
COPY infrastructure/nginx/web.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /repo/apps/web/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
