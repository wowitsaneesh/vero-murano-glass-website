from app import app
from flask import render_template

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/products')
def products():
    placeholder_products = [
        {
            "id": 1,
            "name": "Murano-Inspired Glass Necklace",
            "price": 89.00,
            "category": "Necklaces",
        },
        {
            "id": 2,
            "name": "Blue Glass Bracelet",
            "price": 65.00,
            "category": "Bracelets",
        },
        {
            "id": 3,
            "name": "Handcrafted Glass Earrings",
            "price": 45.00,
            "category": "Earrings",
        },
    ]
    return render_template('products.html', products=placeholder_products)

@app.route("/products/<int:product_id>")
def product_detail(product_id):
    placeholder_products = [
        {
            "id": 1,
            "name": "Murano-Inspired Glass Necklace",
            "price": 89.00,
            "category": "Necklaces",
            "description": "A handcrafted Murano-inspired glass necklace with elegant colour details.",
        },
        {
            "id": 2,
            "name": "Blue Glass Bracelet",
            "price": 65.00,
            "category": "Bracelets",
            "description": "A delicate blue glass bracelet inspired by Venetian glasswork.",
        },
        {
            "id": 3,
            "name": "Handcrafted Glass Earrings",
            "price": 45.00,
            "category": "Earrings",
            "description": "Lightweight handcrafted glass earrings with a colourful finish.",
        },
    ]
    selected_product = None; 

    for product in placeholder_products:
        if product["id"] == product_id:
            selected_product = product
    
    return render_template('product_detail.html', product=selected_product)

@app.route("/products/category/<category_name>")
def products_by_category(category_name):
    placeholder_products = [
        {
            "id": 1,
            "name": "Murano-Inspired Glass Necklace",
            "price": 89.00,
            "category": "Necklaces",
            "description": "A handcrafted Murano-inspired glass necklace with elegant colour details.",
        },
        {
            "id": 2,
            "name": "Blue Glass Bracelet",
            "price": 65.00,
            "category": "Bracelets",
            "description": "A delicate blue glass bracelet inspired by Venetian glasswork.",
        },
        {
            "id": 3,
            "name": "Handcrafted Glass Earrings",
            "price": 45.00,
            "category": "Earrings",
            "description": "Lightweight handcrafted glass earrings with a colourful finish.",
        },
    ]

    filtered_products = []

    for product in placeholder_products:
        if product["category"].lower() == category_name.lower():
            filtered_products.append(product)

    return render_template(
        "products.html",
        products=filtered_products,
        selected_category=category_name
    )