# Vero Murano Glass Website

Vero Murano Glass is a full-stack web development project for a handcrafted Murano-inspired jewellery and glass accessories store.

The goal of this project is to build a polished online store-style website without online payments. Customers will be able to browse products, add items to a cart, enter shipping/contact details, and submit an order request. Instead of processing payment online, the website will send the order details to Andrea by email.

## Planned Features

- Customer-facing product catalogue
- Product categories
- Product detail pages
- User registration and login
- Shopping cart
- GST and total calculation
- Checkout-style order request form
- Email order request to Andrea
- Admin dashboard
- Product and category management
- Product image uploads

## Technology Stack

This project will initially use:

- Python
- Flask
- HTML
- CSS
- Bootstrap
- JavaScript
- SQLite
- SQLAlchemy
- Git and GitHub

## Project Folder Structure

```text
vero-murano-glass-website/
│
├── app/
│   ├── __init__.py
│   ├── routes.py
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css
│   │   ├── js/
│   │   │   └── main.js
│   │   └── images/
│   │
│   └── templates/
│       ├── base.html
│       └── home.html
│
├── tests/
│
├── README.md
├── requirements.txt
└── .gitignore
```
## Initial Project Backlog

### Must Have

- Set up basic Flask application
- Create homepage layout
- Create product catalogue page
- Create product detail page
- Create product categories
- Add user registration and login
- Add shopping cart
- Calculate subtotal, GST, and total
- Create checkout-style order request form
- Send order request email to Andrea
- Create admin login
- Create admin dashboard
- Allow admin to add, edit, and remove products
- Allow admin to add, edit, and remove categories
- Allow admin to upload product images

### Should Have

- Allow Andrea to view submitted order requests in the admin portal
- Allow Andrea to view registered users
- Add product search
- Add product availability status
- Improve responsive design for mobile and tablet

### Could Have

- Add product videos
- Add featured collections
- Add related products
- Add customer order history
- Add contact/about page

### Won't Have in Version 1

- Online payment system
- Live shipping integration
- Discount codes
- Customer reviews
- Wishlist