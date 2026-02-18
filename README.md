# Medical Invoice PDF Parser

A web application that parses Chinese medical electronic invoices (中国医疗电子票据) from PDF format into structured JSON data, using MinerU for document parsing and Zhipu GLM for data structuring.

## Project Overview

This is a personal learning demo project to understand:
- VLM-based document parsing (MinerU internals, pipeline vs VLM backends)
- Full-stack development with React frontend + Python FastAPI backend
- Prompt engineering for structured data extraction with LLMs (Zhipu GLM)
- Integration approaches: cloud API vs self-deployed MinerU

## Tech Stack

- **Frontend:** React 18+ with Vite
- **Backend:** FastAPI (Python)
- **PDF Parsing:** MinerU (open-source, VLM-powered)
- **Data Structuring:** Zhipu GLM API
- **Deployment:** Local development (Phase 1), Kaggle Notebooks for GPU (Phase 2)
- **Environment Management:** Conda

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **Conda** (via Anaconda or Miniconda) - [Download Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- **Node.js 18+ and npm** - [Download Node.js](https://nodejs.org/)
- **Git** - [Download Git](https://git-scm.com/downloads)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd medical-invoice-parser
```

### 2. Set Up Backend

```bash
# Navigate to backend directory
cd backend

# Create and activate conda environment
conda create -n medical-invoice-parser python=3.10 -y
conda activate medical-invoice-parser

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys

Create a `.env` file in the `backend/` directory:

```env
# Zhipu GLM API Key (get from https://open.bigmodel.cn/)
ZHIPU_API_KEY=your_zhipu_api_key_here

# MinerU Online API Token (get from https://mineru.net/apiManage)
MINERU_API_TOKEN=your_mineru_api_token_here
```

**Note:** See `.env.example` for the template.

### 4. Run Backend Server

```bash
# From backend directory with conda environment activated
uvicorn main:app --reload
```

The backend will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

### 5. Set Up Frontend

Open a new terminal:

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install
```

### 6. Run Frontend Development Server

```bash
# From frontend directory
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 7. Use the Application

1. Open your browser and go to `http://localhost:5173`
2. Upload one or more single-page medical invoice PDFs
3. Click the "Convert" button
4. View the resulting JSON data
5. Copy to clipboard or download as `.json` file

## Project Structure

```
medical-invoice-parser/
├── README.md                     # Project overview and setup instructions
├── docs/
│   ├── requirements.md           # Detailed project requirements
│   └── prompts-log.md            # Key Claude Code prompts and learnings
├── frontend/                     # React app (Vite)
│   ├── src/
│   │   ├── App.jsx               # Main application component
│   │   ├── components/           # React components
│   │   │   ├── FileUpload.jsx
│   │   │   ├── ConvertButton.jsx
│   │   │   ├── ProgressBar.jsx
│   │   │   └── JsonViewer.jsx
│   │   └── services/
│   │       └── api.js            # API client for backend calls
├── backend/                      # FastAPI app
│   ├── main.py                   # FastAPI entry point
│   ├── routers/
│   │   └── convert.py            # /convert endpoint
│   ├── services/
│   │   ├── mineru_api.py         # MinerU online API client
│   │   ├── mineru_local.py       # MinerU local integration (Phase 2)
│   │   └── zhipu_structurer.py   # Zhipu GLM integration
│   └── models/
│       └── invoice.py            # Pydantic models for JSON schema
├── notebooks/                    # Kaggle notebooks (Phase 2)
└── samples/                      # Sample invoice PDFs for testing
```

## API Endpoints

### POST `/convert`

Accepts PDF file(s) and returns structured JSON data.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `files` (array of PDF files)

**Response:**
```json
{
  "results": [
    {
      "filename": "invoice.pdf",
      "data": {
        "总金额": 124.56,
        "收款单位": "XX医院",
        "就诊日期": "2024-01-15",
        "医保基金支付金额": 80.00,
        "个人支付": 44.56,
        "个人账户支付": 30.00,
        "个人现金支付": 14.56
      }
    }
  ]
}
```

## Target JSON Schema

Each PDF produces one JSON object. The Pydantic model uses **English field names** internally with **Chinese aliases** so that Zhipu GLM's Chinese-key JSON output can be deserialized directly.

| English Field | Chinese Alias | Type | Description |
|---|---|---|---|
| total_amount | 总金额 | number (2 decimal places) | Total amount on the invoice |
| payee | 收款单位 | string | Hospital / receiving institution name |
| visit_date | 就诊日期 | string (YYYY-MM-DD) | Date of medical visit |
| insurance_payment | 医保基金支付金额 | number (2 decimal places) | Amount paid by medical insurance fund |
| personal_payment | 个人支付 | number (2 decimal places) | Personal payment total |
| personal_account_payment | 个人账户支付 | number (2 decimal places) | Payment from personal medical insurance account |
| personal_cash_payment | 个人现金支付 | number (2 decimal places) | Out-of-pocket cash payment |

> **Note:** The API response serializes with `by_alias=True`, so the JSON keys seen by the frontend remain Chinese.

## Implementation Phases

### Phase 1 - End-to-End with MinerU Online API (Current)
- Everything runs locally
- MinerU called via cloud API (mineru.net)
- No GPU needed
- Focus on full-stack integration

### Phase 2 - Self-Deployed MinerU on Kaggle (Future)
- MinerU runs on Kaggle with GPU
- Compare self-deployed vs API approach
- Learn MinerU internals

## Getting API Keys

### Zhipu GLM API Key
1. Visit [Zhipu AI Platform](https://open.bigmodel.cn/)
2. Register/Login
3. Navigate to API Keys section
4. Create a new API key
5. Free for one month trial period

### MinerU API Token
1. Visit [MinerU](https://mineru.net/)
2. Register/Login
3. Navigate to API Management section
4. Apply for API token (approval required)
4. Free during beta period

## Development Tips

- Run backend with `--reload` flag for auto-restart on code changes
- Run frontend with `npm run dev` for hot module replacement
- Use `http://localhost:8000/docs` to test backend endpoints directly
- Check browser console for frontend errors
- Check terminal for backend errors

## Troubleshooting

### Backend Issues
- **Module not found errors:** Ensure conda environment is activated (`conda activate medical-invoice-parser`)
- **Import errors:** Run `pip install -r requirements.txt` again
- **CORS errors:** Check CORS configuration in `backend/main.py`

### Frontend Issues
- **Module not found errors:** Run `npm install` again
- **Network errors:** Ensure backend server is running on port 8000
- **Build errors:** Clear node_modules and reinstall: `rm -rf node_modules && npm install`

## Resources

- [MinerU GitHub](https://github.com/opendatalab/MinerU)
- [MinerU Documentation](https://opendatalab.github.io/MinerU/)
- [MinerU Online API Docs](https://mineru.net/apiManage/docs)
- [Zhipu AI Platform](https://open.bigmodel.cn/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vite Documentation](https://vitejs.dev/)

## License

This project is for educational purposes only.
