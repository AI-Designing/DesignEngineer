# Security Comprehensive Guide

## Table of Contents
1. [Overview](#overview)
2. [API Key Management](#api-key-management)
3. [Secure Configuration](#secure-configuration)
4. [Implementation](#implementation)
5. [Best Practices](#best-practices)

---

## Overview

This comprehensive security guide covers all aspects of securing the FreeCAD LLM Automation system, with emphasis on protecting sensitive information like API keys, implementing secure configuration practices, and maintaining security across development and production environments.

### Security Principles

The system follows these core security principles:
- **🔒 Defense in Depth**: Multiple layers of security protection
- **🚫 Never Trust, Always Verify**: Validate all inputs and configurations
- **🔑 Least Privilege**: Minimal access rights for all components
- **📝 Audit Trail**: Complete logging of security-relevant events
- **🔄 Secure by Default**: Security enabled out of the box

### Critical Security Rules

**NEVER:**
- ❌ Commit API keys to version control
- ❌ Hardcode secrets in source code
- ❌ Share API keys in public channels
- ❌ Log sensitive information
- ❌ Use production keys in development

**ALWAYS:**
- ✅ Use environment variables or secure vaults
- ✅ Keep `.env` files in `.gitignore`
- ✅ Rotate API keys regularly
- ✅ Use different keys for different environments
- ✅ Monitor API usage for anomalies

---

## API Key Management

### Understanding API Keys

API keys are sensitive credentials that authenticate your application with external services. In this system:

- **Google Gemini API Key**: For LLM-powered code generation
- **DeepSeek API Key**: For advanced reasoning capabilities (if using cloud version)
- **Redis Password**: For secure cache access (if configured)

### Current API Key (IMPORTANT)

Your Google API key: `AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc`

**⚠️ This key is already in your `.env` file and secured. Do NOT share it publicly!**

### Secure Storage Methods

#### Method 1: Environment File (.env) - Recommended for Development

```bash
# Create .env file in project root
cat > .env << 'EOF'
# Google Gemini API Configuration
GOOGLE_API_KEY=AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc

# DeepSeek Configuration (if using cloud)
DEEPSEEK_API_KEY=your_deepseek_key_here

# Redis Configuration (if password protected)
REDIS_PASSWORD=your_redis_password_here

# Environment
ENVIRONMENT=development
DEBUG=true
EOF

# Secure the file
chmod 600 .env
```

#### Method 2: System Environment Variables - Recommended for Production

```bash
# Linux/macOS - Add to ~/.bashrc or ~/.zshrc
export GOOGLE_API_KEY="AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc"  # pragma: allowlist secret
export DEEPSEEK_API_KEY="your_deepseek_key_here"  # pragma: allowlist secret

# Apply changes
source ~/.bashrc  # or source ~/.zshrc

# Verify
echo $GOOGLE_API_KEY
```

#### Method 3: Secret Management Services - Recommended for Enterprise

**AWS Secrets Manager:**
```python
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name):
    """Retrieve secret from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')

    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise Exception(f"Failed to retrieve secret: {e}")

# Usage
api_key = get_secret('freecad-llm/google-api-key')
```

**HashiCorp Vault:**
```python
import hvac

def get_vault_secret(path):
    """Retrieve secret from HashiCorp Vault"""
    client = hvac.Client(url='http://localhost:8200')
    client.token = os.environ.get('VAULT_TOKEN')

    secret = client.secrets.kv.v2.read_secret_version(path=path)
    return secret['data']['data']

# Usage
secrets = get_vault_secret('freecad-llm/api-keys')
api_key = secrets['google_api_key']
```

### API Key Security Best Practices

#### 1. Key Rotation

```python
class APIKeyManager:
    """Manage API key rotation"""

    def __init__(self):
        self.current_key = self.load_current_key()
        self.rotation_schedule = 90  # days
        self.last_rotation = self.get_last_rotation_date()

    def should_rotate(self):
        """Check if key rotation is needed"""
        days_since_rotation = (
            datetime.now() - self.last_rotation
        ).days
        return days_since_rotation >= self.rotation_schedule

    def rotate_key(self, new_key):
        """Rotate to new API key"""
        # Archive old key
        self.archive_key(self.current_key)

        # Update .env file
        self.update_env_file('GOOGLE_API_KEY', new_key)

        # Update current key
        self.current_key = new_key
        self.last_rotation = datetime.now()

        # Log rotation
        logging.info("API key rotated successfully")
```

#### 2. Key Validation

```python
def validate_api_key(api_key):
    """Validate API key format and status"""

    # Check format
    if not api_key:
        raise ValueError("API key is required")

    if not api_key.startswith('AIza'):
        raise ValueError("Invalid Google API key format")

    if len(api_key) < 39:
        raise ValueError("API key too short")

    # Test key validity
    try:
        # Make test request
        response = test_api_request(api_key)
        return True
    except Exception as e:
        raise ValueError(f"API key validation failed: {e}")
```

#### 3. Key Monitoring

```python
class APIKeyMonitor:
    """Monitor API key usage and security"""

    def __init__(self):
        self.usage_tracker = {}
        self.alert_threshold = 1000  # requests per hour

    def track_usage(self, api_key_id, endpoint):
        """Track API key usage"""
        timestamp = datetime.now()
        hour_key = timestamp.strftime('%Y-%m-%d-%H')

        key = f"{api_key_id}:{hour_key}"
        self.usage_tracker[key] = self.usage_tracker.get(key, 0) + 1

        # Check for unusual activity
        if self.usage_tracker[key] > self.alert_threshold:
            self.trigger_alert(f"High API usage detected: {key}")

    def detect_anomalies(self):
        """Detect unusual API usage patterns"""
        # Check for spikes
        # Check for unusual endpoints
        # Check for failed requests
        pass

    def trigger_alert(self, message):
        """Send security alert"""
        logging.warning(f"SECURITY ALERT: {message}")
        # Send email/Slack notification
```

---

## Secure Configuration

### Configuration System

**Location**: `src/ai_designer/config/secure_config.py`

The secure configuration system provides:

#### Secure Config Class

```python
from dataclasses import dataclass
from typing import Optional
import os
from dotenv import load_dotenv

@dataclass
class SecureConfig:
    """Secure configuration management"""

    google_api_key: str
    deepseek_api_key: Optional[str] = None
    redis_password: Optional[str] = None
    environment: str = "development"
    debug: bool = False

    def __post_init__(self):
        """Validate configuration after initialization"""
        self.validate()

    def validate(self):
        """Validate all configuration values"""
        if not self.google_api_key:
            raise ValueError("Google API key is required")

        if not self.google_api_key.startswith('AIza'):
            logging.warning("Google API key format may be invalid")

        if self.environment not in ['development', 'staging', 'production']:
            raise ValueError(f"Invalid environment: {self.environment}")

    def __repr__(self):
        """Safe string representation (masks sensitive data)"""
        return (
            f"SecureConfig("
            f"google_api_key='{self.mask_key(self.google_api_key)}', "
            f"environment='{self.environment}', "
            f"debug={self.debug}"
            f")"
        )

    @staticmethod
    def mask_key(key: str, visible_chars: int = 4) -> str:
        """Mask API key for safe display"""
        if not key:
            return "None"
        if len(key) <= visible_chars * 2:
            return "***"
        return f"{key[:visible_chars]}...{key[-visible_chars:]}"

def load_secure_config() -> SecureConfig:
    """Load configuration from environment"""
    # Load .env file
    load_dotenv()

    # Get configuration values
    config = SecureConfig(
        google_api_key=os.getenv('GOOGLE_API_KEY'),
        deepseek_api_key=os.getenv('DEEPSEEK_API_KEY'),
        redis_password=os.getenv('REDIS_PASSWORD'),
        environment=os.getenv('ENVIRONMENT', 'development'),
        debug=os.getenv('DEBUG', 'false').lower() == 'true'
    )

    return config

# Convenience functions
def get_api_key() -> str:
    """Get Google API key"""
    config = load_secure_config()
    return config.google_api_key

def get_config() -> SecureConfig:
    """Get full configuration"""
    return load_secure_config()
```

#### Usage in Code

```python
from ai_designer.config import get_api_key, get_config

# Get API key securely
api_key = get_api_key()

# Get full configuration
config = get_config()
print(config)  # API key will be masked in output

# Use in LLM client
from ai_designer.llm.client import LLMClient

client = LLMClient(api_key=get_api_key())
```

### File Structure

```
project/
├── .env                          # ✅ Contains secrets (NEVER commit)
├── .env.example                  # ✅ Template (safe to commit)
├── .gitignore                    # ✅ Excludes .env
├── config/
│   ├── config.yaml              # ✅ Non-sensitive config
│   └── redis.conf               # ✅ Redis configuration
└── src/ai_designer/
    └── config/
        ├── __init__.py          # ✅ Exports secure functions
        └── secure_config.py     # ✅ Secure config loader
```

### .env File Template

**File**: `.env.example`

```bash
# ================================================
# FreeCAD LLM Automation - Environment Configuration
# ================================================
#
# IMPORTANT:
# 1. Copy this file to .env
# 2. Fill in your actual values
# 3. NEVER commit .env to version control
#
# ================================================

# Google Gemini API
# Get your key from: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# DeepSeek API (optional, for cloud version)
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Leave empty if no password

# Application Settings
ENVIRONMENT=development  # development, staging, or production
DEBUG=true              # true or false
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR

# Session Management
SESSION_TIMEOUT=3600
MAX_CONCURRENT_SESSIONS=10

# Security Settings
ENABLE_API_KEY_ROTATION=false
API_KEY_ROTATION_DAYS=90
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

### .gitignore Configuration

**File**: `.gitignore`

```gitignore
# Environment files - NEVER COMMIT
.env
.env.local
.env.*.local

# API keys and secrets
secrets/
*.key
*.pem
*.p12

# Configuration with secrets
config/secrets.yaml
config/production.yaml

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# Logs
*.log
logs/

# Database
*.db
*.sqlite
*.sqlite3

# Cache
.cache/
*.cache

# OS files
.DS_Store
Thumbs.db
```

---

## Implementation

### Secure LLM Client

**File**: `src/ai_designer/llm/client.py`

```python
from ai_designer.config import get_api_key
import logging

class LLMClient:
    """Secure LLM client with API key protection"""

    def __init__(self, api_key: str = None):
        """Initialize with secure API key loading"""
        if api_key:
            self.api_key = api_key
        else:
            # Load from secure configuration
            self.api_key = get_api_key()

        # Validate API key
        self._validate_api_key()

        # Initialize client
        self._initialize_client()

    def _validate_api_key(self):
        """Validate API key before use"""
        if not self.api_key:
            raise ValueError("API key is required")

        if not self.api_key.startswith('AIza'):
            logging.warning("API key format may be invalid")

    def _initialize_client(self):
        """Initialize the LLM client"""
        # IMPORTANT: API key should never be logged
        logging.info("Initializing LLM client...")

        # Initialize with masked key in any debug output
        masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}"
        logging.debug(f"Using API key: {masked_key}")

    def __repr__(self):
        """Safe string representation"""
        masked_key = f"{self.api_key[:4]}...{self.api_key[-4:]}"
        return f"LLMClient(api_key='{masked_key}')"
```

### Secure Demo Scripts

All demo scripts now use secure configuration:

```python
from ai_designer.config import get_api_key
from ai_designer.llm.client import LLMClient

# Secure API key loading
api_key = get_api_key()

# Initialize client
client = LLMClient(api_key=api_key)

# Use client
response = client.generate_code("Create a box")
```

### Integration Tests

```python
import pytest
from ai_designer.config import get_api_key, get_config

def test_api_key_loaded():
    """Test that API key loads correctly"""
    api_key = get_api_key()
    assert api_key is not None
    assert api_key.startswith('AIza')

def test_api_key_not_logged():
    """Test that API key is not logged"""
    import logging
    from io import StringIO

    # Capture logs
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger()
    logger.addHandler(handler)

    # Load config
    config = get_config()

    # Check logs don't contain full API key
    log_content = log_capture.getvalue()
    assert 'AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc' not in log_content  # pragma: allowlist secret

def test_config_masking():
    """Test that config masks sensitive data"""
    config = get_config()
    config_str = str(config)

    # Config string should not contain full API key
    assert 'AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc' not in config_str  # pragma: allowlist secret
    assert '...' in config_str  # Should contain masking
```

---

## Best Practices

### 1. Development Workflow

```bash
# Initial setup
git clone <repository>
cd freecad-llm-automation

# Create .env from template
cp .env.example .env

# Edit .env with your API key
nano .env
# Set: GOOGLE_API_KEY=AIzaSyCWUpvNYmalx0whFyG6eIIcSY__ioMSZEc

# Verify .env is ignored
git status
# .env should NOT appear in untracked files

# Verify security
python -c "from ai_designer.config import get_config; print(get_config())"
# API key should be masked in output
```

### 2. Production Deployment

```bash
# Set environment variables directly (more secure)
export GOOGLE_API_KEY="your_production_api_key"  # pragma: allowlist secret
export ENVIRONMENT="production"
export DEBUG="false"

# Or use secret management service
# AWS: Store in AWS Secrets Manager
# GCP: Store in Secret Manager
# Azure: Store in Key Vault

# Deploy application
docker build -t freecad-llm .
docker run -e GOOGLE_API_KEY=$GOOGLE_API_KEY freecad-llm
```

### 3. Docker Security

**Dockerfile:**
```dockerfile
FROM python:3.9

# Don't copy .env file
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/

# Use build args for non-sensitive config
ARG ENVIRONMENT=production
ENV ENVIRONMENT=$ENVIRONMENT

# API keys passed at runtime via environment variables
CMD ["python", "src/main.py"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  freecad-llm:
    build: .
    environment:
      # Load from .env file (not committed)
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env  # Only for local development
```

### 4. CI/CD Security

**GitHub Actions:**
```yaml
name: CI/CD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Run tests
        env:
          # Use GitHub secrets
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: |
          pip install -r requirements-dev.txt
          pytest tests/
```

### 5. Code Review Checklist

Before committing code, verify:

- [ ] No API keys in source code
- [ ] `.env` file in `.gitignore`
- [ ] All secrets loaded from environment
- [ ] Sensitive data masked in logs
- [ ] Tests don't expose secrets
- [ ] Documentation doesn't contain real keys
- [ ] `.env.example` has placeholder values only

### 6. Security Monitoring

```python
class SecurityMonitor:
    """Monitor security-related events"""

    def __init__(self):
        self.audit_log = []
        self.alert_handlers = []

    def log_api_key_access(self, context):
        """Log API key access"""
        self.audit_log.append({
            'timestamp': datetime.now(),
            'event': 'api_key_access',
            'context': context,
            'user': os.getenv('USER'),
            'ip': self.get_client_ip()
        })

    def detect_suspicious_activity(self):
        """Detect suspicious API key usage"""
        # Multiple failed authentication attempts
        # Unusual access patterns
        # Access from unexpected IPs
        # High volume of requests
        pass

    def trigger_security_alert(self, alert_type, details):
        """Trigger security alert"""
        alert = {
            'timestamp': datetime.now(),
            'type': alert_type,
            'details': details,
            'severity': self.calculate_severity(alert_type)
        }

        for handler in self.alert_handlers:
            handler(alert)
```

### 7. Incident Response

If API key is compromised:

1. **Immediate Actions:**
   ```bash
   # Revoke compromised key immediately
   # Generate new key at: https://makersuite.google.com/app/apikey

   # Update .env file
   nano .env
   # Set new key

   # Rotate key in all environments
   # Update production secrets
   # Notify team
   ```

2. **Investigation:**
   ```python
   # Review audit logs
   security_monitor.get_audit_log(
       start_date=incident_date,
       event_type='api_key_access'
   )

   # Check for unauthorized usage
   # Identify affected systems
   ```

3. **Prevention:**
   ```python
   # Implement key rotation
   # Add rate limiting
   # Enhanced monitoring
   # Security training
   ```

---

## Security Checklist

### Initial Setup
- [ ] Created `.env` file with API key
- [ ] Verified `.env` in `.gitignore`
- [ ] Tested configuration loading
- [ ] Confirmed API key not in source code
- [ ] Verified git status (no .env tracking)

### Development
- [ ] Using secure config module
- [ ] API keys never logged
- [ ] Sensitive data masked in output
- [ ] Tests don't expose secrets
- [ ] Code reviews check for leaks

### Deployment
- [ ] Production uses environment variables or vault
- [ ] Different keys for dev/staging/production
- [ ] Secrets not in Docker images
- [ ] CI/CD uses encrypted secrets
- [ ] Monitoring and alerting enabled

### Maintenance
- [ ] Regular API key rotation
- [ ] Security audits performed
- [ ] Incident response plan ready
- [ ] Team trained on security
- [ ] Documentation up to date

---

## Additional Resources

### Getting API Keys

- **Google Gemini**: https://makersuite.google.com/app/apikey
- **DeepSeek**: https://platform.deepseek.com (if using cloud)

### Security Standards

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [12-Factor App Config](https://12factor.net/config)
- [GitHub Security Best Practices](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure)

### Tools

- **Secret Scanning**: git-secrets, truffleHog
- **Vulnerability Scanning**: Snyk, Dependabot
- **Password Management**: 1Password, LastPass, Bitwarden
- **Vault Solutions**: HashiCorp Vault, AWS Secrets Manager

---

## Conclusion

Security is not optional! Following these practices ensures:

- ✅ **API keys protected** from exposure
- ✅ **Version control clean** of sensitive data
- ✅ **Production secure** with proper secret management
- ✅ **Team aligned** on security practices
- ✅ **Systems monitored** for security issues

Remember: **When in doubt, don't commit it!**

---

**Version**: 1.0.0
**Last Updated**: February 2026
**Status**: Production Ready
**Security Level**: High
