import React from 'react'

function App() {
  const config = window.absenzflowConfig

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          AbsenzFlow
        </h1>
        
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                <strong>Willkommen, {config.user.displayName}!</strong>
              </p>
              <p className="text-sm text-blue-600 mt-1">
                Rolle: {config.user.role}
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-gray-50 p-4 rounded-md">
            <h2 className="text-lg font-semibold mb-2">🚀 Entwicklung</h2>
            <p className="text-gray-600">
              Dies ist ein Platzhalter für die React-App. Die vollständige Implementierung
              folgt mit Claude Code.
            </p>
          </div>

          <div className="bg-gray-50 p-4 rounded-md">
            <h2 className="text-lg font-semibold mb-2">📋 Nächste Schritte</h2>
            <ul className="list-disc list-inside text-gray-600 space-y-1">
              <li>Abwesenheitsformular erstellen</li>
              <li>Stundenplan-Integration</li>
              <li>Dashboard für verschiedene Rollen</li>
              <li>Benachrichtigungen anzeigen</li>
            </ul>
          </div>

          <div className="bg-gray-50 p-4 rounded-md">
            <h2 className="text-lg font-semibold mb-2">⚙️ Konfiguration</h2>
            <p className="text-sm text-gray-600">API URL: {config.apiUrl || 'Nicht konfiguriert'}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
