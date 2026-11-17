"use client";

import { useDeferredValue, useMemo, useState } from "react";
import type { ApiEntry } from "@/lib/types";
import { ExternalLinkIcon, FilterIcon, ResetIcon, SearchIcon } from "./icons";

const ROLE_LABELS: Record<string, string> = {
  "py:function": "Fungsi",
  "py:class": "Class",
  "py:method": "Method",
  "py:attribute": "Atribut",
  "py:data": "Data",
  "py:exception": "Exception",
};

function roleLabel(role: string) {
  return ROLE_LABELS[role] ?? role.replace("py:", "");
}

export function ApiExplorer({ entries }: { entries: ApiEntry[] }) {
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("all");
  const [limit, setLimit] = useState(80);
  const deferredQuery = useDeferredValue(query);

  const roles = useMemo(
    () => Array.from(new Set(entries.map((entry) => entry.role))).sort(),
    [entries],
  );

  const filtered = useMemo(() => {
    const normalized = deferredQuery.trim().toLowerCase();
    return entries.filter((entry) => {
      if (role !== "all" && entry.role !== role) return false;
      if (!normalized) return true;
      return (
        entry.name.toLowerCase().includes(normalized) ||
        entry.display.toLowerCase().includes(normalized) ||
        entry.doc.toLowerCase().includes(normalized)
      );
    });
  }, [deferredQuery, entries, role]);

  const visible = filtered.slice(0, limit);

  function resetFilters() {
    setQuery("");
    setRole("all");
    setLimit(80);
  }

  return (
    <div className="api-explorer">
      <div className="api-controls">
        <label className="api-search">
          <SearchIcon size={18} />
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setLimit(80);
            }}
            placeholder="Cari nama fungsi, class, method…"
            aria-label="Cari objek API"
            spellCheck={false}
          />
          {query && (
            <button type="button" className="api-clear" onClick={() => setQuery("")}>
              Hapus
            </button>
          )}
        </label>

        <div className="api-role-filters" aria-label="Filter tipe objek">
          <span className="api-filter-label">
            <FilterIcon size={15} />
            Tipe
          </span>
          <button
            type="button"
            className={role === "all" ? "is-active" : undefined}
            onClick={() => {
              setRole("all");
              setLimit(80);
            }}
          >
            Semua
          </button>
          {roles.map((item) => (
            <button
              type="button"
              key={item}
              className={role === item ? "is-active" : undefined}
              onClick={() => {
                setRole(item);
                setLimit(80);
              }}
            >
              {roleLabel(item)}
            </button>
          ))}
        </div>
      </div>

      <div className="api-result-head">
        <p aria-live="polite">
          <strong>{filtered.length.toLocaleString("id-ID")}</strong> objek ditemukan
          {query ? ` untuk “${query}”` : ""}.
        </p>
        {(query || role !== "all") && (
          <button type="button" className="text-button" onClick={resetFilters}>
            <ResetIcon size={14} />
            Reset filter
          </button>
        )}
      </div>

      <div className="api-table" role="table" aria-label="Indeks objek Python">
        <div className="api-table-head" role="row">
          <span role="columnheader">Nama</span>
          <span role="columnheader">Tipe</span>
          <span role="columnheader">Dokumen</span>
          <span role="columnheader" aria-label="Tautan" />
        </div>
        {visible.map((entry) => (
          <a
            className="api-row"
            role="row"
            key={`${entry.role}-${entry.name}`}
            href={entry.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <span className="api-name" role="cell">
              {entry.display !== entry.name ? entry.display : entry.name}
              {entry.display !== entry.name && <small>{entry.name}</small>}
            </span>
            <span role="cell">
              <span className={`api-role api-role-${entry.role.replace("py:", "")}`}>
                {roleLabel(entry.role)}
              </span>
            </span>
            <span className="api-doc" role="cell">
              {entry.doc}
            </span>
            <span className="api-link-icon" role="cell">
              <ExternalLinkIcon size={16} />
            </span>
          </a>
        ))}
      </div>

      {!filtered.length && (
        <div className="api-empty">
          <p>Tidak ada objek yang cocok.</p>
          <button type="button" className="text-button" onClick={resetFilters}>
            Tampilkan semua
          </button>
        </div>
      )}

      {visible.length < filtered.length && (
        <div className="api-more">
          <button type="button" className="button button-ghost" onClick={() => setLimit((value) => value + 80)}>
            Muat {Math.min(80, filtered.length - visible.length)} objek lagi
          </button>
          <span>
            Menampilkan {visible.length} dari {filtered.length}
          </span>
        </div>
      )}
    </div>
  );
}
