# 🔒 Security Guide for AI Designer

## Overview

This guide explains how to securely configure and use the AI Designer system without exposing sensitive information like API keys in your code or version control.

## 🔑 API Key Security

### **IMPORTANT: Never commit API keys to version control!**

Your Google API key (`AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc`) should **never** be hardcoded in your source code or committed to Git.

### **Secure Configuration Setup**

1. **Environment File (.env)**
   ```bash
   # Create .env file in project root
   echo "GOOGLE_API_KEY=AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc" > .env
   ```

2. **Verify .gitignore**
   ```bash
   # Make sure .env is in .gitignore
   grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
   ```

3. **Use Secure Configuration in Code**
   ```python
   from ai_designer.config import get_api_key

   # Secure API key loading
   api_key = get_api_key()  # Loaded from .env file
   ```

## 📁 File Structure

```
project/
├── .env                    # ✅ Contains API key (NEVER commit)
├── .env.example           # ✅ Template file (safe to commit)
├── .gitignore            # ✅ Contains .env (NEVER commit .env)
└── src/
    └── ai_designer/
        └── config/
            ├── __init__.py
            └── secure_config.py  # ✅ Secure config loader
```

## 🛡️ Security Features Implemented

### **1. Secure Configuration Loading**
- API keys loaded from `.env` file
- Validation of API key format
- Error handling for missing configuration
- No sensitive data in source code

### **2. Git Security**
- `.env` file excluded via `.gitignore`
- `.env.example` template provided
- No hardcoded secrets in any committed files

### **3. Runtime Security**
- API keys masked in logs and console output
- Secure string representations
- Configuration validation

## 🚀 Quick Setup

### **For New Users**

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit with your API key:**
   ```bash
   nano .env
   # Set: GOOGLE_API_KEY=your_actual_api_key_here
   ```

3. **Verify security:**
   ```bash
   # Check that .env is ignored
   git status
   # .env should NOT appear in untracked files
   ```

### **For Existing Users**

If you already have the API key in your environment:

```bash
# Create .env file from existing environment
echo "GOOGLE_API_KEY=$GOOGLE_API_KEY" > .env
```

## 🔍 Security Verification

### **Check Git Status**
```bash
git status
# .env should not appear in untracked files
```

### **Verify Configuration Loading**
```python
from ai_designer.config import get_config
config = get_config()
print(config)  # API key should be masked: AIza...sSEc
```

### **Test API Key Access**
```python
from ai_designer.config import get_api_key
try:
    api_key = get_api_key()
    print("✅ API key loaded successfully")
except Exception as e:
    print(f"❌ API key not found: {e}")
```

## 🚨 Common Security Mistakes to Avoid

### **❌ DON'T DO THIS:**
```python
# NEVER hardcode API keys
api_key = "AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc"  # ❌ BAD!

# NEVER commit .env files
git add .env  # ❌ BAD!
```

### **✅ DO THIS INSTEAD:**
```python
# Use secure configuration
from ai_designer.config import get_api_key
api_key = get_api_key()  # ✅ GOOD!

# Keep .env files local
echo ".env" >> .gitignore  # ✅ GOOD!
```

## 🌍 Deployment Security

### **Development Environment**
- Use `.env` file for local development
- Never commit `.env` to version control
- Use `.env.example` as template

### **Production Environment**
- Set environment variables directly on server
- Use container secrets (Docker, Kubernetes)
- Use cloud secret management services

### **CI/CD Pipelines**
- Store API keys as encrypted secrets
- Use environment-specific configurations
- Never log sensitive values

## 🔧 Configuration Options

### **Required Settings**
```bash
# .env file
GOOGLE_API_KEY=your_google_api_key_here
```

### **Optional Settings**
```bash
# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Logging
DEBUG=false
LOG_LEVEL=INFO

# Session management
SESSION_TIMEOUT=3600
MAX_CONCURRENT_SESSIONS=10
```

## 🆘 Troubleshooting

### **"API key not found" Error**
1. Check `.env` file exists in project root
2. Verify `GOOGLE_API_KEY` is set in `.env`
3. Ensure no extra spaces or quotes in `.env`

### **"Invalid API key format" Warning**
1. Verify API key starts with `AIza`
2. Check API key length (should be 39+ characters)
3. Get new API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### **Git Accidentally Tracked .env**
```bash
# Remove from git but keep local file
git rm --cached .env
git commit -m "Remove .env from tracking"

# Add to .gitignore if not already there
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to .gitignore"
```

## 📚 Additional Resources

- [Google AI Studio API Keys](https://makersuite.google.com/app/apikey)
- [Environment Variables Best Practices](https://12factor.net/config)
- [Git Security Best Practices](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure)

---

## ✅ Security Checklist

- [ ] API key stored in `.env` file
- [ ] `.env` file in `.gitignore`
- [ ] No hardcoded secrets in source code
- [ ] Using secure config module
- [ ] Verified git status (no .env tracking)
- [ ] API key format validated
- [ ] Configuration loading tested

**Remember: Security is not optional! Always protect your API keys and sensitive data.** 🔒
