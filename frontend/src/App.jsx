import { useState } from 'react'
import FileUpload from './components/FileUpload'
import ConvertButton from './components/ConvertButton'
import ProgressBar from './components/ProgressBar'
import JsonViewer from './components/JsonViewer'
import './App.css'

function App() {
  const [files, setFiles] = useState([])
  const [results, setResults] = useState([])
  const [isConverting, setIsConverting] = useState(false)
  const [error, setError] = useState(null)

  const handleFilesChange = (selectedFiles) => {
    setFiles(selectedFiles)
    setResults([])
    setError(null)
  }

  const handleConvert = async () => {
    if (files.length === 0) {
      setError('Please select at least one PDF file')
      return
    }

    setIsConverting(true)
    setError(null)
    setResults([])

    try {
      // TODO: Implement API call to backend
      // const response = await api.convertFiles(files)
      // setResults(response.data.results)

      // Placeholder for now
      setTimeout(() => {
        setIsConverting(false)
      }, 2000)
    } catch (err) {
      setError('Failed to convert files. Please try again.')
      setIsConverting(false)
    }
  }

  return (
    <div className="app-container">
      <header>
        <h1>医疗电子票据解析器</h1>
        <p>Medical Invoice PDF Parser</p>
      </header>

      <main>
        <FileUpload
          files={files}
          onFilesChange={handleFilesChange}
        />

        <ConvertButton
          onConvert={handleConvert}
          isConverting={isConverting}
          hasFiles={files.length > 0}
        />

        {isConverting && <ProgressBar />}

        {error && <div className="error-message">{error}</div>}

        {results.length > 0 && (
          <JsonViewer results={results} />
        )}
      </main>

      <footer>
        <p>Powered by MinerU + Zhipu GLM</p>
      </footer>
    </div>
  )
}

export default App
