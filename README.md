# OneDrive AI Assistant with Gemini Integration

A comprehensive web application that allows you to interact with your OneDrive files using Google's Gemini AI. This application provides file selection, editing, uploading, and AI-powered analysis capabilities.

## 🚀 Features

### Core Functionality
- **OneDrive Integration**: Full access to your OneDrive files and folders
- **AI-Powered Analysis**: Use Google Gemini AI to analyze and answer questions about your files
- **File Selection**: Multi-select files and folders for targeted AI analysis
- **Real-time Chat**: Interactive chat interface with AI assistant

### File Operations
- ✅ **View Files**: Browse your OneDrive directory structure
- ✅ **Select Files**: Multi-select files for AI analysis
- ✅ **File Search**: AI-powered search through file contents

### AI Capabilities
- **Content Analysis**: Analyze PDFs, Word documents, Excel files, and more
- **Data Extraction**: Extract insights from spreadsheets and CSV files
- **Document Summarization**: Get summaries of long documents
- **Question Answering**: Ask specific questions about your files
- **Contextual Responses**: AI responses based on selected files only

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Microsoft Azure AD application
- Google Gemini API key
- OneDrive account

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd oneDrive
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Azure AD Configuration
   AZURE_CLIENT_ID=your_azure_client_id
   AZURE_CLIENT_SECRET=your_azure_client_secret
   AZURE_TENANT_ID=your_azure_tenant_id
   AZURE_REDIRECT_URI=http://localhost:5000/auth/callback

   # Gemini AI Configuration
   GEMINI_API_KEY=your_gemini_api_key

   # Flask Configuration
   FLASK_SECRET_KEY=your_secret_key
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

5. **Access the application**
   Open your browser and go to `http://localhost:5000`

## 🔧 Configuration

### Azure AD Setup
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to "Azure Active Directory" > "App registrations"
3. Click "New registration"
4. Configure the application:
   - Name: "OneDrive AI Assistant"
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: `http://localhost:5000/auth/callback`
5. Note down the Application (client) ID and Directory (tenant) ID
6. Go to "Certificates & secrets" and create a new client secret
7. Go to "API permissions" and add:
   - Microsoft Graph > Files.Read
   - Microsoft Graph > Files.Read.All
   - Microsoft Graph > User.Read
   - Microsoft Graph > Sites.Read.All

### Gemini API Setup
1. Go to [Google AI Studio](https://aistudio.google.com)
2. Create a new API key
3. Add the key to your `.env` file

## 📱 Usage

### Getting Started
1. **Login**: Click "Sign in with Microsoft" to authenticate
2. **Browse Files**: Your OneDrive files will appear in the left sidebar
3. **Select Files**: Click on files to select them for AI analysis
4. **Ask Questions**: Type questions in the chat interface

### File Operations

#### Selecting Files
- **Single Selection**: Click on a file to select it
- **Multi-Selection**: Use checkboxes to select multiple files
- **Select All**: Use the "Select All" button to select all visible files
- **Clear Selection**: Use the "Clear" button to deselect all files


#### AI Analysis
- Select one or more files
- Ask questions like:
  - "What is this document about?"
  - "Summarize the key points"
  - "Find all mentions of 'project management'"
  - "What data is in this spreadsheet?"

## 🎨 Interface Overview

### Sidebar
- **User Info**: Shows your name and connection status
- **Selection Panel**: Displays selected files count and list
- **File Browser**: Hierarchical view of your OneDrive files
- **File Actions**: Buttons for select all, clear, view mode, and upload

### Main Content
- **Chat Header**: Shows AI assistant title and description
- **Chat Messages**: Conversation history with the AI
- **Input Area**: Text input with send button and suggestions
- **Suggestions**: Quick-start question suggestions


## 🔒 Security

- **OAuth 2.0**: Secure Microsoft authentication
- **Token Management**: Automatic token refresh
- **Session Security**: Secure session management
- **API Security**: All API calls use proper authentication

## 📊 Supported File Types

### Text Files
- `.txt` - Plain text files
- `.md` - Markdown files
- `.json` - JSON data files
- `.xml` - XML files

### Documents
- `.pdf` - PDF documents (text extraction)
- `.docx` - Microsoft Word documents
- `.doc` - Legacy Word documents

### Spreadsheets
- `.xlsx` - Microsoft Excel files
- `.xls` - Legacy Excel files
- `.csv` - Comma-separated values

### Presentations
- `.pptx` - Microsoft PowerPoint presentations
- `.ppt` - Legacy PowerPoint presentations

### Images
- `.jpg`, `.jpeg` - JPEG images
- `.png` - PNG images
- `.gif` - GIF images

## 🚨 Troubleshooting

### Common Issues

#### Authentication Problems
- **Issue**: "Authentication failed"
- **Solution**: Check your Azure AD configuration and ensure redirect URI matches exactly

#### File Access Issues
- **Issue**: "Cannot access OneDrive"
- **Solution**: Verify API permissions in Azure AD and ensure Files.Read scope is granted

#### Gemini API Issues
- **Issue**: "Gemini AI is not available"
- **Solution**: Check your Gemini API key and ensure it's valid

#### File Upload Issues
- **Issue**: "Upload failed"
- **Solution**: Check file size limits and ensure you have write permissions

### Debug Mode
Access `/debug` endpoint to see connection status and diagnostic information.

## 🔄 API Endpoints

### Authentication
- `GET /` - Home page
- `GET /login` - Microsoft OAuth login
- `GET /auth/callback` - OAuth callback
- `GET /logout` - Logout

### File Operations
- `GET /api/directory` - Get directory structure

### AI Chat
- `POST /api/chat` - Send message to AI with selected files

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Microsoft Graph API for OneDrive integration
- Google Gemini AI for natural language processing
- Flask framework for the web application
- Font Awesome for icons

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation

---

**Note**: This application requires proper Azure AD and Gemini API setup. Make sure to follow the configuration steps carefully for the application to work correctly.
