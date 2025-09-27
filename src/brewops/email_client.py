"""Email client for connecting to and reading emails via IMAP."""

import imaplib
import smtplib
import email
from email.header import decode_header
from email.message import Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Tuple, Optional, Union, Dict, Any
import logging
import re
from datetime import datetime
from email.utils import parseaddr, parsedate_to_datetime
import html2text

logger = logging.getLogger(__name__)


class EmailMessage:
    """Structured email message object."""
    
    def __init__(self,
                 sender_name: str = "",
                 sender_email: str = "",
                 subject: str = "",
                 body: str = "",
                 timestamp: Optional[datetime] = None,
                 message_id: str = "",
                 imap_uid: str = "",
                 references: str = ""):
        """Initialize email message object.

        Args:
            sender_name: Display name of sender
            sender_email: Email address of sender
            subject: Email subject line
            body: Clean email body text
            timestamp: When email was sent
            message_id: Unique message identifier (Message-ID header)
            imap_uid: IMAP UID for server operations
            references: References header for email threading
        """
        self.sender_name = sender_name
        self.sender_email = sender_email
        self.subject = subject
        self.body = body
        self.timestamp = timestamp
        self.message_id = message_id
        self.imap_uid = imap_uid
        self.references = references
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'subject': self.subject,
            'body': self.body,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'message_id': self.message_id,
            'imap_uid': self.imap_uid,
            'references': self.references
        }


class EmailClient:
    """IMAP email client for brewery operations."""

    def __init__(self, server: str, port: int = 993, use_ssl: bool = True, 
                 smtp_server: str = "", smtp_port: int = 587):
        """Initialize email client with server configuration.

        Args:
            server: IMAP server hostname (e.g., 'imap.gmail.com')
            port: IMAP server port (default 993 for SSL)
            use_ssl: Whether to use SSL connection (default True)
            smtp_server: SMTP server hostname (e.g., 'smtp.gmail.com')
            smtp_port: SMTP server port (default 587 for TLS)
        """
        self.server = server
        self.port = port
        self.use_ssl = use_ssl
        self.smtp_server = smtp_server or server.replace('imap', 'smtp')
        self.smtp_port = smtp_port
        self.connection: Optional[Union[imaplib.IMAP4_SSL, imaplib.IMAP4]] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    def connect(self, username: str, password: str) -> bool:
        """Connect and authenticate with the email server.

        Args:
            username: Email username/address
            password: Email password or app password

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Store credentials for SMTP use
            self.username = username
            self.password = password
            
            if self.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.server, self.port)
            else:
                self.connection = imaplib.IMAP4(self.server, self.port)

            # Authenticate
            if self.connection is None:
                return False
            status, response = self.connection.login(username, password)
            if status == 'OK':
                logger.info(f"Successfully connected to {self.server}")
                return True
            else:
                logger.error(f"Authentication failed: {response}")
                return False

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def select_inbox(self) -> bool:
        """Select the inbox folder.

        Returns:
            True if inbox selected successfully, False otherwise
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return False

        try:
            status, response = self.connection.select('INBOX')
            if status == 'OK':
                logger.info("Inbox selected successfully")
                return True
            else:
                logger.error(f"Failed to select inbox: {response}")
                return False
        except Exception as e:
            logger.error(f"Error selecting inbox: {e}")
            return False


    def fetch_all_emails_full(self) -> List[EmailMessage]:
        """Fetch all emails with body content.
        
        Returns:
            List of EmailMessage objects with full content
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return []
        
        try:
            # Search for all emails using regular search
            status, messages = self.connection.search(None, 'ALL')
            if status != 'OK':
                logger.error("Failed to search for emails")
                return []
            
            email_ids = messages[0].split()
            emails = []
            
            for email_id in email_ids:
                try:
                    # First, let's get the UID for this message
                    uid_status, uid_data = self.connection.fetch(email_id, '(UID)')
                    uid = ""
                    if uid_status == 'OK' and uid_data:
                        for item in uid_data:
                            if isinstance(item, bytes):
                                response_str = item.decode('utf-8', errors='ignore')
                                import re
                                uid_match = re.search(r'UID\s+(\d+)', response_str)
                                if uid_match:
                                    uid = uid_match.group(1)
                                    break
                    
                    # Now fetch the complete email message
                    status, msg_data = self.connection.fetch(email_id, '(RFC822)')
                    if status != 'OK' or not msg_data:
                        continue
                    
                    # Parse complete email
                    raw_email = msg_data[0]
                    if isinstance(raw_email, tuple) and len(raw_email) >= 2:
                        email_bytes = raw_email[1]
                        if isinstance(email_bytes, bytes):
                            msg = email.message_from_bytes(email_bytes)
                        else:
                            continue
                    else:
                        continue
                    
                    # Extract email data with UID
                    email_obj = self._parse_email_message(msg, uid)
                    if email_obj:
                        emails.append(email_obj)
                        
                except Exception as e:
                    logger.warning(f"Error processing email {email_id}: {e}")
                    continue
            
            logger.info(f"Found {len(emails)} emails with full content")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching all emails: {e}")
            return []

    def _parse_email_message(self, msg: Message, imap_uid: str = "") -> Optional[EmailMessage]:
        """Parse email message and extract clean content.
        
        Args:
            msg: Raw email message object
            imap_uid: IMAP UID for server operations
            
        Returns:
            EmailMessage object or None if parsing fails
        """
        try:
            # Extract sender information
            sender_name, sender_email = self._parse_sender(msg.get('From', ''))
            
            # Extract subject
            subject = self._decode_header(msg.get('Subject', 'No Subject'))
            
            # Extract timestamp
            timestamp = None
            date_str = msg.get('Date')
            if date_str:
                try:
                    timestamp = parsedate_to_datetime(date_str)
                except Exception as e:
                    logger.warning(f"Failed to parse date '{date_str}': {e}")
            
            # Extract message ID
            message_id = msg.get('Message-ID', '')

            # Extract References header for threading
            references = msg.get('References', '')

            # Extract body content
            body = self._extract_body(msg)

            # Clean the body text
            clean_body = self._clean_email_body(body)

            return EmailMessage(
                sender_name=sender_name,
                sender_email=sender_email,
                subject=subject,
                body=clean_body,
                timestamp=timestamp,
                message_id=message_id,
                imap_uid=imap_uid,
                references=references
            )
            
        except Exception as e:
            logger.error(f"Error parsing email message: {e}")
            return None

    def _parse_sender(self, from_header: str) -> Tuple[str, str]:
        """Parse sender name and email from From header.
        
        Args:
            from_header: Raw From header value
            
        Returns:
            Tuple of (sender_name, sender_email)
        """
        decoded_from = self._decode_header(from_header)
        sender_name, sender_email = parseaddr(decoded_from)
        
        # Clean up sender name if it exists
        if sender_name:
            sender_name = sender_name.strip('"\'')
        else:
            # If no display name, use the part before @ as name
            if sender_email and '@' in sender_email:
                sender_name = sender_email.split('@')[0]
        
        return sender_name, sender_email

    def _extract_body(self, msg: Message) -> str:
        """Extract body text from email message.
        
        Args:
            msg: Email message object
            
        Returns:
            Plain text body content
        """
        body = ""
        
        if msg.is_multipart():
            # Handle multipart messages
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get("Content-Disposition", "")
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                try:
                    if content_type == "text/plain":
                        # Plain text content
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            charset = part.get_content_charset() or 'utf-8'
                            body = payload.decode(charset, errors='ignore')
                            break  # Prefer plain text
                    elif content_type == "text/html" and not body:
                        # HTML content (fallback if no plain text)
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            charset = part.get_content_charset() or 'utf-8'
                            html_content = payload.decode(charset, errors='ignore')
                            # Convert HTML to plain text
                            h = html2text.HTML2Text()
                            h.ignore_links = True
                            h.ignore_images = True
                            body = h.handle(html_content)
                except Exception as e:
                    logger.warning(f"Error extracting body part: {e}")
                    continue
        else:
            # Handle single part messages
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload and isinstance(payload, bytes):
                    charset = msg.get_content_charset() or 'utf-8'
                    if content_type == "text/html":
                        html_content = payload.decode(charset, errors='ignore')
                        # Convert HTML to plain text
                        h = html2text.HTML2Text()
                        h.ignore_links = True
                        h.ignore_images = True
                        body = h.handle(html_content)
                    else:
                        body = payload.decode(charset, errors='ignore')
            except Exception as e:
                logger.warning(f"Error extracting single part body: {e}")
        
        return body

    def _clean_email_body(self, body: str) -> str:
        """Clean email body by removing signatures and reply chains.
        
        Args:
            body: Raw email body text
            
        Returns:
            Cleaned email body text
        """
        if not body:
            return ""
        
        # Split into lines for processing
        lines = body.split('\n')
        cleaned_lines = []
        
        # Common signature indicators
        signature_patterns = [
            r'^--\s*$',  # Standard signature delimiter
            r'^Best regards?[,.]?\s*$',
            r'^Thanks?[,.]?\s*$',
            r'^Sincerely[,.]?\s*$',
            r'^Cheers[,.]?\s*$',
            r'^Kind regards?[,.]?\s*$',
            r'^Warm regards?[,.]?\s*$'
        ]
        
        # Reply chain indicators
        reply_patterns = [
            r'^On .+ wrote:$',
            r'^From:.*$',
            r'^Sent:.*$',
            r'^To:.*$',
            r'^Subject:.*$',
            r'^Date:.*$',
            r'^\s*>',  # Quoted text
            r'^_{5,}',  # Long underscores
            r'^-{5,}',  # Long dashes
        ]
        
        in_signature = False
        in_reply_chain = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check for signature start
            if not in_signature:
                for pattern in signature_patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        in_signature = True
                        break
            
            # Check for reply chain start
            if not in_reply_chain:
                for pattern in reply_patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        in_reply_chain = True
                        break
            
            # Skip lines that are part of signature or reply chain
            if in_signature or in_reply_chain:
                continue
            
            # Skip very short lines that are likely artifacts
            if len(line_stripped) <= 2 and line_stripped in ['', '-', '_', '|']:
                continue
            
            cleaned_lines.append(line)
        
        # Join cleaned lines and remove excessive whitespace
        cleaned_body = '\n'.join(cleaned_lines)
        
        # Remove multiple consecutive newlines
        cleaned_body = re.sub(r'\n{3,}', '\n\n', cleaned_body)
        
        # Remove trailing/leading whitespace
        cleaned_body = cleaned_body.strip()
        
        return cleaned_body

    def send_email(self, to_email: str, subject: str, body: str,
                   body_type: str = "plain", cc: Optional[List[str]] = None,
                   bcc: Optional[List[str]] = None, in_reply_to: Optional[str] = None,
                   references: Optional[str] = None) -> bool:
        """Send an email using SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body content
            body_type: Either "plain" or "html" (default "plain")
            cc: List of CC email addresses (optional)
            bcc: List of BCC email addresses (optional)
            in_reply_to: Message-ID of the email being replied to (optional)
            references: References header for threading (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.username or not self.password:
            logger.error("Must be connected with credentials to send emails")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = subject

            # Generate a unique Message-ID for this email (required for Gmail threading)
            import uuid
            import time
            domain = self.username.split('@')[1] if '@' in self.username else 'localhost'
            message_id = f"<{uuid.uuid4()}.{int(time.time())}@{domain}>"
            msg['Message-ID'] = message_id

            if cc:
                msg['Cc'] = ', '.join(cc)

            # Add reply headers for threading
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
                logger.info(f"Setting In-Reply-To header: {in_reply_to}")
            if references:
                msg['References'] = references
                logger.info(f"Setting References header: {references}")

            # Attach body
            msg.attach(MIMEText(body, body_type))
            
            # Create SMTP connection
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS encryption
            server.login(self.username, self.password)
            
            # Send email
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
                
            text = msg.as_string()
            server.sendmail(self.username, recipients, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def reply_to_email(self, original_email: EmailMessage, reply_body: str,
                      body_type: str = "plain") -> bool:
        """Reply to an email with proper threading headers for Gmail.

        Args:
            original_email: The original EmailMessage being replied to
            reply_body: The reply message body
            body_type: Either "plain" or "html" (default "plain")

        Returns:
            True if reply sent successfully, False otherwise
        """
        if not original_email.message_id:
            logger.error("Cannot reply: original email has no Message-ID")
            return False

        # Construct reply subject - Gmail REQUIRES standard "Re:" format for threading
        subject = original_email.subject
        # Strip any existing Re: prefixes to avoid "Re: Re:" issues
        while subject.lower().startswith(('re:', 'r:', 'fwd:', 'fw:')):
            colon_pos = subject.find(':')
            if colon_pos > 0:
                subject = subject[colon_pos + 1:].strip()
            else:
                break
        reply_subject = f"Re: {subject}"

        # Set up proper Gmail threading headers
        # Gmail's updated threading policy requires consistent References headers
        in_reply_to = original_email.message_id

        # For Gmail threading, References should contain the original Message-ID
        # If the original email already has References, append to them
        if hasattr(original_email, 'references') and original_email.references:
            # Chain the references: original references + original message-id
            references = f"{original_email.references} {original_email.message_id}"
        else:
            # First reply in thread: just the original message-id
            references = original_email.message_id

        logger.info(f"Sending threaded reply to {original_email.sender_email}")
        logger.info(f"  Subject: {reply_subject}")
        logger.info(f"  In-Reply-To: {in_reply_to}")
        logger.info(f"  References: {references}")

        return self.send_email(
            to_email=original_email.sender_email,
            subject=reply_subject,
            body=reply_body,
            body_type=body_type,
            in_reply_to=in_reply_to,
            references=references
        )

    def create_gmail_label(self, label_name: str) -> bool:
        """Create a new Gmail label using IMAP.
        
        Args:
            label_name: Name of the label to create
            
        Returns:
            True if label created successfully, False otherwise
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return False
        
        try:
            # Gmail treats labels as folders in IMAP
            status, response = self.connection.create(label_name)
            if status == 'OK':
                logger.info(f"Gmail label '{label_name}' created successfully")
                return True
            else:
                logger.error(f"Failed to create label '{label_name}': {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating label '{label_name}': {e}")
            return False

    def list_gmail_labels(self) -> List[str]:
        """List all available Gmail labels.
        
        Returns:
            List of label names
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return []
        
        try:
            status, folders = self.connection.list()
            if status != 'OK':
                logger.error("Failed to list folders/labels")
                return []
            
            labels = []
            for folder in folders:
                if isinstance(folder, bytes):
                    folder_str = folder.decode('utf-8')
                    # Extract folder name from IMAP LIST response
                    # Format: '(\\HasNoChildren) "/" "INBOX"'
                    parts = folder_str.split('"')
                    if len(parts) >= 2:
                        labels.append(parts[-2])
            
            return labels
            
        except Exception as e:
            logger.error(f"Error listing labels: {e}")
            return []

    def apply_gmail_label(self, email_uid: str, label_name: str) -> bool:
        """Apply a Gmail label to an email message.
        
        Args:
            email_uid: UID of the email message
            label_name: Name of the label to apply
            
        Returns:
            True if label applied successfully, False otherwise
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return False
        
        try:
            # Use Gmail's X-GM-LABELS extension
            status, response = self.connection.uid('store', email_uid, 
                                                  '+X-GM-LABELS', f'"{label_name}"')
            if status == 'OK':
                logger.info(f"Applied label '{label_name}' to email {email_uid}")
                return True
            else:
                logger.error(f"Failed to apply label '{label_name}' to email {email_uid}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error applying label '{label_name}' to email {email_uid}: {e}")
            return False

    def remove_gmail_label(self, email_uid: str, label_name: str) -> bool:
        """Remove a Gmail label from an email message.
        
        Args:
            email_uid: UID of the email message
            label_name: Name of the label to remove
            
        Returns:
            True if label removed successfully, False otherwise
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return False
        
        try:
            # Use Gmail's X-GM-LABELS extension with minus sign
            status, response = self.connection.uid('store', email_uid, 
                                                  '-X-GM-LABELS', f'"{label_name}"')
            if status == 'OK':
                logger.info(f"Removed label '{label_name}' from email {email_uid}")
                return True
            else:
                logger.error(f"Failed to remove label '{label_name}' from email {email_uid}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing label '{label_name}' from email {email_uid}: {e}")
            return False

    def get_email_labels(self, email_uid: str) -> List[str]:
        """Get all labels applied to an email message.
        
        Args:
            email_uid: UID of the email message
            
        Returns:
            List of label names applied to the email
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return []
        
        try:
            # Fetch labels using X-GM-LABELS attribute
            status, data = self.connection.uid('fetch', email_uid, 'X-GM-LABELS')
            if status != 'OK' or not data:
                logger.error(f"Failed to fetch labels for email {email_uid}")
                return []
            
            labels = []
            for item in data:
                if isinstance(item, bytes):
                    item_str = item.decode('utf-8')
                    # Parse X-GM-LABELS response
                    # Format: 'UID (X-GM-LABELS ("Label1" "Label2"))'
                    import re
                    matches = re.findall(r'"([^"]*)"', item_str)
                    labels.extend(matches)
            
            return labels
            
        except Exception as e:
            logger.error(f"Error getting labels for email {email_uid}: {e}")
            return []

    def get_email_uids(self, search_criteria: str = 'ALL') -> List[str]:
        """Get UIDs of emails matching search criteria.
        
        Args:
            search_criteria: IMAP search criteria (default 'ALL')
            
        Returns:
            List of email UIDs
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return []
        
        try:
            # Use regular search and then fetch UIDs
            status, messages = self.connection.search(None, search_criteria)
            if status != 'OK':
                logger.error(f"Failed to search for emails with criteria: {search_criteria}")
                return []
            
            if not messages[0]:
                return []
                
            email_ids = messages[0].split()
            uids = []
            
            # Get UID for each message
            for email_id in email_ids:
                try:
                    status, uid_data = self.connection.fetch(email_id, '(UID)')
                    if status == 'OK' and uid_data:
                        for item in uid_data:
                            if isinstance(item, bytes):
                                response_str = item.decode('utf-8', errors='ignore')
                                import re
                                uid_match = re.search(r'UID\s+(\d+)', response_str)
                                if uid_match:
                                    uids.append(uid_match.group(1))
                except Exception as e:
                    logger.warning(f"Error getting UID for email {email_id}: {e}")
                    continue
            
            return uids
            
        except Exception as e:
            logger.error(f"Error searching for email UIDs: {e}")
            return []

    def apply_label(self, email_uid: str, label_name: str) -> bool:
        """Apply a Gmail label to an email message.
        
        This is an alias for apply_gmail_label to match domain logic interface.
        
        Args:
            email_uid: UID of the email message  
            label_name: Name of the label to apply
            
        Returns:
            True if label applied successfully, False otherwise
        """
        return self.apply_gmail_label(email_uid, label_name)

    def archive_email(self, email_uid: str) -> bool:
        """Archive an email by removing it from the inbox.

        For Gmail, this moves the email from Inbox to All Mail, effectively archiving it.

        Args:
            email_uid: UID of the email message to archive

        Returns:
            True if email archived successfully, False otherwise
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return False

        try:
            # Gmail archiving: Use COPY + STORE + EXPUNGE method
            # This is the standard way to archive emails in Gmail via IMAP

            # Step 1: Copy email to [Gmail]/All Mail (note the double quotes)
            status, response = self.connection.uid('copy', email_uid, '"[Gmail]/All Mail"')
            if status != 'OK':
                logger.error(f"Failed to copy email {email_uid} to All Mail: {response}")
                return False

            # Step 2: Mark email as deleted in INBOX
            status, response = self.connection.uid('store', email_uid, '+FLAGS', '\\Deleted')
            if status != 'OK':
                logger.error(f"Failed to mark email {email_uid} as deleted: {response}")
                return False

            # Step 3: Expunge to actually remove from INBOX
            self.connection.expunge()
            logger.info(f"Email {email_uid} archived successfully using copy-delete-expunge method")
            return True

        except Exception as e:
            logger.error(f"Error archiving email {email_uid}: {e}")
            return False

    def fetch_email_thread(self, email: EmailMessage) -> List[EmailMessage]:
        """Fetch all emails in a thread using Gmail's X-GM-THRID extension and fallback methods.

        Args:
            email: The EmailMessage to find the thread for

        Returns:
            List of EmailMessage objects in the thread, sorted chronologically
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return [email]

        logger.info(f"=== Starting thread fetch for email: {email.subject} ===")
        logger.info(f"  Message-ID: {email.message_id}")
        logger.info(f"  References: {email.references}")
        logger.info(f"  From: {email.sender_email}")

        try:
            thread_emails = []

            # Method 1: Try Gmail's X-GM-THRID extension first
            thread_emails = self._fetch_thread_by_gmail_thrid(email)

            if len(thread_emails) > 1:
                logger.info(f"Gmail X-GM-THRID found {len(thread_emails)} emails in thread")
                return thread_emails

            # Method 2: Fallback to References/Message-ID search
            logger.info("Gmail X-GM-THRID didn't find thread, trying References/Message-ID search")
            thread_emails = self._fetch_thread_by_references(email)

            if len(thread_emails) > 1:
                logger.info(f"References search found {len(thread_emails)} emails in thread")
                return thread_emails

            # Method 3: Subject-based search as last resort
            logger.info("References search didn't find thread, trying subject-based search")
            thread_emails = self._fetch_thread_by_subject(email)

            logger.info(f"=== Thread fetch complete: Found {len(thread_emails)} emails in thread ===")
            return thread_emails

        except Exception as e:
            logger.error(f"Error fetching email thread: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [email]

    def _fetch_thread_by_gmail_thrid(self, email: EmailMessage) -> List[EmailMessage]:
        """Fetch thread using Gmail's X-GM-THRID extension, searching across all folders."""
        if not self.connection:
            return [email]

        try:
            # First, get the thread ID for this email
            status, data = self.connection.uid('fetch', email.imap_uid, '(X-GM-THRID)')
            if status != 'OK' or not data:
                logger.debug("Could not fetch X-GM-THRID for email")
                return [email]

            # Parse the thread ID from response
            thread_id = None
            for item in data:
                if isinstance(item, bytes):
                    response_str = item.decode('utf-8', errors='ignore')
                    # Response format: "UID (X-GM-THRID 1234567890)"
                    import re
                    thrid_match = re.search(r'X-GM-THRID\s+(\d+)', response_str)
                    if thrid_match:
                        thread_id = thrid_match.group(1)
                        break

            if not thread_id:
                logger.debug("No X-GM-THRID found in response")
                return [email]

            logger.info(f"Found Gmail thread ID: {thread_id}")

            # Search across multiple Gmail folders
            folders_to_search = ['INBOX', '"[Gmail]/Sent Mail"', '"[Gmail]/All Mail"']
            all_thread_emails = []
            current_folder = None

            try:
                # Remember current folder
                status, response = self.connection.select()
                if status == 'OK':
                    current_folder = 'INBOX'  # Default assumption
            except Exception:
                pass

            for folder in folders_to_search:
                try:
                    logger.debug(f"Searching folder {folder} for thread ID {thread_id}")

                    # Select the folder
                    status, response = self.connection.select(folder)
                    if status != 'OK':
                        logger.debug(f"Could not select folder {folder}")
                        continue

                    # Search for emails with this thread ID in current folder
                    status, messages = self.connection.uid('search', 'ALL', f'X-GM-THRID {thread_id}')
                    if status == 'OK' and messages[0]:
                        email_uids = messages[0].split()
                        logger.info(f"Found {len(email_uids)} emails in {folder} for thread {thread_id}")

                        for uid in email_uids:
                            try:
                                status, data = self.connection.uid('fetch', uid, '(RFC822)')
                                if status == 'OK' and data:
                                    for response_part in data:
                                        if isinstance(response_part, tuple):
                                            import email as email_lib
                                            msg = email_lib.message_from_bytes(response_part[1])
                                            parsed_email = self._parse_email_message(msg, uid.decode())

                                            if parsed_email:
                                                # Check for duplicates by Message-ID
                                                if not any(e.message_id == parsed_email.message_id for e in all_thread_emails):
                                                    all_thread_emails.append(parsed_email)
                                                    logger.debug(f"Added email from {folder}: {parsed_email.subject}")
                            except Exception as e:
                                logger.debug(f"Error fetching email UID {uid} from {folder}: {e}")
                    else:
                        logger.debug(f"No emails found in {folder} for thread {thread_id}")

                except Exception as e:
                    logger.debug(f"Error searching folder {folder}: {e}")

            # Restore original folder if possible
            try:
                if current_folder:
                    self.connection.select(current_folder)
            except Exception:
                # Default back to INBOX
                self.connection.select('INBOX')

            # Sort by timestamp
            all_thread_emails.sort(key=lambda e: e.timestamp if e.timestamp else datetime.min)

            if len(all_thread_emails) > 1:
                logger.info(f"Gmail X-GM-THRID found {len(all_thread_emails)} emails across all folders")
                return all_thread_emails
            else:
                return [email]

        except Exception as e:
            logger.debug(f"Gmail X-GM-THRID method failed: {e}")
            # Make sure we're back in INBOX
            try:
                self.connection.select('INBOX')
            except Exception:
                pass
            return [email]

    def _fetch_thread_by_references(self, email: EmailMessage) -> List[EmailMessage]:
        """Fetch thread using References and Message-ID headers."""
        if not self.connection:
            return [email]

        try:
            thread_emails = []
            message_ids = set()

            # Collect all message IDs from the current email
            if email.message_id:
                message_ids.add(email.message_id.strip())
                logger.debug(f"Added current message ID: {email.message_id.strip()}")

            # Parse References header to get all related message IDs
            if email.references:
                ref_ids = email.references.split()
                logger.debug(f"Found {len(ref_ids)} reference IDs in References header")
                for ref_id in ref_ids:
                    ref_id = ref_id.strip()
                    if ref_id:
                        message_ids.add(ref_id)
                        logger.debug(f"Added reference ID: {ref_id}")

            if not message_ids:
                logger.info("No message IDs found for threading")
                return [email]

            logger.info(f"Searching for {len(message_ids)} message IDs in thread")

            # Try different search approaches for better Gmail compatibility
            for msg_id in message_ids:
                # Clean up the message ID - remove angle brackets for search
                clean_msg_id = msg_id.strip('<>')

                # Try multiple search approaches
                search_attempts = [
                    f'HEADER Message-ID "{msg_id}"',  # With angle brackets
                    f'HEADER Message-ID "{clean_msg_id}"',  # Without angle brackets
                    f'HEADER References "{msg_id}"',  # References with brackets
                    f'HEADER References "{clean_msg_id}"',  # References without brackets
                ]

                for search_criteria in search_attempts:
                    try:
                        logger.debug(f"Trying search: {search_criteria}")
                        status, messages = self.connection.search(None, search_criteria)

                        if status == 'OK' and messages[0]:
                            email_ids = messages[0].split()
                            logger.info(f"Found {len(email_ids)} emails with search: {search_criteria}")

                            for email_id in email_ids:
                                try:
                                    status, data = self.connection.fetch(email_id, '(RFC822 UID)')
                                    if status == 'OK' and data:
                                        for response_part in data:
                                            if isinstance(response_part, tuple):
                                                import email as email_lib
                                                msg = email_lib.message_from_bytes(response_part[1])
                                                parsed_email = self._parse_email_message(msg, email_id.decode())

                                                if parsed_email and parsed_email.message_id not in [e.message_id for e in thread_emails]:
                                                    thread_emails.append(parsed_email)
                                                    logger.debug(f"Added email: {parsed_email.subject}")

                                                    # Also add any new references we find
                                                    if parsed_email.references:
                                                        new_refs = parsed_email.references.split()
                                                        for new_ref in new_refs:
                                                            new_ref = new_ref.strip()
                                                            if new_ref and new_ref not in message_ids:
                                                                message_ids.add(new_ref)
                                except Exception as e:
                                    logger.debug(f"Error processing email {email_id}: {e}")

                        else:
                            logger.debug(f"No results for: {search_criteria}")

                    except Exception as e:
                        logger.debug(f"Search failed for {search_criteria}: {e}")

            # Sort and return
            thread_emails.sort(key=lambda e: e.timestamp if e.timestamp else datetime.min)
            logger.info(f"References method found {len(thread_emails)} emails")
            return thread_emails if thread_emails else [email]

        except Exception as e:
            logger.debug(f"References method failed: {e}")
            return [email]

    def _fetch_thread_by_subject(self, email: EmailMessage) -> List[EmailMessage]:
        """Fetch thread using subject-based search as fallback."""
        if not self.connection:
            return [email]

        try:
            thread_emails = []

            if not email.subject:
                return [email]

            # Strip common reply prefixes to get core subject
            clean_subject = email.subject
            for prefix in ['Re:', 'RE:', 'Fwd:', 'FW:', 'Fw:', 'AW:', 'Aw:']:
                while clean_subject.startswith(prefix):
                    clean_subject = clean_subject[len(prefix):].strip()

            if not clean_subject:
                return [email]

            logger.info(f"Searching by subject: '{clean_subject}'")

            # Search for emails with similar subjects
            search_criteria = f'SUBJECT "{clean_subject}"'
            try:
                status, messages = self.connection.search(None, search_criteria)
                if status == 'OK' and messages[0]:
                    email_ids = messages[0].split()
                    logger.info(f"Found {len(email_ids)} emails with similar subject")

                    for email_id in email_ids[:15]:  # Limit to avoid too many results
                        try:
                            status, data = self.connection.fetch(email_id, '(RFC822 UID)')
                            if status == 'OK' and data:
                                for response_part in data:
                                    if isinstance(response_part, tuple):
                                        import email as email_lib
                                        msg = email_lib.message_from_bytes(response_part[1])
                                        parsed_email = self._parse_email_message(msg, email_id.decode())

                                        if parsed_email and parsed_email.message_id not in [e.message_id for e in thread_emails]:
                                            # Basic relationship check - same sender/recipient pairs
                                            is_related = (
                                                parsed_email.sender_email == email.sender_email or
                                                email.sender_email in parsed_email.body or
                                                parsed_email.sender_email in email.body
                                            )

                                            if is_related:
                                                thread_emails.append(parsed_email)
                                                logger.debug(f"Added subject-related email: {parsed_email.subject}")

                        except Exception as e:
                            logger.debug(f"Error processing email {email_id}: {e}")

            except Exception as e:
                logger.warning(f"Error in subject search: {e}")

            # Sort by timestamp and return
            if not thread_emails:
                thread_emails = [email]

            thread_emails.sort(key=lambda e: e.timestamp if e.timestamp else datetime.min)
            logger.info(f"Subject method found {len(thread_emails)} emails")
            return thread_emails

        except Exception as e:
            logger.debug(f"Subject method failed: {e}")
            return [email]

    def unarchive_email(self, email_uid: str) -> bool:
        """Unarchive an email by adding it back to the inbox.

        Args:
            email_uid: UID of the email message to unarchive

        Returns:
            True if email unarchived successfully, False otherwise
        """
        if not self.connection:
            logger.error("Not connected to email server")
            return False

        try:
            # Move email back to INBOX folder
            try:
                # Try to move from [Gmail]/All Mail back to INBOX (Gmail-specific)
                status, response = self.connection.uid('move', email_uid, 'INBOX')
                if status == 'OK':
                    logger.info(f"Email {email_uid} unarchived to INBOX successfully")
                    return True
            except Exception:
                pass

            # Alternative: Remove archived flag if it was set
            try:
                status, response = self.connection.uid('store', email_uid, '-FLAGS', '\\Archived')
                if status == 'OK':
                    logger.info(f"Email {email_uid} unarchived (removed archived flag) successfully")
                    return True
            except Exception:
                pass

            # Fallback: Remove seen flag to make it appear unread (minimal unarchive behavior)
            status, response = self.connection.uid('store', email_uid, '-FLAGS', '\\Seen')
            if status == 'OK':
                logger.info(f"Email {email_uid} unarchived (marked as unread) successfully")
                return True
            else:
                logger.error(f"Failed to unarchive email {email_uid}: {response}")
                return False

        except Exception as e:
            logger.error(f"Error unarchiving email {email_uid}: {e}")
            return False

    def _decode_header(self, header: str) -> str:
        """Decode email header that might be encoded.

        Args:
            header: Raw header string

        Returns:
            Decoded header string
        """
        if not header:
            return ''

        try:
            decoded_parts = decode_header(header)
            decoded_header = ''

            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_header += part.decode(encoding)
                    else:
                        decoded_header += part.decode('utf-8', errors='ignore')
                else:
                    decoded_header += str(part)

            return decoded_header.strip()
        except Exception as e:
            logger.warning(f"Error decoding header '{header}': {e}")
            return header

    def print_all_emails(self) -> None:
        """Print all emails in the format 'From: X, Subject: Y' (summary view)."""
        emails = self.fetch_all_emails_full()

        if not emails:
            print("No emails found.")
            return

        print(f"\nFound {len(emails)} emails:")
        print("-" * 60)

        for email_msg in emails:
            sender_info = f"{email_msg.sender_name} ({email_msg.sender_email})" if email_msg.sender_name else email_msg.sender_email
            print(f"From: {sender_info}, Subject: {email_msg.subject}")

    def print_all_emails_full(self) -> None:
        """Print all emails with full content in structured format (detailed view)."""
        emails = self.fetch_all_emails_full()
        
        if not emails:
            print("No emails found.")
            return
        
        print(f"\nFound {len(emails)} emails:")
        print("=" * 80)
        
        for i, email_obj in enumerate(emails, 1):
            print(f"\n--- Email {i} ---")
            print(f"From: {email_obj.sender_name} <{email_obj.sender_email}>")
            print(f"Subject: {email_obj.subject}")
            if email_obj.timestamp:
                print(f"Date: {email_obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Message ID: {email_obj.message_id}")
            print("\nBody:")
            print("-" * 40)
            print(email_obj.body[:500] + "..." if len(email_obj.body) > 500 else email_obj.body)
            print("-" * 40)

    def disconnect(self) -> None:
        """Close the connection to the email server."""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.connection = None


def main() -> None:
    """Demo function to test email connection."""
    import os
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    # Configuration - in production these should come from environment variables
    EMAIL_SERVER = os.getenv('EMAIL_SERVER', 'imap.gmail.com')
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')

    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        print("Please set EMAIL_USERNAME and EMAIL_PASSWORD environment variables")
        print("For Gmail, use an app password instead of your regular password")
        return

    # Create email client
    client = EmailClient(EMAIL_SERVER)

    # Connect and authenticate
    if not client.connect(EMAIL_USERNAME, EMAIL_PASSWORD):
        print("Failed to connect to email server")
        return

    # Select inbox
    if not client.select_inbox():
        print("Failed to select inbox")
        client.disconnect()
        return

    # Print all emails (headers only)
    print("\n=== Header-only Email List ===")
    client.print_all_emails()
    
    # Print full emails with content
    print("\n=== Full Email Content ===")
    client.print_all_emails_full()

    # Demonstrate thread functionality
    print("\n=== Email Thread Demonstration ===")
    emails = client.fetch_all_emails_full()
    if emails:
        print(f"Testing thread fetch for first email: {emails[0].subject}")
        thread = client.fetch_email_thread(emails[0])
        print(f"Thread contains {len(thread)} email(s):")
        for i, email in enumerate(thread, 1):
            print(f"  {i}. From: {email.sender_name} <{email.sender_email}>")
            print(f"     Subject: {email.subject}")
            print(f"     Date: {email.timestamp}")
            print(f"     Body preview: {email.body[:100]}...")
            print()
    else:
        print("No emails found to test threading with")

    # Disconnect
    client.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
