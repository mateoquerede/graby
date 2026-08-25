FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /graby-api ./cmd/api

FROM alpine:3.20
RUN apk add --no-cache ca-certificates && adduser -D -H -u 10001 graby
USER graby
COPY --from=build /graby-api /graby-api
EXPOSE 8000
ENTRYPOINT ["/graby-api"]
