import "./globals.css";
import TopBar from "@/components/TopBar";
import StatusBar from "@/components/StatusBar";

export const metadata = {
  title: "GAS-ANAL · European Gas Terminal",
  description: "European gas market analytics — flows, storage, LNG, demand forecast",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <TopBar />
        <main className="page">{children}</main>
        <StatusBar />
      </body>
    </html>
  );
}
