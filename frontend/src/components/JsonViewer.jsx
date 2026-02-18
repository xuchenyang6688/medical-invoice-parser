import { useState } from 'react'
import './JsonViewer.css'

function JsonViewer({ results }) {
  const [copiedIndex, setCopiedIndex] = useState(null)

  const handleCopy = (jsonString, index) => {
    navigator.clipboard.writeText(jsonString).then(() => {
      setCopiedIndex(index)
      setTimeout(() => setCopiedIndex(null), 2000)
    })
  }

  const handleDownload = (result, index) => {
    const jsonString = JSON.stringify(result.data, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${result.filename.replace('.pdf', '')}_extracted.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="json-viewer-container">
      <h2>Results</h2>
      {results.map((result, index) => (
        <div key={index} className="json-result-card">
          <div className="json-result-header">
            <h3>{result.filename}</h3>
            <div className="json-result-actions">
              <button
                className="action-button copy-button"
                onClick={() => handleCopy(JSON.stringify(result.data, null, 2), index)}
                type="button"
              >
                {copiedIndex === index ? 'Copied!' : 'Copy'}
              </button>
              <button
                className="action-button download-button"
                onClick={() => handleDownload(result, index)}
                type="button"
              >
                Download
              </button>
            </div>
          </div>
          <pre className="json-output">
            {JSON.stringify(result.data, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  )
}

export default JsonViewer
