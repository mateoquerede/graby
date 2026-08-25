package openrouter

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

type Client struct {
	key, baseURL string
	models       []string
	http         *http.Client
}

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

func New(key, model string, fallbacks []string, baseURL string, timeout time.Duration) *Client {
	models := make([]string, 0, len(fallbacks)+1)
	if model = strings.TrimSpace(model); model != "" {
		models = append(models, model)
	}
	for _, fallback := range fallbacks {
		if fallback = strings.TrimSpace(fallback); fallback != "" {
			models = append(models, fallback)
		}
	}
	return &Client{key: key, baseURL: strings.TrimRight(baseURL, "/"), models: models, http: &http.Client{Timeout: timeout}}
}

func (c *Client) CompleteJSON(ctx context.Context, messages []Message, maxTokens int, temperature float64) (string, error) {
	if c.key == "" {
		return "", fmt.Errorf("OPENROUTER_API_KEY no está configurada.")
	}
	if len(c.models) == 0 {
		return "", fmt.Errorf("OPENROUTER_MODEL no está configurado.")
	}
	var failures []string
	for _, model := range c.models {
		for attempt := 0; attempt < 2; attempt++ {
			body := map[string]any{
				"model": model, "messages": messages, "temperature": temperature, "max_tokens": maxTokens,
				"response_format": map[string]string{"type": "json_object"},
				"reasoning":       map[string]any{"exclude": true, "effort": "low"},
			}
			data, _ := json.Marshal(body)
			request, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/chat/completions", bytes.NewReader(data))
			if err != nil {
				return "", err
			}
			request.Header.Set("Authorization", "Bearer "+c.key)
			request.Header.Set("Content-Type", "application/json")
			request.Header.Set("HTTP-Referer", "https://heygraby.com")
			request.Header.Set("X-Title", "Graby")
			response, err := c.http.Do(request)
			if err != nil {
				failures = append(failures, fmt.Sprintf("%s intento %d: %v", model, attempt+1, err))
				continue
			}
			responseBody, _ := io.ReadAll(io.LimitReader(response.Body, 1<<20))
			response.Body.Close()
			if response.StatusCode < 200 || response.StatusCode >= 300 {
				failures = append(failures, fmt.Sprintf("%s: HTTP %d: %s", model, response.StatusCode, truncate(string(responseBody), 300)))
				break
			}
			var result struct {
				Choices []struct {
					Message struct {
						Content   json.RawMessage `json:"content"`
						Reasoning string          `json:"reasoning"`
					} `json:"message"`
				} `json:"choices"`
			}
			if err := json.Unmarshal(responseBody, &result); err != nil || len(result.Choices) == 0 {
				failures = append(failures, fmt.Sprintf("%s intento %d: respuesta inválida", model, attempt+1))
				continue
			}
			content := string(result.Choices[0].Message.Content)
			var stringContent string
			if json.Unmarshal(result.Choices[0].Message.Content, &stringContent) == nil {
				content = stringContent
			}
			if strings.TrimSpace(content) == "" {
				content = result.Choices[0].Message.Reasoning
			}
			if strings.TrimSpace(content) != "" {
				return strings.TrimSpace(content), nil
			}
			failures = append(failures, fmt.Sprintf("%s intento %d: OpenRouter devolvió contenido vacío.", model, attempt+1))
		}
	}
	return "", fmt.Errorf("Todos los modelos de OpenRouter fallaron: %s", strings.Join(failures, "; "))
}

func truncate(value string, max int) string {
	if len(value) > max {
		return value[:max]
	}
	return value
}
