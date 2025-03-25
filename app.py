import streamlit as st
import openai
import os
from PIL import Image
import io
import docx
import PyPDF2
import pandas as pd
import tempfile
import base64

# Set OpenAI API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY is not set in .streamlit/secrets.toml file.")

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Set the model to gpt-4o-mini only
st.session_state.openai_model = "gpt-4o-mini"

# Page configuration with ChatGPT-like styling
st.set_page_config(
    page_title="NarderioGPT",
    page_icon="💬",
    layout="wide"
)

# Custom CSS for ChatGPT-like interface
st.markdown("""
<style>
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 800px;
    margin: 0 auto;
}

.stChatMessage {
    background-color: #f7f7f8;
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 10px;
    color: #202123;
}

.stChatMessage[data-testid*="user"] {
    background-color: #f0f2f6;
    color: #202123;
    border: 1px solid #d9d9e3;
}

.stChatMessage[data-testid*="assistant"] {
    background-color: #ffffff;
    border: 1px solid #e5e5e5;
    color: #202123;
}

/* Ensure text is visible in chat messages */
.stChatMessage p, .stChatMessage div {
    color: #202123 !important;
    font-size: 16px;
    line-height: 1.5;
}

/* Style for code blocks in chat messages */
.stChatMessage pre {
    background-color: #f6f8fa !important;
    border-radius: 6px;
    padding: 16px;
    overflow: auto;
    font-family: monospace;
}

.stChatMessage code {
    background-color: #f6f8fa !important;
    color: #24292e !important;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: monospace;
    font-size: 85%;
}

/* Style for the avatar container to ensure it's visible */
.stChatMessageAvatar {
    background-color: transparent !important;
}

.stChatInputContainer {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: 80%;
    max-width: 800px;
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 0 10px rgba(0,0,0,0.1);
    padding: 10px;
}

.stButton>button {
    background-color: #10a37f;
    color: white;
    border-radius: 4px;
    border: none;
    padding: 0.5rem 1rem;
}

.stButton>button:hover {
    background-color: #0d8c6d;
}

.sidebar .sidebar-content {
    background-color: #202123;
    color: white;
}

.sidebar-title {
    color: white;
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 20px;
}

.sidebar-subtitle {
    color: #c5c5d2;
    font-size: 16px;
    margin-top: 30px;
    margin-bottom: 10px;
}

.stTitle {
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 2rem;
    color: #202123;
}
</style>
""", unsafe_allow_html=True)

# Main title
st.title("NarderioGPT")

# Sidebar for file uploads and settings
with st.sidebar:
    st.markdown('<div class="sidebar-title">NarderioGPT</div>', unsafe_allow_html=True)
    
    # File upload section
    st.markdown('<div class="sidebar-subtitle">Upload Files</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Choose a file", 
        type=["txt", "pdf", "docx", "csv", "xlsx"]
    )
    
    # Image upload section
    st.markdown('<div class="sidebar-subtitle">Upload Images</div>', unsafe_allow_html=True)
    uploaded_image = st.file_uploader(
        "Choose an image", 
        type=["jpg", "jpeg", "png"]
    )
    
    # Clear chat button
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Function to extract text from different file types
def extract_text_from_file(file):
    try:
        file_extension = file.name.split('.')[-1].lower()
        
        if file_extension == 'txt':
            try:
                return file.getvalue().decode('utf-8')
            except UnicodeDecodeError:
                return file.getvalue().decode('latin-1')
        
        elif file_extension == 'pdf':
            try:
                # Save uploaded file to a temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(file.getvalue())
                    temp_path = temp_file.name
                
                # Extract text from PDF
                text = ""
                try:
                    with open(temp_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        total_pages = len(pdf_reader.pages)
                        
                        if total_pages == 0:
                            return "The PDF file appears to be empty."
                            
                        for page_num in range(total_pages):
                            try:
                                page = pdf_reader.pages[page_num]
                                page_text = page.extract_text()
                                
                                if page_text and page_text.strip():
                                    text += f"--- Page {page_num+1} ---\n{page_text}\n\n"
                                else:
                                    text += f"[Page {page_num+1} contains no extractable text]\n"
                            except Exception as page_error:
                                text += f"[Error extracting page {page_num+1}: {str(page_error)}]\n"
                finally:
                    # Always clean up the temporary file
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass  # Ignore errors during cleanup
                
                # Check if any text was successfully extracted
                if text.strip():
                    return text
                else:
                    return "The PDF file does not contain extractable text. It might be scanned or protected."
            except Exception as e:
                return f"Error processing PDF file: {str(e)}"
        
        elif file_extension == 'docx':
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
                    temp_file.write(file.getvalue())
                    temp_path = temp_file.name
                
                try:
                    doc = docx.Document(temp_path)
                    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                    
                    # Check if any text was successfully extracted
                    if text.strip():
                        return text
                    else:
                        return "The Word document does not contain extractable text."
                finally:
                    # Always clean up the temporary file
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass  # Ignore errors during cleanup
            except Exception as e:
                return f"Error processing DOCX file: {str(e)}"
        
        elif file_extension in ['csv', 'xlsx']:
            try:
                if file_extension == 'csv':
                    df = pd.read_csv(file)
                else:  # xlsx
                    df = pd.read_excel(file)
                
                if df.empty:
                    return "The file is empty or does not contain valid data."
                
                # Format the dataframe as a string with a reasonable max_rows
                # to avoid overwhelming the model with very large datasets
                with pd.option_context('display.max_rows', 100, 'display.max_columns', 20):
                    return df.to_string()
            except Exception as e:
                return f"Error processing {file_extension.upper()} file: {str(e)}"
        
        return f"Unsupported file type: {file_extension}"
    except Exception as e:
        return f"General error processing file: {str(e)}"

# Create a container for chat messages with scrolling
chat_container = st.container()

# Display chat messages in the container
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user" and "image_data" in message:
                # Display image if it exists in the message
                st.image(message["image_data"], caption="Uploaded Image")
            st.markdown(message["content"])

# Process user input
if prompt := st.chat_input("Send a message..."):
    # Process uploaded file if any
    file_content = None
    if uploaded_file is not None:
        file_content = extract_text_from_file(uploaded_file)
        
        # Check if file content was successfully extracted
        if file_content and not (file_content.startswith("Error") or file_content.startswith("The PDF file does not") or file_content.startswith("Unsupported")):
            # Show preview with ellipsis only if content is long enough
            preview_text = file_content[:500]
            if len(file_content) > 500:
                preview_text += "..."
            st.sidebar.text_area("File Content Preview", preview_text, height=200)
        else:
            # Show error message in sidebar
            st.sidebar.error(f"Problem with file: {file_content}")
            # Still keep the error message as file_content to inform the AI
    
    # Process uploaded image if any
    image_data = None
    if uploaded_image is not None:
        image = Image.open(uploaded_image)
        image_data = image
        
        # Display the image in the user message
        user_message = {"role": "user", "content": prompt, "image_data": image_data}
        st.session_state.messages.append(user_message)
        
        # Display the message and image
        with st.chat_message("user"):
            st.image(image_data, caption="Uploaded Image")
            st.markdown(prompt)
        
        # Prepare image for API
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_bytes = buffered.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create message content with image for vision model
        message_content = [
            {"type": "text", "text": prompt}
        ]
        
        # Add image to message content if needed
        message_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"},
            }
        )
    else:
        # Text-only message
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)
        
        # Display the message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Prepare message content for API
        message_content = prompt
    
    # Add file content to the prompt if available
    if file_content:
        if isinstance(message_content, list):
            # For vision model with image
            message_content[0]["text"] += f"\n\nFile Content: {file_content}"
        else:
            # For text-only models
            message_content += f"\n\nFile Content: {file_content}"
    
    # Display assistant thinking indicator
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("<div class='typing-indicator'>Thinking...</div>", unsafe_allow_html=True)
    
    try:
        # Call OpenAI API based on content type - using streaming for both text and image
        full_response = ""
        
        # Prepare messages based on content type
        if image_data is not None:
            # For images with vision model
            messages_for_api = [
                {"role": m["role"], "content": m["content"]} 
                for m in st.session_state.messages[:-1]
            ] + [{"role": "user", "content": message_content}]
        else:
            # For text-only interactions
            # Get all previous messages
            messages_for_api = [
                {"role": m["role"], "content": m["content"]} 
                for m in st.session_state.messages[:-1]
            ]
            # Add the current message with the updated content
            messages_for_api.append({"role": "user", "content": message_content})
        
        # Use streaming for all responses
        for response in openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages_for_api,
            max_tokens=4096,
            stream=True,
        ):
            # Extract the content from the chunk
            content_delta = response.choices[0].delta.content or ""
            full_response += content_delta
            
            # Update the message placeholder with the accumulated response
            message_placeholder.markdown(full_response + "▌")
        
        # Final update without the cursor
        message_placeholder.markdown(full_response)
        
        # Add the complete response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    except Exception as e:
        error_message = f"Error: {str(e)}"
        message_placeholder.markdown(error_message)
        st.error(error_message)

# Display instructions in the sidebar footer
with st.sidebar:
    st.divider()
    st.markdown('<div class="sidebar-subtitle">Instructions</div>', unsafe_allow_html=True)
    st.markdown("""
    1. Optionally upload files or images
    2. Type your message in the chat input
    3. Clear the chat using the button above
    """)
    
    st.divider()
    st.caption("© 2025 NarderioGPT")