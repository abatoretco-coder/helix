FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_MEILI_URL=http://localhost:7700
ARG NEXT_PUBLIC_MEILI_SEARCH_KEY=

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_MEILI_URL=$NEXT_PUBLIC_MEILI_URL
ENV NEXT_PUBLIC_MEILI_SEARCH_KEY=$NEXT_PUBLIC_MEILI_SEARCH_KEY

RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/package*.json ./
RUN npm ci --production

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "start"]
