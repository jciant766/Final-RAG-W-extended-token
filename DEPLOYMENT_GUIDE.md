# Streamlit Community Cloud Deployment Guide

## Prerequisites
1. GitHub account
2. Streamlit Community Cloud account (free at share.streamlit.io)

## Steps to Deploy

### 1. Prepare Your Repository
- All files are ready in your project
- Make sure to exclude sensitive files by creating `.gitignore`:

```
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env
.env
chroma_db/
.venv/
venv/
```

### 2. Push to GitHub
1. Initialize git repository: `git init`
2. Add all files: `git add .`
3. Commit: `git commit -m "Initial RAG app with AI overview"`
4. Create GitHub repository
5. Add remote: `git remote add origin <your-repo-url>`
6. Push: `git push -u origin main`

### 3. Deploy on Streamlit Community Cloud
1. Go to https://share.streamlit.io
2. Click "Deploy an app"
3. Connect your GitHub account
4. Select your repository
5. Set main file path: `main.py`
6. Click "Deploy!"

### 4. Configure Secrets
1. In your deployed app, go to Settings → Secrets
2. Add the following secret:
```
OPENAI_API_KEY = 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
```

### 5. First Run
- The first deployment will take 2-3 minutes as it processes the Malta Commercial Code document
- You'll see debug logs showing document processing and vector database creation
- Once complete, you can search and get AI-powered overviews

## Features
- ✅ AI-powered legal research with overviews
- ✅ Article citations with page numbers
- ✅ Semantic search through Malta Commercial Code
- ✅ Confidence scoring for AI responses
- ✅ Token usage tracking

## Troubleshooting
- If deployment fails, check the logs in Streamlit Community Cloud
- Ensure all dependencies are in `Requirements.txt`
- Verify the API key is correctly set in secrets
- The app will automatically rebuild the vector database on first run

