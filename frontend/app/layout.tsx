import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Graby — Tu copiloto de compras",
  description: "Describí lo que querés comprar y Graby arma el carrito por vos.",
  icons: {
    icon: "/graby-icon.png",
    shortcut: "/graby-icon.png",
    apple: "/graby-icon.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  );
}
