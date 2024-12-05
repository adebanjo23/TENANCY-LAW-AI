# Ontario Tenancy Law Assistant

An AI-powered legal assistant for Ontario tenancy law inquiries and rental contract analysis.

## Features

- Interactive chat interface for tenancy law questions
- Contract analysis against Ontario regulations
- Document upload and processing (PDF, DOCX)
- Chat history management
- Multiple LLM provider support

## Requirements

- Python 3.9+
- Streamlit
- LangChain
- LlamaParse
- OpenAI/Groq/Anthropic/Gemini API access



## Configuration

1. Create `.env` file:
```env
OPENAI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
LLAMA_CLOUD_API_KEY=your_key_here
```

2. Configure LLM settings in `src/config.py`

## Usage

Run the Streamlit app:
```bash
streamlit run ui/streamlit_app.py
```