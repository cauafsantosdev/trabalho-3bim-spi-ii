"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AddIcon, InfoIcon, SearchIcon } from "./Icons";

const links = [
  { href: "/", label: "Consulta", icon: SearchIcon },
  { href: "/servidores/novo", label: "Novo registro", icon: AddIcon },
  { href: "/sobre", label: "Sobre a base", icon: InfoIcon },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="Arquivo Servidores — página inicial">
          <span>Arquivo /</span><strong>Servidores</strong>
        </Link>
        <nav className="main-nav" aria-label="Navegação principal">
          {links.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link className={active ? "nav-link active" : "nav-link"} href={href} key={href}>
                <Icon /><span>{label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
