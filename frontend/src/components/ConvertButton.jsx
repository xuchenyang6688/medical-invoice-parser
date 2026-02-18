import './ConvertButton.css'

function ConvertButton({ onConvert, isConverting, hasFiles }) {
  return (
    <div className="convert-button-container">
      <button
        className={`convert-button ${isConverting ? 'converting' : ''} ${!hasFiles ? 'disabled' : ''}`}
        onClick={onConvert}
        disabled={isConverting || !hasFiles}
        type="button"
      >
        {isConverting ? (
          <>
            <span className="spinner"></span>
            Converting...
          </>
        ) : (
          'Convert'
        )}
      </button>
    </div>
  )
}

export default ConvertButton
