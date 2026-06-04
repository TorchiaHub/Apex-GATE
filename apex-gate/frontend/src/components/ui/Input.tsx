import type { InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, id, style, ...rest }: Props) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
      {label && (
        <label htmlFor={inputId} style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)", fontWeight: "var(--weight-medium)" }}>
          {label}
        </label>
      )}
      <input
        id={inputId}
        style={{
          background: "var(--color-bg-elevated)",
          border: `1px solid ${error ? "var(--color-error)" : "var(--color-border)"}`,
          borderRadius: "var(--radius-md)",
          padding: "var(--space-2) var(--space-3)",
          color: "var(--color-text-primary)",
          fontSize: "var(--text-sm)",
          outline: "none",
          transition: "border-color var(--duration-fast)",
          width: "100%",
          ...style,
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = "var(--color-accent)"; }}
        onBlur={(e) => { e.currentTarget.style.borderColor = error ? "var(--color-error)" : "var(--color-border)"; }}
        {...rest}
      />
      {error && <span style={{ fontSize: "var(--text-xs)", color: "var(--color-error)" }}>{error}</span>}
    </div>
  );
}
