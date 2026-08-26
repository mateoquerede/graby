// Package guard agrupa los filtros de texto que validan los pedidos del usuario
// antes de procesarlos. Las listas de términos son configurables para poder
// extenderlas sin tocar la lógica.
package guard

import (
	"regexp"
	"strings"
)

// ShoppingTerms son palabras que sugieren una intención de compra o de
// preparar una receta/idea. Se pueden extender desde el código que importa
// el paquete.
var ShoppingTerms = []string{
	// Productos y categorías de supermercado.
	"agua", "alimento", "arroz", "bebida", "bizcocho", "branca", "cafe",
	"carrito", "carne", "cerveza", "chocolate", "condimento", "desodorante",
	"detergente", "dulce", "fideos", "galleta", "gaseosa", "fernet", "harina",
	"higiene", "huevo", "jabon", "jugo", "leche", "limpieza", "manteca",
	"mayonesa", "pan", "papel", "pasta", "pollo", "producto", "queso", "sal",
	"shampoo", "supermercado", "vino", "yogur", "yerba",
	// Acciones de compra.
	"compra", "comprar",
	// Recetas e ideas de preparación.
	"torta", "taco", "receta", "hacer", "preparar", "cocinar", "necesario",
	"necesita", "idea", "ingrediente", "elaborar", "armar", "plato", "comida",
	"menu", "menú", "desayuno", "almuerzo", "cena",
}

// ShoppingQuantityPattern matchea una cantidad con su unidad de medida.
var ShoppingQuantityPattern = regexp.MustCompile(`(?i)\b\d+(?:[.,]\d+)?\s*(?:kg|kgs|kilo(?:s)?|g|gr|gramo(?:s)?|l|lt|lts|litro(?:s)?|ml|unidad(?:es)?|pack|caja(?:s)?|botella(?:s)?)\b`)

// AnyNumberPattern matchea cualquier número suelto.
var AnyNumberPattern = regexp.MustCompile(`\b\d+(?:[.,]\d+)?\b`)

// InjectionPattern detecta intentos de inyección de instrucciones.
var InjectionPattern = regexp.MustCompile(`(?is)\b(ignore|ignora|olvida|forget|disregard)\b.{0,40}\b(instrucciones?|rules?|reglas?)\b|\b(system|developer|assistant)\s*:|\b(exec|execute|ejecuta|python|powershell|shell|comando)\b`)

// LooksLikeShoppingRequest devuelve true si el texto parece un pedido de
// compra o una receta/idea de preparación. Acepta términos de la lista
// ShoppingTerms o cantidades con unidad.
func LooksLikeShoppingRequest(value string) bool {
	for _, term := range ShoppingTerms {
		if regexp.MustCompile(`(?i)\b` + term + `\b`).MatchString(value) {
			return true
		}
	}
	return ShoppingQuantityPattern.MatchString(value) || len(AnyNumberPattern.FindAllString(value, -1)) >= 2
}

// Injection devuelve true si el texto contiene instrucciones no permitidas.
func Injection(value string) bool {
	return InjectionPattern.MatchString(value)
}

// HasAnyTerm devuelve true si el texto contiene alguno de los términos dados.
// Útil para extender el guard con términos propios sin tocar la lista global.
func HasAnyTerm(value string, terms ...string) bool {
	for _, term := range terms {
		if regexp.MustCompile(`(?i)\b` + term + `\b`).MatchString(value) {
			return true
		}
	}
	return false
}

// Normalize limpia y normaliza un texto para comparaciones.
func Normalize(value string) string {
	return strings.Join(strings.Fields(strings.ToLower(value)), " ")
}