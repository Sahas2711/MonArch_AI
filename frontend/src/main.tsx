import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App"
import "./styles/theme.css"
import "./styles/auth-nav.css"
import "./styles/views.css"
import "./styles/chat.css"
import "./styles/auth-forms.css"

const stored = localStorage.getItem("monarch.theme") || localStorage.getItem("wemboo.theme")
document.documentElement.setAttribute("data-theme", stored === "dark" ? "dark" : "light")

/* default landing route so the first paint has a real URL */
if (!window.location.hash) window.location.hash = "#/"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
