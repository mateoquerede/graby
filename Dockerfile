FROM golang:1.22-alpine AS build

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN APP_VERSION=$(cat VERSION) && \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -X main.Version=${APP_VERSION}" -o /out/graby-api ./cmd/api && \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/graby-worker ./cmd/worker

FROM alpine:3.20 AS api
RUN apk add --no-cache ca-certificates && adduser -D -H -u 10001 graby
USER graby
COPY --from=build /out/graby-api /graby-api
EXPOSE 8000
ENTRYPOINT ["/graby-api"]

FROM alpine:3.20 AS worker
RUN apk add --no-cache ca-certificates && adduser -D -H -u 10001 graby
USER graby
COPY --from=build /out/graby-worker /graby-worker
ENTRYPOINT ["/graby-worker"]
