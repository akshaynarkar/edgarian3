import React, { useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

export default function NavBar() {
  const location = useLocation();
  const appNode = document.getElementById("app");
  const initialTheme = appNode?.classList.contains("light") ? "light" : "dark";
  const [theme, setTheme] = useState(initialTheme);

  const navLinks = useMemo(
    () => [
      { to: "/", label: "Search" },
      { to: "/company/AAPL", label: "Company" },
    ],
    [],
  );

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    appNode?.classList.toggle("light", nextTheme === "light");
    document.querySelectorAll('iframe').forEach(f => f.contentWindow?.postMessage({type:'edgarian-theme', isLight: !isDark}, '*'));
    window.localStorage.setItem("edgarian-theme", nextTheme);
    setTheme(nextTheme);
  };

  return (
    <nav className="nav">
      <div className="nav-left">
        <Link className="nav-logo" to="/">
          Edgarian
        </Link>

        {navLinks.map((link) => {
          const isActive =
            link.to === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith("/company");

          return (
            <Link
              key={link.to}
              className={`nav-link ${isActive ? "is-active" : ""}`}
              to={link.to}
            >
              {link.label}
            </Link>
          );
        })}
      </div>

      <div className="nav-right">
        <button className="mode-btn" type="button" onClick={toggleTheme}>
          {theme === "dark" ? "☀ Light" : "☾ Dark"}
        </button>
      </div>
    </nav>
  );
}
