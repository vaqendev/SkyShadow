import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { Button } from "@/components/ui/button";

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    {/* <Button size="lg" variant="outline"> hello world </Button> */}
  </StrictMode>,
)
