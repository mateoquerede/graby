import { CartItem, ProposedItem } from "../Chat.types";

export const DEMO_MESSAGE = "Comprame cosas para hacer tacos para 4 personas.";

export const DEMO_ITEMS: ProposedItem[] = [
  { query: "Tortillas de maíz", quantity: 2 },
  { query: "Carne picada", quantity: 1 },
  { query: "Cebolla", quantity: 2 },
  { query: "Tomate", quantity: 3 },
  { query: "Lechuga", quantity: 1 },
  { query: "Queso rallado", quantity: 1 },
  { query: "Salsa picante", quantity: 1 },
];

export const DEMO_CART: CartItem[] = [
  {
    requested: "tortillas",
    name: "Tortillas de maíz",
    quantity: 2,
    price: 1200,
    reason: "Elegí las de maíz en vez de las de harina: son las clásicas para tacos y rinden más para 4 personas.",
  },
  {
    requested: "carne",
    name: "Carne picada",
    quantity: 1,
    price: 4500,
    reason: "Opté por carne picada de ternera en vez de la de cerdo: es más versátil para el relleno y rinde mejor.",
  },
  {
    requested: "cebolla",
    name: "Cebolla",
    quantity: 2,
    price: 800,
    reason: "Compré la cebolla común en vez de la morada: es más barata y una va al sofrito, la otra al pico de gallo.",
  },
  {
    requested: "tomate",
    name: "Tomate",
    quantity: 3,
    price: 1500,
    reason: "Elegí tomates redondos en vez de los perita: estaban más baratos y maduros, ideales para el pico de gallo.",
  },
  {
    requested: "lechuga",
    name: "Lechuga",
    quantity: 1,
    price: 900,
    reason: "Una capuchina en vez de la mantecosa: rinde más y alcanza y sobra para el toque fresco de los tacos.",
  },
  {
    requested: "queso",
    name: "Queso rallado",
    quantity: 1,
    price: 1800,
    reason: "Elegí el rallado en sachet en vez del bloque: es más barato y rinde igual para gratinar cada taco.",
  },
  {
    requested: "salsa",
    name: "Salsa picante",
    quantity: 1,
    price: 1100,
    reason: "Elegí una de mediana potencia en vez de la extra fuerte: sé que te gusta el picante pero no demasiado.",
  },
];

export const DEMO_TOTAL = DEMO_CART.reduce((sum, item) => sum + (item.price ?? 0) * item.quantity, 0);
