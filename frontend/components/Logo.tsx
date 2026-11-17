import Link from "next/link";

export function Logo() {
  return (
    <Link href="/" className="brand" aria-label="PyJourney — beranda">
      <span className="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 32 32" fill="none">
          <path
            d="M11.5 9.5 7 16l4.5 6.5"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M20.5 9.5 25 16l-4.5 6.5"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M18 8 14 24"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
          />
        </svg>
      </span>
      <span className="brand-name">
        Py<span>Journey</span>
      </span>
    </Link>
  );
}
