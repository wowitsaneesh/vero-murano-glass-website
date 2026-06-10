from app import app
from app.models import Product, Category, User
from flask import render_template, request, redirect, url_for, session

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

    return render_template("admin_dashboard.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/signup")
def signup():
    return render_template("signup.html")