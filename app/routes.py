import os
import uuid
import re

from werkzeug.utils import secure_filename

from app import app, db
from app.models import Product, Category, User, ProductMedia
from flask import render_template, request, redirect, url_for, session, flash

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
    for media_file in media_files:
        if not media_file or not media_file.filename:
            continue

        media_type = get_media_type(media_file.filename)

        if media_type is None:
            continue

        original_filename = secure_filename(media_file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            unique_filename
        )

        media_file.save(file_path)

        product_media = ProductMedia(
            filename=unique_filename,
            media_type=media_type,
            product_id=product_id
        )

        db.session.add(product_media)

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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/products')
def products():
    all_products = Product.query.all()
    return render_template('products.html', products=all_products)

@app.route("/products/<int:product_id>")
def product_detail(product_id):
    selected_product = Product.query.get_or_404(product_id)
    
    return render_template('product_detail.html', product=selected_product)

@app.route("/products/category/<category_name>")
def products_by_category(category_name):
    selected_category = Category.query.filter_by(name=category_name).first_or_404()
    filtered_products = Product.query.filter_by(category_id=selected_category.id).all()

    return render_template(
        "products.html",
        products=filtered_products,
        selected_category=category_name
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

@app.route("/account")
def account():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("account.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    products = Product.query.all()
    categories = Category.query.all()

    return render_template(
        "admin_dashboard.html",
        products=products,
        categories=categories
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
        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            media.filename
        )

        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(product)
    db.session.commit()

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/media/<int:media_id>/delete", methods=["POST"])
def admin_delete_media(media_id):
    if session.get("user_role") != "admin":
        return redirect(url_for("login"))

    media = ProductMedia.query.get_or_404(media_id)

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        media.filename
    )

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(media)
    db.session.commit()

    return redirect(url_for("admin_dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

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
                error="Password must be at least 8 characters and include uppercase, lowercase, number, and special character.",
                name=name,
                email=email
            )
        
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return render_template(
                "signup.html",
                error="An account with this email already exists.",
                name=name,
                email=email
            )
        
        new_user = User(
            name=name,
            email=email,
            role="customer"
        )

        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        session["user_name"] = new_user.name
        session["user_role"] = new_user.role

        return redirect(url_for("account"))

    return render_template("signup.html")

    