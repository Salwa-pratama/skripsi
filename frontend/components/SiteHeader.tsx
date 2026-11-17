"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "./Logo";
import { SearchDialog } from "./SearchDialog";
import { ThemeToggle } from "./ThemeToggle";
import { CloseIcon, MenuIcon, SearchIcon } from "./icons";
import { GamificationBar } from "./GamificationBar";

const links = [
  { href: "/materi", label: "Materi" },
  { href: "/indeks", label: "Indeks API" },
  { href: "/sumber", label: "Sumber" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <>
      <header className="site-header">
        <div className="container header-inner">
          <Logo />

          <nav className="desktop-nav" aria-label="Navigasi utama">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={isActive(link.href) ? "is-active" : undefined}
                aria-current={isActive(link.href) ? "page" : undefined}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <GamificationBar />

          <div className="header-actions">
            <button
              type="button"
              className="search-trigger"
              onClick={() => setSearchOpen(true)}
              aria-label="Cari materi (Ctrl+K)"
            >
              <SearchIcon size={17} />
              <span>Cari materi</span>
              <kbd>Ctrl K</kbd>
            </button>
            <ThemeToggle />
            <button
              type="button"
              className="icon-button menu-toggle"
              onClick={() => setMenuOpen((value) => !value)}
              aria-expanded={menuOpen}
              aria-controls="mobile-navigation"
              aria-label={menuOpen ? "Tutup menu" : "Buka menu"}
            >
              {menuOpen ? <CloseIcon size={20} /> : <MenuIcon size={20} />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <nav id="mobile-navigation" className="mobile-nav" aria-label="Navigasi seluler">
            <div className="container">
              {links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={isActive(link.href) ? "is-active" : undefined}
                >
                  {link.label}
                </Link>
              ))}
              <button
                type="button"
                className="mobile-search-button"
                onClick={() => {
                  setMenuOpen(false);
                  setSearchOpen(true);
                }}
              >
                <SearchIcon size={18} />
                Cari materi
              </button>
            </div>
          </nav>
        )}
      </header>

      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
