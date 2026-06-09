import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './styles/global.css'
import App from './App'
import EntosisPage from './pages/EntosisPage'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/entosis" element={<EntosisPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
