import logging
from typing import Optional, List
from dataclasses import dataclass
import streamlit as st
import asyncio
import os
import tempfile
from src.config import LLMProvider
from src.llm.llm_factory import create_llm
from services.legal_assistant import LegalAssistant
from services.document_processor import DocumentProcessor, DocumentFile, DocumentType, DocumentProcessingError
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProcessedDocument:
    content: str
    file_name: str
    num_pages: int
    doc_type: str


class DocumentProcessingService:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.logger = logging.getLogger(__name__)

    async def process_document(self, file_content: bytes, file_name: str) -> ProcessedDocument:
        try:
            self.logger.info(f"Starting document processing for {file_name}")
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name

            try:
                parsed_docs = await self.doc_processor.parse_document([temp_file_path])
                if not parsed_docs:
                    raise DocumentProcessingError("No content extracted from document")

                contents = []
                for i, doc in enumerate(parsed_docs):
                    self.logger.debug(f"Processing section {i + 1}")
                    if hasattr(doc, 'page_content'):
                        content = doc.page_content
                    elif hasattr(doc, 'text'):
                        content = doc.text
                    elif isinstance(doc, dict):
                        content = doc.get('text', doc.get('content', ''))
                    else:
                        content = str(doc)

                    if content and content.strip():
                        contents.append(content.strip())

                if not contents:
                    raise DocumentProcessingError("No valid content found in parsed documents")

                combined_content = "\n\n".join(contents)
                return ProcessedDocument(
                    content=combined_content,
                    file_name=file_name,
                    num_pages=len(contents),
                    doc_type=DocumentType.PDF.value if file_name.lower().endswith('.pdf') else DocumentType.WORD.value
                )
            finally:
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    self.logger.warning(f"Failed to delete temporary file: {str(e)}")

        except Exception as e:
            self.logger.error(f"Document processing failed: {str(e)}")
            raise DocumentProcessingError(f"Failed to process document: {str(e)}")


class StreamlitApp:
    def __init__(self):
        self.initialize_session_state()
        self.assistant = self.initialize_assistant()
        self.doc_service = DocumentProcessingService()
        self.logger = logging.getLogger(__name__)
        self.setup_page_style()

    def setup_page_style(self):
        st.set_page_config(
            page_title="Ontario Tenancy Law Assistant",
            page_icon="⚖️",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        st.markdown("""
        <style>
            .main {
                padding: 2rem;
                max-width: 1200px;
                margin: 0 auto;
            }

            .stTitle {
                color: #2C3E50;
                font-family: 'Helvetica Neue', sans-serif;
                font-weight: 700;
                padding-bottom: 1rem;
                border-bottom: 2px solid #E74C3C;
                margin-bottom: 2rem;
            }

            .stChatMessage {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 1rem;
                margin: 0.5rem 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }

            .stButton button {
                background-color: #E74C3C;
                color: white;
                border-radius: 5px;
                padding: 0.5rem 1rem;
                border: none;
                transition: all 0.3s ease;
            }

            .stButton button:hover {
                background-color: #C0392B;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }

            .uploadedFile {
                border: 2px dashed #3498DB;
                border-radius: 10px;
                padding: 1rem;
                text-align: center;
                background-color: #EBF5FB;
            }

            .css-1d391kg {
                background-color: #f8f9fa;
                padding: 2rem 1rem;
            }

            .stTab {
                background-color: white;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 1rem;
            }

            .analysis-card {
                background-color: white;
                border-radius: 10px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin: 1rem 0;
            }

            .chat-container {
                max-height: 600px;
                overflow-y: auto;
                padding: 1rem;
                background: #fff;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }

            .welcome-message {
                padding: 2rem;
                background: linear-gradient(135deg, #E8F6FF 0%, #F0F4F8 100%);
                border-radius: 10px;
                margin-bottom: 2rem;
            }

            .status-indicator {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-right: 5px;
            }

            .status-online {
                background-color: #2ECC71;
            }

            /* Progress Bar Styling */
            .stProgress > div > div {
                background-color: #E74C3C;
            }

            /* File Uploader Improvements */
            .stUploadedFile {
                border: 2px solid #E74C3C;
                border-radius: 10px;
                padding: 1rem;
            }

            /* Tooltip Styling */
            .tooltip {
                position: relative;
                display: inline-block;
            }

            .tooltip .tooltiptext {
                visibility: hidden;
                background-color: #2C3E50;
                color: #fff;
                text-align: center;
                padding: 5px;
                border-radius: 6px;
                position: absolute;
                z-index: 1;
                bottom: 125%;
                left: 50%;
                transform: translateX(-50%);
                opacity: 0;
                transition: opacity 0.3s;
            }

            .tooltip:hover .tooltiptext {
                visibility: visible;
                opacity: 1;
            }

            /* Add this to your existing CSS in setup_page_style() */

            /* Sidebar animations and styling */
            .css-1d391kg {
                background: linear-gradient(145deg, #f8f9fa, #ffffff);
                animation: gradientAnimation 15s ease infinite;
                position: relative;
                overflow: hidden;
            }

            @keyframes gradientAnimation {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            /* Animated sidebar cards */
            .sidebar-card {
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                margin: 1rem 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transform: translateY(0);
                transition: all 0.3s ease;
                border-left: 4px solid transparent;
                animation: slideIn 0.5s ease-out;
            }

            .sidebar-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 12px rgba(0,0,0,0.15);
                border-left: 4px solid #E74C3C;
            }

            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateX(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            /* Animated feature icons */
            .feature-icon {
                display: inline-block;
                margin-right: 8px;
                animation: bounce 2s infinite;
            }

            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-3px); }
            }

            /* Version badge */
            .version-badge {
                background: linear-gradient(135deg, #E74C3C, #C0392B);
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-size: 0.8em;
                position: fixed;
                bottom: 1rem;
                left: 50%;
                transform: translateX(-50%);
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.4); }
                70% { box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }
                100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
            }

            /* Floating elements animation */
            .floating {
                animation: floating 3s ease-in-out infinite;
            }

            @keyframes floating {
                0% { transform: translateY(0px); }
                50% { transform: translateY(-10px); }
                100% { transform: translateY(0px); }
            }
        </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def initialize_session_state():
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "current_tab" not in st.session_state:
            st.session_state.current_tab = "Chat Assistant"
        if "processed_documents" not in st.session_state:
            st.session_state.processed_documents = []

    @staticmethod
    def initialize_assistant():
        api_key = os.getenv("GROQ_API_KEY")
        llm = create_llm(LLMProvider.GROQ, api_key)
        return LegalAssistant(llm)

    async def process_uploaded_file(self, uploaded_file) -> Optional[str]:
        try:
            if not uploaded_file:
                return None

            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            processed_doc = await self.doc_service.process_document(
                file_content=file_content,
                file_name=uploaded_file.name
            )
            st.session_state.processed_documents.append(processed_doc)
            return processed_doc.content

        except DocumentProcessingError as e:
            st.error(f"📄 Failed to process document: {str(e)}")
            return None
        except Exception as e:
            st.error("❌ An unexpected error occurred")
            return None

    def render_chat_assistant(self):
        st.title("⚖️ Ontario Tenancy Law Assistant")

        if not st.session_state.messages:
            st.markdown("""
            <div class="welcome-message">
                <h3>👋 Welcome to the Ontario Tenancy Law Assistant!</h3>
                <p>I'm here to help you understand Ontario's tenancy laws and your rights.</p>
                <div style="margin: 1rem 0;">
                    <span class="status-indicator status-online"></span>
                    <span style="color: #2ECC71;">Assistant is ready to help</span>
                </div>
                <div style="background: white; padding: 1rem; border-radius: 5px; margin-top: 1rem;">
                    <p><strong>Popular topics:</strong></p>
                    <ul style="list-style-type: none; padding-left: 0;">
                        <li>🏠 Tenant rights and responsibilities</li>
                        <li>📝 Lease agreements</li>
                        <li>💰 Rent increases and deposits</li>
                        <li>🔧 Maintenance and repairs</li>
                        <li>⚖️ Dispute resolution</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

        chat_container = st.container()

        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"], avatar="⚖️" if message["role"] == "assistant" else "👤"):
                    st.markdown(message["content"])

        prompt = st.chat_input("Ask about Ontario tenancy law...", key="chat_input")
        if prompt:
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant", avatar="⚖️"):
                with st.spinner("💭 Thinking..."):
                    try:
                        chat_history = "\n".join(
                            [f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages])
                        response = self.assistant.get_response(prompt, chat_history)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

    def render_contract_analyzer(self):
        st.title("📄 Rental Contract Analyzer")

        # Introduction card with better spacing and layout
        st.markdown("""
        <div class="analysis-card" style="margin-bottom: 2rem;">
            <h3 style="color: #2C3E50; margin-bottom: 1rem;">📊 Contract Analysis Tool</h3>
            <p style="font-size: 1.1em; margin-bottom: 1rem;">Upload your rental agreement for a comprehensive analysis:</p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                <div>
                    <h4 style="color: #34495E;">Key Features:</h4>
                    <ul style="list-style: none; padding-left: 0;">
                        <li style="margin: 0.5rem 0;"><span style="color: #27AE60;">✓</span> Legal compliance check</li>
                        <li style="margin: 0.5rem 0;"><span style="color: #27AE60;">✓</span> Clause analysis</li>
                    </ul>
                </div>
                <div>
                    <h4 style="color: #34495E;">Benefits:</h4>
                    <ul style="list-style: none; padding-left: 0;">
                        <li style="margin: 0.5rem 0;"><span style="color: #27AE60;">✓</span> Rights review</li>
                        <li style="margin: 0.5rem 0;"><span style="color: #27AE60;">✓</span> Expert recommendations</li>
                    </ul>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Input method selection with better visual hierarchy
        input_method = st.radio(
            "Select Input Method:",
            ["Upload Document", "Paste Text"],
            format_func=lambda x: "📎 " + x if x == "Upload Document" else "📝 " + x,
            horizontal=True,
            key="input_method"
        )

        contract_text = None

        # Create columns for better layout
        col1, col2 = st.columns([2, 1])

        with col1:
            if input_method == "Upload Document":
                uploaded_file = st.file_uploader(
                    "Drop your rental agreement here",
                    type=['txt', 'pdf', 'docx'],
                    help="Supported formats: PDF, Word, and Text files",
                    key="file_uploader"
                )

                if uploaded_file:
                    st.markdown(f"""
                    <div class="uploadedFile" style="margin: 1rem 0;">
                        <div style="display: flex; align-items: center; justify-content: center; padding: 1rem;">
                            <span style="font-size: 2em; margin-right: 10px;">📄</span>
                            <span style="font-size: 1.1em;">{uploaded_file.name}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.spinner("📑 Processing document..."):
                        contract_text = asyncio.run(self.process_uploaded_file(uploaded_file))
            else:
                contract_text = st.text_area(
                    "Paste your rental agreement",
                    height=300,
                    placeholder="Copy and paste your rental agreement here...",
                    help="Your text will be analyzed for compliance with Ontario tenancy laws",
                    key="text_input"
                )

        with col2:
            st.markdown("<br>" * 3, unsafe_allow_html=True)  # Add some spacing
            if contract_text:
                if st.button("🔍 Analyze Contract", use_container_width=True, key="analyze_button"):
                    self._analyze_contract_text(contract_text)

    def _analyze_contract_text(self, contract_text: str):
        with st.spinner("🔍 Analyzing your contract..."):
            try:
                analysis = self.assistant.analyze_contract(contract_text)

                # Clear previous content
                st.empty()

                # Success message with animation
                st.success("✅ Analysis Complete!")

                # Analysis report with improved layout
                st.markdown("""
                <style>
                    .report-container {
                        background: white;
                        border-radius: 10px;
                        padding: 2rem;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        margin: 2rem 0;
                    }
                    .report-section {
                        margin-bottom: 2rem;
                        padding: 1.5rem;
                        background: #f8f9fa;
                        border-radius: 8px;
                    }
                    .report-header {
                        color: #2C3E50;
                        border-bottom: 2px solid #E74C3C;
                        padding-bottom: 1rem;
                        margin-bottom: 2rem;
                    }
                </style>
                <div class="report-container">
                    <h2 class="report-header">📊 Contract Analysis Report</h2>
                """, unsafe_allow_html=True)

                # Split analysis into sections and display with better formatting
                st.markdown(f"""
                <div class="report-section">
                    <h3 style="color: #34495E;">Key Findings</h3>
                    {analysis}
                </div>
                """, unsafe_allow_html=True)

                # Action buttons in a better layout
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.download_button(
                        label="📥 Download Full Report",
                        data=analysis,
                        file_name="contract_analysis_report.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"""
                ❌ Analysis failed

                Error details: {str(e)}

                Please try again or contact support if the problem persists.
                """)

    def render_sidebar(self):
        with st.sidebar:
            st.markdown("""
            <div class='floating' style='text-align: center; margin-bottom: 2rem;'>
                <h1 style='color: #E74C3C; margin-bottom: 0;'>⚖️</h1>
                <h3 style='color: #2C3E50; margin-top: 0;'>Ontario Tenancy Law Assistant</h3>
            </div>

            <div class="sidebar-card">
                <h4>🎯 Quick Actions</h4>
                """, unsafe_allow_html=True)

            if st.session_state.messages:
                if st.button("🗑️ Clear Chat"):
                    if st.button("⚠️ Confirm Clear"):
                        st.session_state.messages = []
                        st.rerun()

            st.markdown("""
            <div class="sidebar-card">
                <h4>📋 Features</h4>
                <p><span class="feature-icon">💬</span> Interactive legal guidance</p>
                <p><span class="feature-icon">📝</span> Contract analysis</p>
                <p><span class="feature-icon">✅</span> Compliance checks</p>
                <p><span class="feature-icon">🔍</span> Plain language explanations</p>
            </div>

            <div class="sidebar-card">
                <h4>⚠️ Disclaimer</h4>
                <p style='font-size: 0.8em; color: #666;'>
                    This tool provides information based on Ontario tenancy law but does not constitute
                    legal advice. For specific legal situations, please consult a qualified legal professional.
                </p>
            </div>

            <div class="version-badge">
                v1.0.0
            </div>
            """, unsafe_allow_html=True)

    def main(self):
        tab1, tab2 = st.tabs(["💬 Chat Assistant", "📄 Contract Analyzer"])

        with tab1:
            self.render_chat_assistant()

        with tab2:
            self.render_contract_analyzer()

        self.render_sidebar()


if __name__ == "__main__":
    app = StreamlitApp()
    app.main()
