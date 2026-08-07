import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './styles/global.css'
import App from './App'
import EntosisPage from './pages/EntosisPage'
import AnalyticsPage from './pages/AnalyticsPage'
import WarPage from './pages/WarPage'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/entosis" element={<EntosisPage />} />
        <Route path="/war" element={<WarPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
