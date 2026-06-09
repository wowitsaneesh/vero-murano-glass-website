from app import app
from app.models import Product, Category
from flask import render_template

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