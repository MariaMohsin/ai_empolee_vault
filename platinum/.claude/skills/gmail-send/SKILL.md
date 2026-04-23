# Skill: gmail-send

Send real emails via Gmail SMTP.

## Usage

```bash
python .claude/skills/gmail-send/scripts/send_email.py \
  --to "recipient@example.com" \
  --subject "Subject line" \
  --body "Email content here"
```

## Setup

Set environment variables:
```bash
export EMAIL_ADDRESS="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
```

For Gmail App Password: https://myaccount.google.com/apppasswords

## Input Parameters

- `--to`: Recipient email address (required)
- `--subject`: Email subject line (required)
- `--body`: Email body text (required)
- `--cc`: CC recipients (optional, comma-separated)
- `--bcc`: BCC recipients (optional, comma-separated)

## Output

Success: "Email sent successfully to recipient@example.com"
Error: "Failed to send email: [error message]"

## Notes

- Uses Gmail SMTP (smtp.gmail.com:587)
- Requires Gmail App Password (not regular password)
- Supports plain text emails
- Production-ready with error handling
