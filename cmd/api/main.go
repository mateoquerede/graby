package main

import (
	"context"
	"log"
	"net/http"
	"time"

	"github.com/heygraby/graby/internal/api"
	"github.com/heygraby/graby/internal/config"
	"github.com/heygraby/graby/internal/store"
)

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
	if err := http.ListenAndServe(":"+cfg.Port, api.New(repo, cfg.CORSOrigins).Handler()); err != nil {
		log.Fatal(err)
	}
}
