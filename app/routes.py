import os
import uuid
import re
import smtplib
import json
import urllib.error
import urllib.request
import html
import secrets
import hmac
import hashlib
import time

import vercel_blob

from email.message import EmailMessage
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

from app import app, db
from app.models import (
    Product,
    Category,
    User,
    ProductMedia,
    OrderEnquiry,
    OrderItem,
    PendingSignup
)

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

ALLOWED_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif"
}

ALLOWED_VIDEO_EXTENSIONS = {
    "mp4",
    "webm",
    "mov"
}


def get_media_type(filename):
    if "." not in filename:
        return None

    extension = filename.rsplit(".", 1)[1].lower()

    if extension in ALLOWED_IMAGE_EXTENSIONS:
        return "image"

    if extension in ALLOWED_VIDEO_EXTENSIONS:
        return "video"

    return None

def validate_product_form():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    price_text = request.form.get("price", "").strip()
    category_id_text = request.form.get("category_id", "").strip()

    if not name:
        return None, "Product name is required."

    if len(name) > 150:
        return None, "Product name cannot exceed 150 characters."

    if not description:
        return None, "Product description is required."

    try:
        price = float(price_text)
    except (TypeError, ValueError):
        return None, "Price must be a valid number."

    if price < 0:
        return None, "Price cannot be negative."

    try:
        category_id = int(category_id_text)
    except (TypeError, ValueError):
        return None, "Please select a valid category."

    category = db.session.get(Category, category_id)

    if category is None:
        return None, "The selected category does not exist."

    data = {
        "name": name,
        "description": description,
        "price": price,
        "category_id": category_id
    }

    return data, None


def validate_media_files(media_files):
    for media_file in media_files:
        if not media_file or not media_file.filename:
            continue

        if get_media_type(media_file.filename) is None:
            return (
                False,
                f"{media_file.filename} is not a supported image or video file."
            )

    return True, None


def save_product_media(media_files, product_id):
    using_blob_storage = bool(os.environ.get("BLOB_READ_WRITE_TOKEN"))

    for media_file in media_files:
        if not media_file or not media_file.filename:
            continue

        media_type = get_media_type(media_file.filename)

        if media_type is None:
            continue

        original_filename = secure_filename(media_file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"

        if using_blob_storage:
            blob = vercel_blob.put(
                unique_filename,
                media_file.read()
            )
            stored_filename = blob["url"]
        else:
            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                unique_filename
            )

            media_file.save(file_path)
            stored_filename = unique_filename

        product_media = ProductMedia(
            filename=stored_filename,
            media_type=media_type,
            product_id=product_id
        )

        db.session.add(product_media)


def save_video_urls(video_urls, product_id):
    for video_url in video_urls:
        video_url = video_url.strip()

        if not video_url:
            continue

        product_media = ProductMedia(
            filename=video_url,
            media_type="video",
            product_id=product_id
        )

        db.session.add(product_media)


def delete_media_file(media):
    if media.filename.startswith("http://") or media.filename.startswith("https://"):
        vercel_blob.delete([media.filename])
        return

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        media.filename
    )

    if os.path.exists(file_path):
        os.remove(file_path)


def generate_upload_token():
    expires_at = str(int(time.time()) + 300)

    signature = hmac.new(
        app.config["SECRET_KEY"].encode(),
        expires_at.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{expires_at}.{signature}"

def is_valid_password(password):
    if len(password) < 8:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False

    return True

def get_cart_summary():
    cart = session.get("cart", {})
    cart_items = []
    subtotal = 0

    for product_id, quantity in cart.items():
        product = db.session.get(Product, int(product_id))

        if product is None:
            continue

        quantity = int(quantity)
        line_total = product.price * quantity
        subtotal += line_total

        product_images = [
            media
            for media in product.media
            if media.media_type == "image"
        ]

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "line_total": line_total,
            "image": product_images[0] if product_images else None
        })

    gst = subtotal * 0.10
    total = subtotal + gst

    return {
        "items": cart_items,
        "subtotal": subtotal,
        "gst": gst,
        "total": total
    }

def build_order_summary(order):
    lines = []

    for item in order.items:
        lines.append(
            f"{item.product_name} "
            f"x {item.quantity} "
            f"@ ${item.unit_price:.2f} "
            f"= ${item.line_total:.2f}"
        )

    return "\n".join(lines)


def send_email(
    to_email,
    subject,
    text_body,
    html_body=None,
    reply_to=None
):
    mail_username = app.config.get("MAIL_USERNAME")
    mail_password = app.config.get("MAIL_PASSWORD")
    mail_server = app.config.get("MAIL_SERVER")
    mail_port = app.config.get("MAIL_PORT")

    if not mail_username or not mail_password:
        raise RuntimeError("Email credentials are not configured.")

    message = EmailMessage()
    message["From"] = f"Vero Murano Glass <{mail_username}>"
    message["To"] = to_email
    message["Subject"] = subject

    if reply_to:
        message["Reply-To"] = reply_to

    message.set_content(text_body)

    if html_body:
        message.add_alternative(
            html_body,
            subtype="html"
        )

    with smtplib.SMTP(mail_server, mail_port) as smtp:
        smtp.starttls()
        smtp.login(mail_username, mail_password)
        smtp.send_message(message)


def send_order_enquiry_emails(order):
    andrea_email = app.config.get("ANDREA_EMAIL")

    if not andrea_email:
        raise RuntimeError("Andrea's email is not configured.")

    order_summary = build_order_summary(order)

    safe_customer_name = html.escape(order.customer_name)
    safe_customer_email = html.escape(order.email)
    safe_customer_phone = html.escape(order.phone)
    safe_shipping_address = html.escape(
        order.shipping_address
    ).replace("\n", "<br>")

    safe_message = html.escape(
        order.message or "No message provided."
    ).replace("\n", "<br>")

    item_rows = ""

    for item in order.items:
        safe_product_name = html.escape(
            item.product_name
        )

        item_rows += f"""
            <tr>
                <td style="
                    padding: 16px 0;
                    border-bottom: 1px solid #eee7e2;
                ">
                    <div style="
                        color: #222222;
                        font-size: 15px;
                        font-weight: 600;
                    ">
                        {safe_product_name}
                    </div>

                    <div style="
                        margin-top: 5px;
                        color: #77706c;
                        font-size: 13px;
                    ">
                        Quantity: {item.quantity}
                        &nbsp;·&nbsp;
                        ${item.unit_price:.2f} each
                    </div>
                </td>

                <td style="
                    padding: 16px 0;
                    border-bottom: 1px solid #eee7e2;
                    color: #222222;
                    font-size: 15px;
                    font-weight: 700;
                    text-align: right;
                    white-space: nowrap;
                ">
                    ${item.line_total:.2f}
                </td>
            </tr>
        """

    andrea_text_body = f"""
A new order enquiry has been submitted.

Enquiry ID: {order.id}

Customer details
Name: {order.customer_name}
Email: {order.email}
Phone: {order.phone}

Shipping address:
{order.shipping_address}

Customer message:
{order.message or "No message provided."}

Products:
{order_summary}

Subtotal: ${order.subtotal:.2f}
GST: ${order.gst:.2f}
Total payable: ${order.total:.2f}

Reply directly to this email to contact the customer.
""".strip()

    customer_text_body = f"""
Hello {order.customer_name},

Thank you for submitting an order enquiry to Vero Murano Glass.

Your enquiry reference is #{order.id}.

Products:
{order_summary}

Subtotal: ${order.subtotal:.2f}
GST: ${order.gst:.2f}
Total payable: ${order.total:.2f}

Andrea will contact you to confirm product availability,
shipping, and payment details.

No payment has been taken online.

Regards,
Vero Murano Glass
""".strip()
    
    andrea_html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
</head>

<body style="
    margin: 0;
    padding: 0;
    background-color: #f7f3ef;
    font-family: Arial, Helvetica, sans-serif;
    color: #222222;
">
    <table
        role="presentation"
        width="100%"
        cellspacing="0"
        cellpadding="0"
        border="0"
        style="background-color: #f7f3ef;"
    >
        <tr>
            <td align="center" style="padding: 40px 16px;">
                <table
                    role="presentation"
                    width="100%"
                    cellspacing="0"
                    cellpadding="0"
                    border="0"
                    style="
                        max-width: 680px;
                        background-color: #ffffff;
                        border-radius: 22px;
                        overflow: hidden;
                        box-shadow:
                            0 18px 50px rgba(34, 34, 34, 0.08);
                    "
                >
                    <tr>
                        <td style="
                            padding: 34px 40px;
                            background-color: #222222;
                            text-align: center;
                        ">
                            <div style="
                                color: #ffffff;
                                font-family: Georgia, serif;
                                font-size: 27px;
                                font-weight: bold;
                            ">
                                Vero Murano Glass
                            </div>

                            <div style="
                                margin-top: 8px;
                                color: #d9d1cb;
                                font-size: 12px;
                                letter-spacing: 2px;
                                text-transform: uppercase;
                            ">
                                New order enquiry
                            </div>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 38px 40px 24px;">
                            <div style="
                                margin-bottom: 12px;
                                color: #965d45;
                                font-size: 12px;
                                font-weight: bold;
                                letter-spacing: 1.6px;
                                text-transform: uppercase;
                            ">
                                Action required
                            </div>

                            <h1 style="
                                margin: 0;
                                font-family: Georgia, serif;
                                font-size: 34px;
                                line-height: 1.2;
                                color: #222222;
                            ">
                                New enquiry from {safe_customer_name}
                            </h1>

                            <p style="
                                margin: 18px 0 0;
                                color: #625d59;
                                font-size: 15px;
                                line-height: 1.7;
                            ">
                                A customer has submitted an order enquiry.
                                Review their details and reply directly to
                                this email to contact them.
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 0 40px 26px;">
                            <table
                                role="presentation"
                                width="100%"
                                cellspacing="0"
                                cellpadding="0"
                                border="0"
                                style="
                                    background-color: #f7f3ef;
                                    border-radius: 16px;
                                "
                            >
                                <tr>
                                    <td style="padding: 20px 22px;">
                                        <div style="
                                            color: #77706c;
                                            font-size: 12px;
                                            letter-spacing: 1.3px;
                                            text-transform: uppercase;
                                        ">
                                            Enquiry reference
                                        </div>

                                        <div style="
                                            margin-top: 6px;
                                            color: #222222;
                                            font-size: 22px;
                                            font-weight: bold;
                                        ">
                                            #{order.id}
                                        </div>
                                    </td>

                                    <td style="
                                        padding: 20px 22px;
                                        text-align: right;
                                    ">
                                        <div style="
                                            color: #77706c;
                                            font-size: 12px;
                                            letter-spacing: 1.3px;
                                            text-transform: uppercase;
                                        ">
                                            Total payable
                                        </div>

                                        <div style="
                                            margin-top: 6px;
                                            color: #222222;
                                            font-size: 22px;
                                            font-weight: bold;
                                        ">
                                            ${order.total:.2f}
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 0 40px 26px;">
                            <h2 style="
                                margin: 0 0 14px;
                                font-family: Georgia, serif;
                                font-size: 23px;
                            ">
                                Customer details
                            </h2>

                            <table
                                role="presentation"
                                width="100%"
                                cellspacing="0"
                                cellpadding="0"
                                border="0"
                                style="
                                    border: 1px solid #eee7e2;
                                    border-radius: 16px;
                                "
                            >
                                <tr>
                                    <td style="
                                        padding: 20px 22px;
                                        color: #77706c;
                                        font-size: 13px;
                                    ">
                                        Full name
                                    </td>

                                    <td style="
                                        padding: 20px 22px;
                                        text-align: right;
                                        font-size: 14px;
                                        font-weight: 600;
                                    ">
                                        {safe_customer_name}
                                    </td>
                                </tr>

                                <tr>
                                    <td style="
                                        padding: 0 22px 20px;
                                        color: #77706c;
                                        font-size: 13px;
                                    ">
                                        Email
                                    </td>

                                    <td style="
                                        padding: 0 22px 20px;
                                        text-align: right;
                                        font-size: 14px;
                                    ">
                                        <a
                                            href="mailto:{safe_customer_email}"
                                            style="
                                                color: #965d45;
                                                text-decoration: none;
                                                font-weight: 600;
                                            "
                                        >
                                            {safe_customer_email}
                                        </a>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="
                                        padding: 0 22px 20px;
                                        color: #77706c;
                                        font-size: 13px;
                                    ">
                                        Phone
                                    </td>

                                    <td style="
                                        padding: 0 22px 20px;
                                        text-align: right;
                                        font-size: 14px;
                                        font-weight: 600;
                                    ">
                                        {safe_customer_phone}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 0 40px 26px;">
                            <h2 style="
                                margin: 0 0 14px;
                                font-family: Georgia, serif;
                                font-size: 23px;
                            ">
                                Shipping address
                            </h2>

                            <div style="
                                padding: 20px 22px;
                                background-color: #fbf8f5;
                                border: 1px solid #eee7e2;
                                border-radius: 16px;
                                color: #4f4945;
                                font-size: 14px;
                                line-height: 1.7;
                            ">
                                {safe_shipping_address}
                            </div>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 0 40px 26px;">
                            <h2 style="
                                margin: 0 0 14px;
                                font-family: Georgia, serif;
                                font-size: 23px;
                            ">
                                Customer message
                            </h2>

                            <div style="
                                padding: 20px 22px;
                                background-color: #fbf8f5;
                                border-left: 4px solid #965d45;
                                border-radius: 12px;
                                color: #4f4945;
                                font-size: 14px;
                                line-height: 1.7;
                            ">
                                {safe_message}
                            </div>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 0 40px 18px;">
                            <h2 style="
                                margin: 0 0 6px;
                                font-family: Georgia, serif;
                                font-size: 23px;
                            ">
                                Order summary
                            </h2>

                            <table
                                role="presentation"
                                width="100%"
                                cellspacing="0"
                                cellpadding="0"
                                border="0"
                            >
                                {item_rows}
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 4px 40px 30px;">
                            <table
                                role="presentation"
                                width="100%"
                                cellspacing="0"
                                cellpadding="0"
                                border="0"
                            >
                                <tr>
                                    <td style="
                                        padding: 8px 0;
                                        color: #625d59;
                                        font-size: 14px;
                                    ">
                                        Subtotal
                                    </td>

                                    <td style="
                                        padding: 8px 0;
                                        text-align: right;
                                        font-size: 14px;
                                        font-weight: 600;
                                    ">
                                        ${order.subtotal:.2f}
                                    </td>
                                </tr>

                                <tr>
                                    <td style="
                                        padding: 8px 0;
                                        color: #625d59;
                                        font-size: 14px;
                                    ">
                                        GST (10%)
                                    </td>

                                    <td style="
                                        padding: 8px 0;
                                        text-align: right;
                                        font-size: 14px;
                                        font-weight: 600;
                                    ">
                                        ${order.gst:.2f}
                                    </td>
                                </tr>

                                <tr>
                                    <td style="
                                        padding: 16px 0 0;
                                        border-top: 1px solid #ddd4ce;
                                        font-size: 17px;
                                        font-weight: bold;
                                    ">
                                        Total payable
                                    </td>

                                    <td style="
                                        padding: 16px 0 0;
                                        border-top: 1px solid #ddd4ce;
                                        text-align: right;
                                        font-size: 19px;
                                        font-weight: bold;
                                    ">
                                        ${order.total:.2f}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="
                            padding: 0 40px 40px;
                            text-align: center;
                        ">
                            <a
                                href="mailto:{safe_customer_email}?subject=Re:%20Vero%20Murano%20Glass%20enquiry%20%23{order.id}"
                                style="
                                    display: inline-block;
                                    padding: 14px 28px;
                                    background-color: #222222;
                                    color: #ffffff;
                                    border-radius: 999px;
                                    font-size: 14px;
                                    font-weight: bold;
                                    text-decoration: none;
                                "
                            >
                                Reply to customer
                            </a>

                            <p style="
                                margin: 14px 0 0;
                                color: #77706c;
                                font-size: 12px;
                                line-height: 1.6;
                            ">
                                You can also use your normal Reply button.
                                It will send the response to the customer.
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <td style="
                            padding: 26px 40px;
                            background-color: #f7f3ef;
                            text-align: center;
                        ">
                            <div style="
                                color: #222222;
                                font-family: Georgia, serif;
                                font-size: 18px;
                                font-weight: bold;
                            ">
                                Vero Murano Glass
                            </div>

                            <div style="
                                margin-top: 8px;
                                color: #77706c;
                                font-size: 12px;
                            ">
                                Website order enquiry notification
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
""".strip()

    customer_html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">
</head>

<body style="
    margin: 0;
    padding: 0;
    background-color: #f7f3ef;
    font-family: Arial, Helvetica, sans-serif;
    color: #222222;
">
    <table
        role="presentation"
        width="100%"
        cellspacing="0"
        cellpadding="0"
        border="0"
        style="background-color: #f7f3ef;"
    >
        <tr>
            <td align="center" style="padding: 40px 16px;">
                <table
                    role="presentation"
                    width="100%"
                    cellspacing="0"
                    cellpadding="0"
                    border="0"
                    style="
                        max-width: 640px;
                        background-color: #ffffff;
                        border-radius: 22px;
                        overflow: hidden;
                        box-shadow:
                            0 18px 50px rgba(34, 34, 34, 0.08);
                    "
                >
                    <tr>
                        <td style="
                            padding: 34px 40px;
                            background-color: #222222;
                            text-align: center;
                        ">
                            <div style="
                                color: #ffffff;
                                font-family: Georgia, serif;
                                font-size: 27px;
                                font-weight: bold;
                            ">
                                Vero Murano Glass
                            </div>

                            <div style="
                                margin-top: 8px;
                                color: #d9d1cb;
                                font-size: 12px;
                                letter-spacing: 2px;
                                text-transform: uppercase;
                            ">
                                Order enquiry confirmation
                            </div>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 38px 40px 24px;">
                            <div style="
                                margin-bottom: 12px;
                                color: #965d45;
                                font-size: 12px;
                                font-weight: bold;
                                letter-spacing: 1.6px;
                                text-transform: uppercase;
                            ">
                                Enquiry received
                            </div>

                            <h1 style="
                                margin: 0;
                                color: #222222;
                                font-family: Georgia, serif;
                                font-size: 34px;
                                line-height: 1.2;
                            ">
                                Thank you, {safe_customer_name}.
                            </h1>

                            <p style="
                                margin: 18px 0 0;
                                color: #625d59;
                                font-size: 15px;
                                line-height: 1.7;
                            ">
                                We have received your order enquiry.
                                Andrea will contact you shortly to confirm
                                availability, shipping and payment details.
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 0 40px 26px;">
                            <table
                                role="presentation"
                                width="100%"
                                cellspacing="0"
                                cellpadding="0"
                                border="0"
                                style="
                                    background-color: #f7f3ef;
                                    border-radius: 16px;
                                "
                            >
                                <tr>
                                    <td style="padding: 20px 22px;">
                                        <div style="
                                            color: #77706c;
                                            font-size: 12px;
                                            letter-spacing: 1.3px;
                                            text-transform: uppercase;
                                        ">
                                            Enquiry reference
                                        </div>

                                        <div style="
                                            margin-top: 6px;
                                            color: #222222;
                                            font-size: 22px;
                                            font-weight: bold;
                                        ">
                                            #{order.id}
                                        </div>
                                    </td>

                                    <td style="
                                        padding: 20px 22px;
                                        text-align: right;
                                    ">
                                        <div style="
                                            color: #77706c;
                                            font-size: 12px;
                                            letter-spacing: 1.3px;
                                            text-transform: uppercase;
                                        ">
                                            Total payable
                                        </div>

                                        <div style="
                                            margin-top: 6px;
                                            color: #222222;
                                            font-size: 22px;
                                            font-weight: bold;
                                        ">
                                            ${order.total:.2f}
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 0 40px 18px;">
                            <h2 style="
                                margin: 0 0 6px;
                                font-family: Georgia, serif;
                                font-size: 23px;
                            ">
                                Your order summary
                            </h2>

                            <table
                                role="presentation"
                                width="100%"
                                cellspacing="0"
                                cellpadding="0"
                                border="0"
                            >
                                {item_rows}
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 4px 40px 32px;">
                            <table
                                role="presentation"
                                width="100%"
                                cellspacing="0"
                                cellpadding="0"
                                border="0"
                            >
                                <tr>
                                    <td style="
                                        padding: 8px 0;
                                        color: #625d59;
                                        font-size: 14px;
                                    ">
                                        Subtotal
                                    </td>

                                    <td style="
                                        padding: 8px 0;
                                        color: #222222;
                                        font-size: 14px;
                                        font-weight: 600;
                                        text-align: right;
                                    ">
                                        ${order.subtotal:.2f}
                                    </td>
                                </tr>

                                <tr>
                                    <td style="
                                        padding: 8px 0;
                                        color: #625d59;
                                        font-size: 14px;
                                    ">
                                        GST (10%)
                                    </td>

                                    <td style="
                                        padding: 8px 0;
                                        color: #222222;
                                        font-size: 14px;
                                        font-weight: 600;
                                        text-align: right;
                                    ">
                                        ${order.gst:.2f}
                                    </td>
                                </tr>

                                <tr>
                                    <td style="
                                        padding: 16px 0 0;
                                        border-top: 1px solid #ddd4ce;
                                        color: #222222;
                                        font-size: 17px;
                                        font-weight: bold;
                                    ">
                                        Total payable
                                    </td>

                                    <td style="
                                        padding: 16px 0 0;
                                        border-top: 1px solid #ddd4ce;
                                        color: #222222;
                                        font-size: 19px;
                                        font-weight: bold;
                                        text-align: right;
                                    ">
                                        ${order.total:.2f}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding: 0 40px 38px;">
                            <div style="
                                padding: 20px;
                                background-color: #fbf8f5;
                                border: 1px solid #eee7e2;
                                border-radius: 14px;
                                color: #625d59;
                                font-size: 14px;
                                line-height: 1.7;
                            ">
                                <strong style="color: #222222;">
                                    What happens next?
                                </strong>

                                <br>

                                Andrea will review your enquiry and contact
                                you by email. No online payment has been
                                taken.
                            </div>
                        </td>
                    </tr>

                    <tr>
                        <td style="
                            padding: 26px 40px;
                            background-color: #f7f3ef;
                            text-align: center;
                        ">
                            <div style="
                                color: #222222;
                                font-family: Georgia, serif;
                                font-size: 18px;
                                font-weight: bold;
                            ">
                                Vero Murano Glass
                            </div>

                            <div style="
                                margin-top: 8px;
                                color: #77706c;
                                font-size: 12px;
                                line-height: 1.6;
                            ">
                                Handcrafted Murano-inspired jewellery
                                and glass accessories.
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
""".strip()

    send_email(
        to_email=andrea_email,
        subject=(
            f"New order enquiry #{order.id} "
            f"from {order.customer_name}"
        ),
        text_body=andrea_text_body,
        html_body=andrea_html_body,
        reply_to=order.email
    )

    send_email(
        to_email=order.email,
        subject=(
            f"Your Vero Murano Glass enquiry "
            f"#{order.id}"
        ),
        text_body=customer_text_body,
        html_body=customer_html_body,
        reply_to=andrea_email
    )

@app.context_processor
def inject_cart_data():
    cart_summary = get_cart_summary()

    cart_count = sum(
        item["quantity"]
        for item in cart_summary["items"]
    )

    return {
        "cart_count": cart_count,
        "navbar_cart": cart_summary
    }

@app.route("/")
def home():
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "home.html",
        categories=categories
    )

def is_ajax_request():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


@app.route("/products")
def products():
    page = request.args.get("page", 1, type=int)

    product_pagination = (
        Product.query
        .order_by(Product.id.desc())
        .paginate(
            page=page,
            per_page=12,
            error_out=False
        )
    )

    template = (
        "partials/products_list.html"
        if is_ajax_request()
        else "products.html"
    )

    return render_template(
        template,
        products=product_pagination.items,
        pagination=product_pagination,
        selected_category=None
    )

@app.route("/products/<int:product_id>")
def product_detail(product_id):
    selected_product = Product.query.get_or_404(product_id)
    
    return render_template('product_detail.html', product=selected_product)

@app.route("/products/category/<category_name>")
def products_by_category(category_name):
    selected_category = (
        Category.query
        .filter_by(name=category_name)
        .first_or_404()
    )

    page = request.args.get("page", 1, type=int)

    product_pagination = (
        Product.query
        .filter_by(category_id=selected_category.id)
        .order_by(Product.id.desc())
        .paginate(
            page=page,
            per_page=12,
            error_out=False
        )
    )

    template = (
        "partials/products_list.html"
        if is_ajax_request()
        else "products.html"
    )

    return render_template(
        template,
        products=product_pagination.items,
        pagination=product_pagination,
        selected_category=selected_category.name
    )

@app.route("/cart")
def cart():
    cart_summary = get_cart_summary()

    return render_template(
        "cart.html",
        cart=cart_summary
    )


@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    Product.query.get_or_404(product_id)

    cart = session.get("cart", {})
    product_key = str(product_id)

    cart[product_key] = int(cart.get(product_key, 0)) + 1

    session["cart"] = cart
    session.modified = True

    flash("Product added to cart.", "success")

    return redirect(request.referrer or url_for("products"))


@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    Product.query.get_or_404(product_id)

    try:
        quantity = int(request.form.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1

    cart = session.get("cart", {})
    product_key = str(product_id)

    if quantity <= 0:
        cart.pop(product_key, None)
    else:
        cart[product_key] = min(quantity, 99)

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)

    session["cart"] = cart
    session.modified = True

    flash("Product removed from cart.", "success")

    return redirect(url_for("cart"))


@app.route("/cart/clear", methods=["POST"])
def clear_cart():
    session.pop("cart", None)
    session.modified = True

    flash("Cart cleared.", "success")

    return redirect(url_for("cart"))

@app.route("/cart/change/<int:product_id>", methods=["POST"])
def change_cart_quantity(product_id):
    product = Product.query.get_or_404(product_id)

    data = request.get_json(silent=True) or {}

    try:
        change = int(data.get("change", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid quantity change."}), 400

    cart = session.get("cart", {})
    product_key = str(product_id)

    current_quantity = int(cart.get(product_key, 0))
    new_quantity = current_quantity + change

    if new_quantity <= 0:
        cart.pop(product_key, None)
        new_quantity = 0
    else:
        new_quantity = min(new_quantity, 99)
        cart[product_key] = new_quantity

    session["cart"] = cart
    session.modified = True

    cart_summary = get_cart_summary()

    cart_count = sum(
        item["quantity"]
        for item in cart_summary["items"]
    )

    line_total = product.price * new_quantity

    return jsonify({
        "product_id": product.id,
        "quantity": new_quantity,
        "line_total": round(line_total, 2),
        "subtotal": round(cart_summary["subtotal"], 2),
        "gst": round(cart_summary["gst"], 2),
        "total": round(cart_summary["total"], 2),
        "cart_count": cart_count,
        "cart_empty": len(cart_summary["items"]) == 0
    })

@app.route("/api/postcode/<postcode>")
def postcode_lookup(postcode):
    if not postcode.isdigit() or len(postcode) != 4:
        return jsonify({
            "error": "Enter a valid four-digit postcode."
        }), 400

    api_url = (
        f"https://v0.postcodeapi.com.au/suburbs/"
        f"{postcode}.json"
    )

    try:
        api_request = urllib.request.Request(
            api_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Vero-Murano-Glass"
            }
        )

        with urllib.request.urlopen(
            api_request,
            timeout=8
        ) as response:
            results = json.loads(
                response.read().decode("utf-8")
            )

    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError
    ):
        return jsonify({
            "error": "Postcode lookup is currently unavailable."
        }), 503

    if not results:
        return jsonify({
            "error": "No suburbs were found for this postcode."
        }), 404

    suburbs = sorted({
        result["name"]
        for result in results
        if result.get("name")
    })

    state = results[0].get("state", {}).get(
        "abbreviation",
        ""
    )

    return jsonify({
        "postcode": postcode,
        "state": state,
        "suburbs": suburbs
    })

@app.route("/checkout/enquiry", methods=["GET", "POST"])
def checkout_enquiry():
    cart_summary = get_cart_summary()

    if not cart_summary["items"]:
        flash("Your cart is empty.", "danger")
        return redirect(url_for("products"))

    logged_in_user = None

    if session.get("user_id"):
        logged_in_user = db.session.get(
            User,
            session["user_id"]
        )

    if request.method == "POST":
        customer_name = request.form.get(
            "customer_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        street_address = request.form.get(
            "street_address",
            ""
        ).strip()

        address_line_2 = request.form.get(
            "address_line_2",
            ""
        ).strip()

        postcode = request.form.get(
            "postcode",
            ""
        ).strip()

        suburb = request.form.get(
            "suburb",
            ""
        ).strip()

        state = request.form.get(
            "state",
            ""
        ).strip()

        message = request.form.get(
            "message",
            ""
        ).strip()

        if not customer_name:
            flash("Your name is required.", "danger")

        elif not email or "@" not in email:
            flash("A valid email address is required.", "danger")

        elif not phone:
            flash("Your phone number is required.", "danger")

        elif not street_address:
            flash("Your street address is required.", "danger")

        elif not postcode.isdigit() or len(postcode) != 4:
            flash("Enter a valid four-digit postcode.", "danger")

        elif not suburb:
            flash("Please select your suburb.", "danger")

        elif not state:
            flash("A valid Australian state is required.", "danger")

        else:
            try:
                address_parts = [street_address]

                if address_line_2:
                    address_parts.append(address_line_2)

                address_parts.append(
                    f"{suburb} {state} {postcode}"
                )

                shipping_address = "\n".join(address_parts)
                
                order = OrderEnquiry(
                    customer_name=customer_name,
                    email=email,
                    phone=phone,
                    shipping_address=shipping_address,
                    message=message or None,
                    subtotal=cart_summary["subtotal"],
                    gst=cart_summary["gst"],
                    total=cart_summary["total"],
                    status="New",
                    user_id=(
                        logged_in_user.id
                        if logged_in_user
                        else None
                    )
                )

                db.session.add(order)
                db.session.flush()

                for cart_item in cart_summary["items"]:
                    product = cart_item["product"]
                    quantity = cart_item["quantity"]
                    line_total = cart_item["line_total"]

                    order_item = OrderItem(
                        product_name=product.name,
                        unit_price=product.price,
                        quantity=quantity,
                        line_total=line_total,
                        order_enquiry_id=order.id
                    )

                    db.session.add(order_item)

                db.session.commit()

            except Exception:
                db.session.rollback()

                flash(
                    "Your enquiry could not be saved. Please try again.",
                    "danger"
                )

                return render_template(
                    "checkout_enquiry.html",
                    cart=cart_summary,
                    user=logged_in_user,
                    form_data=request.form
                )

            email_sent = True

            try:
                send_order_enquiry_emails(order)

            except Exception as error:
                print(f"Email sending failed: {error}")
                email_sent = False

            session.pop("cart", None)
            session.modified = True

            return render_template(
                "enquiry_confirmation.html",
                order=order,
                email_sent=email_sent
            )

    return render_template(
        "checkout_enquiry.html",
        cart=cart_summary,
        user=logged_in_user,
        form_data={}
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            session["user_role"] = user.role

            if user.is_admin():
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("account"))

    return render_template("login.html")

@app.route("/account", methods=["GET", "POST"])
def account():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        street_address = request.form.get(
            "street_address",
            ""
        ).strip()
        address_line_2 = request.form.get(
            "address_line_2",
            ""
        ).strip()
        suburb = request.form.get("suburb", "").strip()
        state = request.form.get("state", "").strip()
        postcode = request.form.get("postcode", "").strip()

        if not name:
            flash("Your name is required.", "danger")

        elif phone and len(phone) < 8:
            flash("Enter a valid phone number.", "danger")

        elif postcode and (
            not postcode.isdigit()
            or len(postcode) != 4
        ):
            flash(
                "Enter a valid four-digit postcode.",
                "danger"
            )

        elif any([
            street_address,
            suburb,
            state,
            postcode
        ]) and not all([
            street_address,
            suburb,
            state,
            postcode
        ]):
            flash(
                "Complete all required shipping address fields.",
                "danger"
            )

        else:
            user.name = name
            user.phone = phone or None
            user.street_address = street_address or None
            user.address_line_2 = address_line_2 or None
            user.suburb = suburb or None
            user.state = state or None
            user.postcode = postcode or None

            db.session.commit()

            flash(
                "Your profile details have been updated.",
                "success"
            )

            return redirect(url_for("account"))

    page = request.args.get("page", 1, type=int)

    order_pagination = (
        OrderEnquiry.query
        .filter_by(user_id=user.id)
        .order_by(OrderEnquiry.created_at.desc())
        .paginate(
            page=page,
            per_page=5,
            error_out=False
        )
    )

    if is_ajax_request():
        return render_template(
            "partials/account_orders_panel.html",
            order_enquiries=order_pagination.items,
            order_pagination=order_pagination
        )

    return render_template(
        "account.html",
        user=user,
        order_enquiries=order_pagination.items,
        order_pagination=order_pagination
    )


@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    product_page = request.args.get(
        "product_page",
        1,
        type=int
    )

    product_pagination = (
        Product.query
        .order_by(Product.id.desc())
        .paginate(
            page=product_page,
            per_page=10,
            error_out=False
        )
    )

    products = product_pagination.items
    categories = Category.query.all()

    order_page = request.args.get(
        "order_page",
        1,
        type=int
    )

    order_pagination = (
        OrderEnquiry.query
        .order_by(OrderEnquiry.created_at.desc())
        .paginate(
            page=order_page,
            per_page=10,
            error_out=False
        )
    )

    orders = order_pagination.items

    if is_ajax_request():
        ajax_section = request.args.get("ajax_section")

        if ajax_section == "products":
            return render_template(
                "partials/admin_products_panel.html",
                products=products,
                product_pagination=product_pagination,
                categories=categories
            )

        if ajax_section == "orders":
            return render_template(
                "partials/admin_orders_panel.html",
                orders=orders,
                order_pagination=order_pagination,
                product_pagination=product_pagination
            )

    return render_template(
        "admin_dashboard.html",
        products=products,
        product_pagination=product_pagination,
        categories=categories,
        orders=orders,
        order_pagination=order_pagination,
        using_blob_storage=bool(os.environ.get("BLOB_READ_WRITE_TOKEN"))
    )

@app.route("/admin/products/add", methods=["POST"])
def admin_add_product():
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    product_data, error = validate_product_form()

    if error:
        flash(error, "danger")
        return redirect(url_for("admin_dashboard"))

    media_files = request.files.getlist("media_files")
    media_valid, media_error = validate_media_files(media_files)

    if not media_valid:
        flash(media_error, "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        new_product = Product(
            name=product_data["name"],
            description=product_data["description"],
            price=product_data["price"],
            category_id=product_data["category_id"],
        )

        db.session.add(new_product)
        db.session.flush()

        save_product_media(media_files, new_product.id)
        save_video_urls(
            request.form.getlist("video_urls"),
            new_product.id
        )

        db.session.commit()

        flash("Product added successfully.", "success")

    except Exception:
        db.session.rollback()
        flash("The product could not be added.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/products/<int:product_id>/edit", methods=["POST"])
def admin_edit_product(product_id):
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    product = Product.query.get_or_404(product_id)

    product_data, error = validate_product_form()

    if error:
        flash(error, "danger")
        return redirect(url_for("admin_dashboard"))

    media_files = request.files.getlist("media_files")
    media_valid, media_error = validate_media_files(media_files)

    if not media_valid:
        flash(media_error, "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        product.name = product_data["name"]
        product.description = product_data["description"]
        product.price = product_data["price"]
        product.category_id = product_data["category_id"]

        save_product_media(media_files, product.id)
        save_video_urls(
            request.form.getlist("video_urls"),
            product.id
        )

        db.session.commit()

        flash("Product updated successfully.", "success")

    except Exception:
        db.session.rollback()
        flash("The product could not be updated.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
def admin_delete_product(product_id):
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    product = Product.query.get_or_404(product_id)

    for media in product.media:
        delete_media_file(media)

    db.session.delete(product)
    db.session.commit()

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/media/<int:media_id>/delete", methods=["POST"])
def admin_delete_media(media_id):
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    media = ProductMedia.query.get_or_404(media_id)

    delete_media_file(media)

    db.session.delete(media)
    db.session.commit()

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/media/upload-token", methods=["POST"])
def admin_media_upload_token():
    if session.get("user_role") != "admin":
        return jsonify({"error": "Not authorized."}), 403

    return jsonify({"token": generate_upload_token()})

@app.route("/admin/categories/add", methods=["POST"])
def admin_add_category():
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()

    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for("admin_dashboard"))

    if len(name) > 80:
        flash("Category name cannot exceed 80 characters.", "danger")
        return redirect(url_for("admin_dashboard"))

    existing_category = Category.query.filter(
        db.func.lower(Category.name) == name.lower()
    ).first()

    if existing_category:
        flash("A category with this name already exists.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        new_category = Category(name=name)

        db.session.add(new_category)
        db.session.commit()

        flash("Category added successfully.", "success")

    except Exception:
        db.session.rollback()
        flash("The category could not be added.", "danger")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/categories/<int:category_id>/edit", methods=["POST"])
def admin_edit_category(category_id):
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    category = Category.query.get_or_404(category_id)
    name = request.form.get("name", "").strip()

    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for("admin_dashboard"))

    if len(name) > 80:
        flash("Category name cannot exceed 80 characters.", "danger")
        return redirect(url_for("admin_dashboard"))

    existing_category = Category.query.filter(
        db.func.lower(Category.name) == name.lower(),
        Category.id != category.id
    ).first()

    if existing_category:
        flash("A category with this name already exists.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        category.name = name
        db.session.commit()

        flash("Category updated successfully.", "success")

    except Exception:
        db.session.rollback()
        flash("The category could not be updated.", "danger")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/categories/<int:category_id>/delete", methods=["POST"])
def admin_delete_category(category_id):
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    category = Category.query.get_or_404(category_id)

    if category.products:
        flash(
            "This category cannot be deleted because products are using it.",
            "danger"
        )
        return redirect(url_for("admin_dashboard"))

    try:
        db.session.delete(category)
        db.session.commit()

        flash("Category deleted successfully.", "success")

    except Exception:
        db.session.rollback()
        flash("The category could not be deleted.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

def generate_signup_otp():
    return str(secrets.randbelow(9000) + 1000)


def send_signup_otp_email(name, email, otp):
    safe_name = html.escape(name)
    safe_otp = html.escape(otp)

    text_body = f"""
Hello {name},

Your Vero Murano Glass verification code is:

{otp}

This code expires in 10 minutes.

If you did not request this account, you can ignore this email.

Regards,
Vero Murano Glass
""".strip()

    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
</head>

<body style="
    margin: 0;
    padding: 0;
    background-color: #f7f3ef;
    font-family: Arial, Helvetica, sans-serif;
    color: #222222;
">
    <table
        role="presentation"
        width="100%"
        cellspacing="0"
        cellpadding="0"
        border="0"
        style="background-color: #f7f3ef;"
    >
        <tr>
            <td
                align="center"
                style="padding: 40px 16px;"
            >
                <table
                    role="presentation"
                    width="100%"
                    cellspacing="0"
                    cellpadding="0"
                    border="0"
                    style="
                        max-width: 600px;
                        background-color: #ffffff;
                        border-radius: 22px;
                        overflow: hidden;
                        box-shadow:
                            0 18px 50px rgba(34, 34, 34, 0.08);
                    "
                >
                    <tr>
                        <td style="
                            padding: 34px 40px;
                            background-color: #222222;
                            text-align: center;
                        ">
                            <div style="
                                color: #ffffff;
                                font-family: Georgia, serif;
                                font-size: 27px;
                                font-weight: bold;
                            ">
                                Vero Murano Glass
                            </div>

                            <div style="
                                margin-top: 8px;
                                color: #d9d1cb;
                                font-size: 12px;
                                letter-spacing: 2px;
                                text-transform: uppercase;
                            ">
                                Email verification
                            </div>
                        </td>
                    </tr>

                    <tr>
                        <td style="
                            padding: 40px;
                            text-align: center;
                        ">
                            <div style="
                                color: #965d45;
                                font-size: 12px;
                                font-weight: bold;
                                letter-spacing: 1.6px;
                                text-transform: uppercase;
                            ">
                                Confirm your email
                            </div>

                            <h1 style="
                                margin: 14px 0 0;
                                color: #222222;
                                font-family: Georgia, serif;
                                font-size: 32px;
                                line-height: 1.2;
                            ">
                                Hello, {safe_name}
                            </h1>

                            <p style="
                                margin: 18px auto 0;
                                max-width: 440px;
                                color: #625d59;
                                font-size: 15px;
                                line-height: 1.7;
                            ">
                                Enter the verification code below to
                                complete the creation of your account.
                            </p>

                            <div style="
                                margin: 30px auto;
                                padding: 20px;
                                max-width: 280px;
                                background-color: #f7f3ef;
                                border: 1px solid #eee7e2;
                                border-radius: 18px;
                                color: #222222;
                                font-size: 38px;
                                font-weight: bold;
                                letter-spacing: 14px;
                            ">
                                {safe_otp}
                            </div>

                            <p style="
                                margin: 0;
                                color: #77706c;
                                font-size: 13px;
                                line-height: 1.6;
                            ">
                                This code expires in 10 minutes.
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <td style="
                            padding: 24px 40px;
                            background-color: #f7f3ef;
                            color: #77706c;
                            font-size: 12px;
                            line-height: 1.6;
                            text-align: center;
                        ">
                            If you did not request this account,
                            you can safely ignore this email.
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
""".strip()

    send_email(
        to_email=email,
        subject="Your Vero Murano Glass verification code",
        text_body=text_body,
        html_body=html_body
    )

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name:
            return render_template(
                "signup.html",
                error="Your name is required.",
                name=name,
                email=email
            )

        if not email or "@" not in email:
            return render_template(
                "signup.html",
                error="Enter a valid email address.",
                name=name,
                email=email
            )

        if password != confirm_password:
            return render_template(
                "signup.html",
                error="Passwords do not match.",
                name=name,
                email=email
            )

        if not is_valid_password(password):
            return render_template(
                "signup.html",
                error=(
                    "Password must be at least 8 characters "
                    "and include uppercase, lowercase, number, "
                    "and special character."
                ),
                name=name,
                email=email
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            return render_template(
                "signup.html",
                error=(
                    "An account with this email already exists."
                ),
                name=name,
                email=email
            )

        otp = generate_signup_otp()
        now = datetime.utcnow()

        pending_signup = PendingSignup.query.filter_by(
            email=email
        ).first()

        if pending_signup is None:
            pending_signup = PendingSignup(
                name=name,
                email=email,
                password_hash="",
                otp_hash="",
                otp_expires_at=now,
                otp_sent_at=now
            )

            db.session.add(pending_signup)

        pending_signup.name = name
        pending_signup.set_password(password)
        pending_signup.set_otp(otp)
        pending_signup.otp_expires_at = (
            now + timedelta(minutes=10)
        )
        pending_signup.otp_sent_at = now
        pending_signup.failed_attempts = 0

        try:
            db.session.commit()

            send_signup_otp_email(
                name=name,
                email=email,
                otp=otp
            )

        except Exception as error:
            db.session.rollback()
            print(f"Signup OTP error: {error}")

            return render_template(
                "signup.html",
                error=(
                    "We could not send the verification code. "
                    "Please try again."
                ),
                name=name,
                email=email
            )

        session["pending_signup_id"] = pending_signup.id

        return redirect(url_for("verify_email"))

    return render_template("signup.html")

@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    pending_signup_id = session.get(
        "pending_signup_id"
    )

    if not pending_signup_id:
        flash(
            "Please begin the signup process again.",
            "danger"
        )
        return redirect(url_for("signup"))

    pending_signup = db.session.get(
        PendingSignup,
        pending_signup_id
    )

    if pending_signup is None:
        session.pop("pending_signup_id", None)

        flash(
            "Your verification request could not be found.",
            "danger"
        )
        return redirect(url_for("signup"))

    if request.method == "POST":
        otp = request.form.get(
            "otp",
            ""
        ).strip()

        if not otp.isdigit() or len(otp) != 4:
            return render_template(
                "verify_email.html",
                email=pending_signup.email,
                error="Enter the four-digit code."
            )

        if pending_signup.failed_attempts >= 5:
            return render_template(
                "verify_email.html",
                email=pending_signup.email,
                error=(
                    "Too many incorrect attempts. "
                    "Request a new code."
                )
            )

        if datetime.utcnow() > pending_signup.otp_expires_at:
            return render_template(
                "verify_email.html",
                email=pending_signup.email,
                error=(
                    "This verification code has expired. "
                    "Request a new code."
                )
            )

        if not pending_signup.check_otp(otp):
            pending_signup.failed_attempts += 1
            db.session.commit()

            remaining_attempts = (
                5 - pending_signup.failed_attempts
            )

            return render_template(
                "verify_email.html",
                email=pending_signup.email,
                error=(
                    "Incorrect verification code. "
                    f"{remaining_attempts} attempt"
                    f"{'' if remaining_attempts == 1 else 's'} "
                    "remaining."
                )
            )

        existing_user = User.query.filter_by(
            email=pending_signup.email
        ).first()

        if existing_user:
            db.session.delete(pending_signup)
            db.session.commit()

            session.pop("pending_signup_id", None)

            flash(
                "An account with this email already exists.",
                "danger"
            )
            return redirect(url_for("login"))

        new_user = User(
            name=pending_signup.name,
            email=pending_signup.email,
            password_hash=pending_signup.password_hash,
            role="customer"
        )

        try:
            db.session.add(new_user)
            db.session.delete(pending_signup)
            db.session.commit()

        except Exception:
            db.session.rollback()

            return render_template(
                "verify_email.html",
                email=pending_signup.email,
                error=(
                    "Your account could not be created. "
                    "Please try again."
                )
            )

        session.pop("pending_signup_id", None)

        session["user_id"] = new_user.id
        session["user_name"] = new_user.name
        session["user_role"] = new_user.role

        flash(
            "Your email has been verified and your account is ready.",
            "success"
        )

        return redirect(url_for("account"))

    return render_template(
        "verify_email.html",
        email=pending_signup.email
    )


@app.route("/resend-verification-code", methods=["POST"])
def resend_verification_code():
    pending_signup_id = session.get(
        "pending_signup_id"
    )

    if not pending_signup_id:
        flash(
            "Please begin the signup process again.",
            "danger"
        )
        return redirect(url_for("signup"))

    pending_signup = db.session.get(
        PendingSignup,
        pending_signup_id
    )

    if pending_signup is None:
        session.pop("pending_signup_id", None)
        return redirect(url_for("signup"))

    now = datetime.utcnow()

    seconds_since_last_send = (
        now - pending_signup.otp_sent_at
    ).total_seconds()

    if seconds_since_last_send < 60:
        wait_seconds = int(
            60 - seconds_since_last_send
        )

        flash(
            f"Please wait {wait_seconds} seconds "
            "before requesting another code.",
            "danger"
        )

        return redirect(url_for("verify_email"))

    otp = generate_signup_otp()

    pending_signup.set_otp(otp)
    pending_signup.otp_expires_at = (
        now + timedelta(minutes=10)
    )
    pending_signup.otp_sent_at = now
    pending_signup.failed_attempts = 0

    try:
        db.session.commit()

        send_signup_otp_email(
            name=pending_signup.name,
            email=pending_signup.email,
            otp=otp
        )

    except Exception as error:
        db.session.rollback()
        print(f"OTP resend error: {error}")

        flash(
            "The verification code could not be sent.",
            "danger"
        )

        return redirect(url_for("verify_email"))

    flash(
        "A new verification code has been sent.",
        "success"
    )

    return redirect(url_for("verify_email"))

    