package main

import (
	"context"
	"log"
	"net/http"
	"time"

	"graby/internal/api"
	"graby/internal/config"
	"graby/internal/store"
)

// Version is injected at build time via:
//   -ldflags "-X main.Version=v0.1.0-beta"
var Version = "dev"

func main() {
	cfg := config.Load()
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	repo, err := store.New(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatal(err)
	}
	defer repo.Close()
	if err := repo.Init(ctx); err != nil {
		log.Fatal(err)
	}
	log.Printf("API listening on :%s", cfg.Port)
	if err := http.ListenAndServe(":"+cfg.Port, api.New(repo, cfg.CORSOrigins, Version).Handler()); err != nil {
		log.Fatal(err)
	}
}
