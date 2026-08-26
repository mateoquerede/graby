import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-poppins",
});

export const metadata: Metadata = {
  title: "Graby — Tu copiloto de compras",
  description: "Describí lo que querés comprar y Graby arma el carrito por vos.",
  icons: {
    icon: "/graby-icon.png",
    shortcut: "/graby-icon.png",
    apple: "/graby-icon.png",
  },
};

// Aplica el tema antes de pintar para evitar el parpadeo (FOUC).
const themeScript = `(function(){try{var t=localStorage.getItem("graby-theme")||"system";var d=t==="dark"||(t==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.classList.toggle("dark",d);var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute("content",d?"#0b1020":"#f8fafc");}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${poppins.variable} font-sans text-gray-900 antialiased`}>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
