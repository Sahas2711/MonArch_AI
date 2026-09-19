import React, { useEffect } from "react"
import { useApp } from "./store/app"
import { Shell } from "./components/Shell"
import { Toaster } from "./components/ui"
import { routeById } from "./lib/router"
import { Landing } from "./views/Landing"
import { SignIn } from "./views/SignIn"
import { Dashboard } from "./views/Dashboard"
import { Analyze } from "./views/Analyze"
import { Report } from "./views/Report"
import { History } from "./views/History"
import { Negotiate } from "./views/Negotiate"
import { Calculator } from "./views/Calculator"
import { Copilot } from "./views/Copilot"
import { Knowledge } from "./views/Knowledge"
import { Organization } from "./views/Organization"
import { Billing } from "./views/Billing"
import { ApiKeys } from "./views/ApiKeys"
import { Settings } from "./views/Settings"
import { Admin } from "./views/Admin"

const App: React.FC = () => {
  const { route, theme, signedIn, role } = useApp()

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
  }, [theme])

  const meta = routeById(route)

  /* route guard: every workspace screen needs a verified session, admin needs a role */
  const blocked = (meta.protected && !signedIn) || (meta.adminOnly && role !== "admin")

  const view = () => {
    switch (route) {
      case "dashboard": return <Dashboard />
      case "analyze": return <Analyze />
      case "report": return <Report />
      case "history": return <History />
      case "negotiate": return <Negotiate />
      case "calculator": return <Calculator />
      case "copilot": return <Copilot />
      case "knowledge": return <Knowledge />
      case "organization": return <Organization />
      case "billing": return <Billing />
      case "keys": return <ApiKeys />
      case "settings": return <Settings />
      case "admin": return <Admin />
      default: return <Dashboard />
    }
  }

  let body: React.ReactNode
  if (blocked) body = <SignIn />
  else if (route === "landing") body = <Landing />
  else if (route === "signin") body = signedIn ? <Shell>{<Dashboard />}</Shell> : <SignIn />
  else body = <Shell flush={route === "copilot"}>{view()}</Shell>

  return (
    <>
      {body}
      <Toaster />
    </>
  )
}

export default App
