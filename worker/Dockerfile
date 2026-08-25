FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /graby-worker ./cmd/worker

FROM alpine:3.20
RUN apk add --no-cache ca-certificates && adduser -D -H -u 10001 graby
USER graby
COPY --from=build /graby-worker /graby-worker
ENTRYPOINT ["/graby-worker"]
