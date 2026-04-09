import base64
import datetime
import random
import string
import time
import os
from googleapiclient.discovery import build
import re
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo
import google.auth.transport.requests
from google.oauth2.credentials import Credentials

from attachment_service import generate_attachment


def resolve_spintax(text):
    """Resolves {A|B|C} spintax in text."""
    if not text:
        return ""
    while "{" in text and "|" in text:
        match = re.search(r"\{([^{}]+)\}", text)
        if not match:
            break
        options = match.group(1).split("|")
        text = text.replace(match.group(0), random.choice(options), 1)
    return text


def render_dynamic_text(raw_text, replacements):
    rendered = raw_text or ""
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return resolve_spintax(rendered)


def apply_body_modifiers(final_body_html, ui_config):
    body_html = final_body_html or ""

    if ui_config.get("color"):
        rand_color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        body_html = (
            f"<div style='color: {rand_color}; border: 3px solid {rand_color}; padding: 10px;'>"
            f"{body_html}</div>"
        )

    if ui_config.get("unsub"):
        body_html += (
            "<br><br><p style='font-size:10px; color:gray;'>"
            "If you wish to stop receiving these emails, "
            "<a href='#'>click here to unsubscribe</a>.</p>"
        )

    return body_html


def _build_replacements(row, current_date_str):
    dest_email = row.get("Email", row.get("email", str(row.iloc[0])))
    name = str(row.get("Name", row.get("First_Name", "Customer")))
    txn_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    inv_len = random.choice([7, 8, 10])
    inv_no = "INV-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=inv_len))
    return dest_email, name, inv_no, {
        "[First_Name]": name,
        "[Email]": dest_email,
        "[Invoice_Number]": inv_no,
        "[Transaction_ID]": txn_id,
        "[Issue_Date]": current_date_str,
        "#INVOICE#": inv_no,
        "#RANDOM#": txn_id,
        "#DATE#": current_date_str,
        "#EMAIL#": dest_email,
        "#NAME#": name,
        "#FIRST_NAME#": name,
    }


def _attachment_mime_details(filename):
    lower_name = (filename or "").lower()
    if lower_name.endswith(".pdf"):
        return "application", "pdf"
    if lower_name.endswith(".docx"):
        return (
            "application",
            "vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    if lower_name.endswith(".pptx"):
        return (
            "application",
            "vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    if lower_name.endswith(".png"):
        return "image", "png"
    if lower_name.endswith(".jpg") or lower_name.endswith(".jpeg"):
        return "image", "jpeg"
    if lower_name.endswith(".gif"):
        return "image", "gif"
    if lower_name.endswith(".bmp"):
        return "image", "bmp"
    if lower_name.endswith(".tiff"):
        return "image", "tiff"
    if lower_name.endswith(".webp"):
        return "image", "webp"
    return "application", "octet-stream"


def start_bulk_dispatch(target_df, sender_list, ui_config, log_callback):
    """
    Handles the entire bulk dispatch process.
    ui_config: dict of all checkbox/entry values.
    log_callback: function(msg) to log to UI.
    """

    try:
        log_callback("Engine Dispatch Started!")

        subj_tmpl = ui_config.get("subject", "Invoice Attachment")
        raw_body_html = ui_config.get("raw_body_html", ui_config.get("body", ""))
        raw_attachment_html = ui_config.get("raw_attachment_html", ui_config.get("content", ""))
        sender_name_tmpl = ui_config.get("sender_name", "Sender")
        img_format = ui_config.get("img_format", "png")
        output_mode = ui_config.get("output_mode", "To pdf")
        custom_pdf_path = ui_config.get("custom_pdf_path")

        tfn1_val = ui_config.get("tfn1", "")
        if ui_config.get("tfn1_b64"):
            tfn1_val = base64.b64encode(tfn1_val.encode()).decode()

        tfn2_val = ui_config.get("tfn2", "")
        if ui_config.get("tfn2_b64"):
            tfn2_val = base64.b64encode(tfn2_val.encode()).decode()

        geo_choice = ui_config.get("geo", "USA")
        tz = (
            ZoneInfo("America/New_York") if geo_choice == "USA" else
            ZoneInfo("Europe/London") if geo_choice == "UK" else
            ZoneInfo("Australia/Sydney") if geo_choice == "AUS" else
            None
        )
        current_date_str = (
            datetime.datetime.now(tz).strftime("%B %d, %Y")
            if tz else time.strftime("%B %d, %Y")
        )

        total_limit = min(len(target_df), 1000)
        if ui_config.get("test_mail"):
            total_limit = 1
            log_callback("Test Mail mode: Sending to only 1 recipient.")

        base_delay = ui_config.get("delay", 1000) / 1000.0
        sent_count = 0
        total_sent_this_session = 0
        curr_user = None
        rotate_limit = ui_config.get("rotate_limit", 50)
        auth_choice = ui_config.get("auth_method", "Manual")

        for _, row in target_df.iterrows():
            if sent_count >= total_limit:
                break

            dest_email = None
            try:
                dest_email, name, inv_no, replacements = _build_replacements(row, current_date_str)

                log_callback(f"Preparing to send to {dest_email} (Invoice: {inv_no})")

                replacements["#TFN#"] = tfn1_val
                replacements["#TFNA#"] = tfn2_val

                final_body_html = render_dynamic_text(raw_body_html, replacements)
                final_attachment_html = render_dynamic_text(raw_attachment_html, replacements)

                sender_replacements = dict(replacements)
                sender_replacements["[First_Name]"] = name

                if ui_config.get("soft_fmt"):
                    final_attachment_html = f"<div style='font-family: monospace;'>{final_attachment_html}</div>"

                final_body_html = apply_body_modifiers(final_body_html, ui_config)

                attachment_buffer, attachment_name, cid_id = generate_attachment(
                    final_attachment_html=final_attachment_html,
                    output_mode=output_mode,
                    img_format=img_format,
                    config_dict={**ui_config, "inv_no": inv_no},
                )

                if auth_choice == "Manual":
                    acc_user = ui_config.get("manual_sender", "").strip()
                    acc_pass = ui_config.get("manual_pass", "").strip()
                else:
                    if ui_config.get("rotate_each"):
                        sender_idx = (total_sent_this_session // rotate_limit) % len(sender_list)
                    else:
                        sender_idx = sent_count % len(sender_list)
                    sender_acc = sender_list[sender_idx]
                    acc_user = sender_acc.get("email", "")
                    acc_pass = sender_acc.get("password", "")
                    acc_token = sender_acc.get("token", sender_acc.get("access_token", ""))
                    refresh_token = sender_acc.get("refresh_token", "")
                    client_id = sender_acc.get("client_id", "")
                    client_secret = sender_acc.get("client_secret", "")
                    token_uri = sender_acc.get("token_uri", "https://oauth2.googleapis.com/token")

                try:
                    if (auth_choice == "JSON" or auth_choice == "GoogleOAuth") and (acc_token or refresh_token):
                        creds = Credentials(
                            token=acc_token,
                            refresh_token=refresh_token,
                            token_uri=token_uri,
                            client_id=client_id,
                            client_secret=client_secret
                        )
                    else:
                        raise Exception("Gmail API strictly requires OAuth2 credentials. Support for manual login is gone.")
                    
                    if acc_user != curr_user:
                        curr_user = acc_user
                except Exception as auth_err:
                    log_callback(f"Auth FAILED for {acc_user}: {auth_err}")
                    if ui_config.get("limit_check"):
                        curr_user = None
                        continue
                    raise auth_err

                multipart_type = "related" if output_mode == "Inline image" else "mixed"
                msg = MIMEMultipart(multipart_type)

                sender_display_name = render_dynamic_text(sender_name_tmpl, sender_replacements)
                msg["From"] = f"{sender_display_name} <{acc_user}>"
                msg["To"] = f"{name} <{dest_email}>" if ui_config.get("with_name") else dest_email

                subj_final = render_dynamic_text(subj_tmpl, replacements)
                if ui_config.get("with_name") and f" {name}" not in subj_final:
                    subj_final += f" - {name}"
                msg["Subject"] = subj_final

                if ui_config.get("header"):
                    msg.add_header("X-Priority", "1 (Highest)")
                    msg.add_header("X-Mailer", "BM2 Ultra Modular Engine")

                body_html_for_message = final_body_html
                if output_mode == "Inline Html":
                    body_html_for_message += f"<br><br>{final_attachment_html}"
                elif output_mode == "Inline image" and attachment_buffer and cid_id:
                    body_html_for_message += f'<br><br><img src="cid:{cid_id}" alt="{attachment_name or "inline-image"}">'

                alternative_part = MIMEMultipart("alternative")
                alternative_part.attach(MIMEText(body_html_for_message, "html", "utf-8"))
                msg.attach(alternative_part)

                if attachment_buffer:
                    payload = attachment_buffer

                    if output_mode == "Inline image" and cid_id:
                        subtype = (attachment_name or f"file.{img_format}").rsplit(".", 1)[-1].lower()
                        if subtype == "jpg":
                            subtype = "jpeg"
                        image_part = MIMEImage(payload, _subtype=subtype)
                        image_part.add_header("Content-ID", f"<{cid_id}>")
                        image_part.add_header("Content-Disposition", f'inline; filename="{attachment_name}"')
                        msg.attach(image_part)
                    else:
                        maintype, subtype = _attachment_mime_details(attachment_name)
                        attachment_part = MIMEBase(maintype, subtype)
                        attachment_part.set_payload(payload)
                        encoders.encode_base64(attachment_part)
                        attachment_part.add_header("Content-Disposition", f'attachment; filename="{attachment_name}"')
                        msg.attach(attachment_part)
                
                # Add custom external PDF if selected
                if custom_pdf_path and os.path.exists(custom_pdf_path):
                    try:
                        with open(custom_pdf_path, 'rb') as f:
                            pdf_data = f.read()
                        
                        pdf_part = MIMEBase('application', 'pdf')
                        pdf_part.set_payload(pdf_data)
                        encoders.encode_base64(pdf_part)
                        
                        filename = os.path.basename(custom_pdf_path)
                        pdf_part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                        
                        msg.attach(pdf_part)
                    except Exception as e:
                        print(f"Warning: Could not attach custom PDF: {e}")

                raw_string = base64.urlsafe_b64encode(msg.as_bytes()).decode()
                raw_payload = {'raw': raw_string}

                service = build('gmail', 'v1', credentials=creds)
                service.users().messages().send(userId='me', body=raw_payload).execute()
                sent_count += 1
                total_sent_this_session += 1
                log_callback(f"SUCCESS: Sent to {dest_email} via {acc_user}")

                delay = base_delay
                if ui_config.get("delay_each"):
                    delay += random.uniform(0.5, 2.0)
                if ui_config.get("delay_50") and sent_count % 50 == 0:
                    log_callback("Every 50 Limit reached: Sleeping for 30 seconds.")
                    delay += 30
                time.sleep(delay)

            except Exception as row_err:
                log_callback(f"FAILED for {dest_email}: {row_err}")

        log_callback(f"Campaign Completed. Total sent: {sent_count}")

    except Exception as e:
        log_callback(f"ENGINE CRASH: {e}")
    finally:
        pass
