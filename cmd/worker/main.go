package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"graby/internal/config"
	"graby/internal/store"
	"graby/internal/worker"
)

func main() {
	cfg := config.Load()
	startup, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	repo, err := store.New(startup, cfg.DatabaseURL)
	if err == nil {
		err = repo.Init(startup)
	}
	cancel()
	if err != nil {
		log.Fatal(err)
	}
	defer repo.Close()
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	if err := worker.New(repo, cfg).Run(ctx); err != nil && err != context.Canceled {
		log.Fatal(err)
	}
}
