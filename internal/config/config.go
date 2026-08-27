package config

import (
	"bufio"
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	DatabaseURL       string
	Port              string
	CORSOrigins       []string
	OpenRouterKey     string
	OpenRouterModel   string
	OpenRouterModels  []string
	OpenRouterBaseURL string
	OpenRouterTimeout time.Duration
	CotoSearchKey     string
	Provider          string
	Debug             bool
}

func Load() Config {
	loadDotEnv(".env")
	origins := split(os.Getenv("CORS_ORIGINS"))
	if len(origins) == 0 {
		origins = []string{"https://heygraby.com", "https://www.heygraby.com"}
	}

	models := split(os.Getenv("OPENROUTER_FALLBACK_MODELS"))
	if legacy := strings.TrimSpace(os.Getenv("OPENROUTER_FALLBACK_MODEL")); legacy != "" {
		models = append(models, legacy)
	}
	timeout := 60
	if parsed, err := strconv.Atoi(os.Getenv("OPENROUTER_TIMEOUT")); err == nil && parsed > 0 {
		timeout = parsed
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}
	base := os.Getenv("OPENROUTER_BASE_URL")
	if base == "" {
		base = "https://openrouter.ai/api/v1"
	}
	return Config{
		DatabaseURL:       env("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/graby?sslmode=disable"),
		Port:              port,
		CORSOrigins:       origins,
		OpenRouterKey:     os.Getenv("OPENROUTER_API_KEY"),
		OpenRouterModel:   os.Getenv("OPENROUTER_MODEL"),
		OpenRouterModels:  models,
		OpenRouterBaseURL: strings.TrimRight(base, "/"),
		OpenRouterTimeout: time.Duration(timeout) * time.Second,
		CotoSearchKey:     os.Getenv("COTO_SEARCH_API_KEY"),
		Provider:          env("GRABY_PROVIDER", "coto"),
		Debug:             truthy(os.Getenv("GRABY_DEBUG")),
	}
}

// loadDotEnv preserves the Python service's local .env behavior without
// overriding values injected by a deployment environment.
func loadDotEnv(path string) {
	file, err := os.Open(path)
	if err != nil {
		return
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		key, value, found := strings.Cut(line, "=")
		if !found || os.Getenv(strings.TrimSpace(key)) != "" {
			continue
		}
		value = strings.Trim(strings.TrimSpace(value), `"'`)
		_ = os.Setenv(strings.TrimSpace(key), value)
	}
}

func split(value string) []string {
	var result []string
	for _, value := range strings.Split(value, ",") {
		if value = strings.TrimSpace(value); value != "" {
			result = append(result, value)
		}
	}
	return result
}

func env(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}

func truthy(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "1", "true", "yes", "on":
		return true
	}
	return false
}
