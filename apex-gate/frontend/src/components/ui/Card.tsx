import type { CSSProperties, MouseEventHandler, ReactNode } from "react";

interface Props {
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
  glow?: boolean;
  onClick?: MouseEventHandler<HTMLDivElement>;
}

export function Card({ children, style, className, glow, onClick }: Props) {
  return (
    <div
      className={className}
      onClick={onClick}
      style={{
        background: "var(--color-bg-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-6)",
        boxShadow: glow ? "var(--shadow-accent)" : "var(--shadow-sm)",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
