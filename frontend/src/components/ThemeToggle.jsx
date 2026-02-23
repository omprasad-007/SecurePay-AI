import React from "react";
import { useTheme } from "../App.jsx";

const modes = ["light", "dark", "vibrant"];

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const next = () => {
    const idx = modes.indexOf(theme);
    const nextMode = modes[(idx + 1) % modes.length];
    setTheme(nextMode);
  };

  return <button className="btn-outline" onClick={next}>Theme: {theme}</button>;
}
