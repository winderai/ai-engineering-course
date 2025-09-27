# Brewery Operations Hub

A demo application for processing brewery operations emails using AI.

## Phase 1: Basic Email Connection

This implementation provides basic email connectivity via IMAP to read unread emails.

### Features

- ✅ Connect to email provider using IMAP
- ✅ Authenticate with app password
- ✅ Select inbox folder  
- ✅ Fetch list of unread emails
- ✅ Print email subjects and senders

### Quick Start

1. **Set up email credentials using .env file (recommended):**
   ```bash
   cd src/brewery-ops
   cp .env.example .env
   # Edit .env file with your actual credentials
   ```

   Or set environment variables directly:
   ```bash
   export EMAIL_SERVER=imap.gmail.com  # Optional, defaults to Gmail
   export EMAIL_USERNAME=your-email@gmail.com
   export EMAIL_PASSWORD=your-app-password
   ```

2. **For Gmail users:**
   - Enable 2-factor authentication
   - Create an app password: https://support.google.com/accounts/answer/185833
   - Use the app password as `EMAIL_PASSWORD`

3. **Test the connection:**
   ```bash
   cd src/brewery-ops
   python test_email.py
   ```

4. **Run the FastAPI server:**
   ```bash
   cd src/brewery-ops
   python main.py
   ```

### API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /emails/test` - Test email connection
- `GET /emails/unread` - Get list of unread emails

### Example Output

When running `python test_email.py`, you should see:

```
=== Brewery Ops Email Connection Test ===

📧 Connecting to: imap.gmail.com
👤 Username: your-email@gmail.com

🔑 Authenticating...
✅ Authentication successful!
📂 Selecting inbox...
✅ Inbox selected!
📬 Fetching unread emails...

Found 3 unread emails:
------------------------------------------------------------
From: supplier@brewery-supplies.com, Subject: Order #12345 Ready for Pickup
From: equipment@brewtech.com, Subject: Maintenance Schedule for Tank #7
From: customer.service@hops-direct.com, Subject: Delivery Confirmation - Premium Hops

✅ Email connection test completed successfully!
```

### Testing with curl

```bash
# Test connection
curl http://localhost:8000/emails/test

# Get unread emails
curl http://localhost:8000/emails/unread
```

### Success Criteria ✅

- [x] Can see list of unread emails
- [x] Can print "From: X, Subject: Y" for each email  
- [x] No authentication errors
- [x] Proper error handling for missing credentials
- [x] FastAPI endpoints for web access

### Project Structure

```
src/brewery-ops/
├── main.py          # FastAPI application with email endpoints
├── email_client.py  # IMAP email client implementation
├── test_email.py    # Standalone test script
├── .env.example     # Example environment configuration
├── .env             # Your actual configuration (create from .env.example)
└── README.md        # This file
```

### Environment Configuration

The application now supports loading configuration from a `.env` file using python-dotenv. This makes it easier to manage credentials locally without exposing them in your shell history.

**Required variables:**
- `EMAIL_USERNAME` - Your email address
- `EMAIL_PASSWORD` - Your email password (use app password for Gmail)

**Optional variables:**
- `EMAIL_SERVER` - IMAP server (defaults to `imap.gmail.com`)

### Next Steps

This completes Phase 1. Future phases will add:
- Email content parsing and classification
- Integration with AI models for processing
- Database storage for email tracking
- Automated responses and workflows