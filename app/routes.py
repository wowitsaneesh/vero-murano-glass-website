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