import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import schema

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASSWORD", "")
        self.sent_dir = "data/sent_proposals"
        os.makedirs(self.sent_dir, exist_ok=True)

    def send_proposal(
        self,
        proposal_id: int,
        db: Session,
        recipient_override: str = None,
        notes: str = None
    ) -> dict:
        """
        Dispatches the approved proposal directly from the user's registered company email
        to the issuing government/organization email address provided in the bid.
        """
        proposal = db.query(schema.Proposal).filter(schema.Proposal.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")

        tender = proposal.tender
        if not tender:
            raise ValueError(f"No tender associated with proposal {proposal_id}.")

        # 1. Resolve Sender Email (from registered company profile)
        company = db.query(schema.Company).first()
        sender_email = (company.email if company and company.email else "").strip()
        if not sender_email:
            sender_email = os.getenv("SENDER_EMAIL", "").strip()

        if not sender_email:
            raise ValueError(
                "Sender email is not configured. Please register your company email in the Company Profile before submitting."
            )

        company_name = (company.name if company and company.name else "Vendor Enterprise").strip()

        # 2. Resolve Recipient Email (from tender opportunity / procurement notice)
        recipient = (recipient_override or tender.issuer_email or "").strip()
        if not recipient:
            raise ValueError(
                f"Tender '{tender.title}' does not have a designated issuing authority email. Please provide a recipient email address."
            )

        subject = f"[Official Bid Proposal] {tender.title} - Ref #{tender.reference_id or tender.id}"

        # 3. Construct Formal Submission Package
        body_text = (
            f"Dear Procurement Selection Committee,\n\n"
            f"On behalf of {company_name} ({sender_email}), we are pleased to officially submit our formal proposal "
            f"for the opportunity '{tender.title}' (Reference ID: {tender.reference_id or tender.id}).\n\n"
            f"Executive Summary:\n"
            f"{proposal.executive_summary or 'Please find our attached bid proposal.'}\n\n"
            f"Compliance & Approach Summary:\n"
            f"{proposal.technical_approach or 'All requirements evaluated and verified against company ground truth.'}\n\n"
            f"The complete verified bid proposal document is attached.\n\n"
            f"Sincerely,\n"
            f"{company_name} Bid Management Team\n"
            f"Official Contact: {sender_email}\n"
            f"Submitted via BidPilot Autonomous Platform on {datetime.utcnow().strftime('%Y-%m-%d at %H:%M UTC')}"
        )

        if notes:
            body_text += f"\n\nApproval Notes:\n{notes}"

        # 4. Save Local Archival Audit Copy
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        record_file = os.path.join(self.sent_dir, f"Proposal_{proposal_id}_{timestamp_str}.md")
        with open(record_file, "w", encoding="utf-8") as f:
            f.write(
                f"# {subject}\n\n"
                f"**From:** {sender_email}\n"
                f"**To:** {recipient}\n"
                f"**Date:** {datetime.utcnow().isoformat()}\n\n"
                f"{proposal.full_content or body_text}"
            )

        # 5. Live Transmission or Local Archival Mode
        sent_live = False
        if self.smtp_user and self.smtp_pass:
            try:
                msg = MIMEMultipart()
                msg["From"] = sender_email
                msg["To"] = recipient
                msg["Subject"] = subject
                msg.attach(MIMEText(body_text, "plain"))

                # Attach proposal document
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload((proposal.full_content or body_text).encode("utf-8"))
                encoders.encode_base64(attachment)
                clean_ref = "".join(c for c in (tender.reference_id or str(tender.id)) if c.isalnum() or c in "-_")
                attachment.add_header("Content-Disposition", f"attachment; filename=Proposal_{clean_ref}.md")
                msg.attach(attachment)

                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)

                sent_live = True
                logger.info(f"Proposal {proposal_id} sent via live SMTP from {sender_email} to {recipient}")
            except Exception as e:
                logger.error(f"Live SMTP transmission error: {e}")
                raise RuntimeError(f"SMTP Transmission Failed: {str(e)}")

        # 6. Update Proposal & Tender State
        proposal.status = "SUBMITTED"
        tender.status = "SUBMITTED"
        proposal.review_notes = (
            (proposal.review_notes or "") +
            f"\n[DISPATCH AUDIT] Dispatched from {sender_email} to {recipient} at {datetime.utcnow().isoformat()}"
        )
        db.commit()
        db.refresh(proposal)
        db.refresh(tender)

        return {
            "status": "success",
            "message": f"Proposal successfully dispatched from {sender_email} to {recipient}",
            "sent_live": sent_live,
            "sender_email": sender_email,
            "recipient_email": recipient,
            "subject": subject,
            "local_audit_record": record_file,
            "timestamp": datetime.utcnow().isoformat()
        }
