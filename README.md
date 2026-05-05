# CotoBot

Un bot automatizado para hacer compras en Coto Digital usando Playwright y Ollama.

## Estructura del Proyecto

- `src/`: Código fuente del proyecto
  - `main.py`: Punto de entrada principal
  - `planner.py`: Planifica búsquedas usando IA
  - `login.py`: Maneja el login al sitio
  - `cart.py`: Gestiona el carrito de compras
  - `search.py`: Funciones de búsqueda de productos
  - `product_parser.py`: Parsing de información de productos
  - `add_product.py`: Agrega productos al carrito
  - `evaluator.py`: Evalúa productos usando IA
  - `config.py`: Carga configuraciones desde JSON
  - `requirements.txt`: Dependencias Python
  - `run.bat`: Script para ejecutar en Windows

- Archivos de configuración (JSON):
  - `lista.json`: Lista de productos a comprar
  - `settings.json`: Credenciales de login (copiar de `settings.example.json`)
  - `rules.json`: Reglas para la evaluación de productos
  - `bloqueados.json`: PLUs bloqueados

## Instalación

1. Instalar dependencias: `pip install -r src/requirements.txt`
2. Instalar Ollama y el modelo llama3
3. Copiar `settings.example.json` a `settings.json` y configurar con tus credenciales
4. Ejecutar: `python src/main.py` o usar run.bat

## Funcionamiento

El bot carga la lista de productos, planifica búsquedas, se loguea, limpia el carrito, busca y agrega productos automáticamente, y deja el carrito listo para pago manual.