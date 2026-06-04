import type { ReactNode } from "react";

type Variant = "success" | "warning" | "error" | "info" | "neutral";

interface Props {
  variant?: Variant;
  children: ReactNode;
}

const variantStyle: Record<Variant, { background: string; color: string; border: string }> = {
  success: { background: "var(--color-success-dim)", color: "var(--color-success)", border: "rgba(52,211,153,0.2)" },
  warning: { background: "var(--color-warning-dim)", color: "var(--color-warning)", border: "rgba(251,191,36,0.2)" },
  error: { background: "var(--color-error-dim)", color: "var(--color-error)", border: "rgba(248,113,113,0.2)" },
  info: { background: "var(--color-accent-dim)", color: "var(--color-accent-hover)", border: "rgba(99,102,241,0.2)" },
  neutral: { background: "rgba(255,255,255,0.06)", color: "var(--color-text-secondary)", border: "var(--color-border)" },
};

export function Badge({ variant = "neutral", children }: Props) {
  const s = variantStyle[variant];
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      padding: "2px 8px",
      borderRadius: "var(--radius-full)",
      fontSize: "var(--text-xs)",
      fontWeight: "var(--weight-medium)",
      background: s.background,
      color: s.color,
      border: `1px solid ${s.border}`,
      lineHeight: 1.6,
    }}>
      {children}
    </span>
  );
}
