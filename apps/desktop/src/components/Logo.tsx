// The InClave mark — an inward arrow (data enters) held inside a rounded
// enclosure (the on-device enclave). Used wherever the brand glyph appears
// (assistant avatar, empty state, onboarding) instead of a generic spark.
//
// `variant`:
//   - "glyph"  → just the frame + arrow, inherits currentColor (for inline use
//                on tinted backgrounds, e.g. the assistant avatar).
//   - "badge"  → the full app-icon treatment (ink ground, white frame, indigo
//                arrow) inside a rounded square, for hero / onboarding.

export function Logo({
  className,
  variant = "glyph",
  title = "InClave",
}: {
  className?: string;
  variant?: "glyph" | "badge";
  title?: string;
}) {
  if (variant === "badge") {
    // Tighter geometry than the app-icon master: the mark fills more of the
    // square (thicker frame, larger arrow) so it stays legible at small inline
    // sizes like the 28px titlebar badge. The OS adds its own padding for the
    // dock icon, so the standalone .icns still breathes.
    return (
      <svg
        viewBox="0 0 1024 1024"
        className={className}
        role="img"
        aria-label={title}
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect width="1024" height="1024" rx="232" fill="#0F0F14" />
        <rect
          x="436"
          y="276"
          width="324"
          height="472"
          rx="128"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth="74"
        />
        <path d="M226 512 L388 404 V620 Z" fill="#6C63FF" />
      </svg>
    );
  }

  // Glyph: frame uses currentColor; arrow uses the brand accent. Scales cleanly
  // and reads on any background the caller tints.
  return (
    <svg
      viewBox="0 0 1024 1024"
      className={className}
      role="img"
      aria-label={title}
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect
        x="402"
        y="300"
        width="322"
        height="424"
        rx="118"
        fill="none"
        stroke="currentColor"
        strokeWidth="64"
      />
      <path d="M250 512 L364 436 V588 Z" fill="currentColor" />
    </svg>
  );
}
