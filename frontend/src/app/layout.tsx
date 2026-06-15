import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "gas-analytics",
  description: "European gas market analytics",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/map", label: "Flow map" },
  { href: "/storage", label: "Storage" },
  { href: "/facilities", label: "Facilities" },
  { href: "/lng", label: "LNG" },
  { href: "/demand", label: "Demand" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <div className="brand">gas-analytics</div>
          <nav>
            {NAV.map((n) => (
              <Link key={n.href} href={n.href}>{n.label}</Link>
            ))}
          </nav>
        </header>
        <main className="page">{children}</main>
      </body>
    </html>
  );
}
