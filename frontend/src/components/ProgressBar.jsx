import './ProgressBar.css'

function ProgressBar() {
  return (
    <div className="progress-bar-container">
      <div className="progress-bar">
        <div className="progress-bar-fill"></div>
      </div>
      <p className="progress-text">Processing your files...</p>
    </div>
  )
}

export default ProgressBar
