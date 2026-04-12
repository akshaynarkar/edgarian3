import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./theme/tokens.css";

const mountNode = document.getElementById("root");
mountNode.id = "app";

const storedTheme = window.localStorage.getItem("edgarian-theme") || "dark";
if (storedTheme === "light") {
  mountNode.classList.add("light");
} else {
  mountNode.classList.remove("light");
}

ReactDOM.createRoot(mountNode).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
