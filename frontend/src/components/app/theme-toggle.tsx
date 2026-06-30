import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/lib/use-theme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={toggle}
      aria-label="Toggle theme"
      title="Toggle theme"
    >
      {theme === "dark" ? <Sun /> : <Moon />}
    </Button>
  );
}
