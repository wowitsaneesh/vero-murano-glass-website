# Vero Murano Glass Website

Vero Murano Glass is a full-stack web development project for a handcrafted Murano-inspired jewellery and glass accessories store.

The goal of this project is to build a polished online store-style website without online payments. Customers will be able to browse products, add items to a cart, enter shipping/contact details, and submit an order request. Instead of processing payment online, the website will send the order details to Andrea by email.

This project is also being used as a practical Agile Web Development learning project, with features being developed across small issues, branches, pull requests, and sprints.

## Current Features

- Homepage with improved storefront layout
- Product catalogue page
- Product detail pages
- Product category filtering
- SQLite database setup
- Product and category database models
- Database migrations using Flask-Migrate
- Sample seed data for local development
- Bootstrap-based responsive layout
- Custom CSS styling with variables for future dark mode support

## Planned Features

- Customer registration and login
- Shopping cart
- GST and total calculation
- Checkout-style order request form
- Email order request to Andrea
- Admin dashboard
- Product and category management
- Product image uploads
- Product media management
- Dark mode toggle
- Testing and deployment setup

## Technology Stack

This project uses:

- Python
- Flask
- HTML
- CSS
- Bootstrap
- JavaScript
- SQLite
- SQLAlchemy
- Flask-Migrate
- Git and GitHub

## Project Folder Structure

```text
vero-murano-glass-website/
│
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   │
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css
│   │   ├── js/
│   │   └── images/
│   │
│   └── templates/
│       ├── base.html
│       ├── home.html
│       ├── products.html
│       └── product_detail.html
│
├── migrations/
│   └── versions/
│
├── tests/
│
├── config.py
├── run.py
├── seed.py
├── README.md
├── requirements.txt
└── .gitignore
```

## Local Development Setup

Follow these steps to run the project locally.

### 1. Clone the repository

```bash
git clone https://github.com/wowitsaneesh/vero-murano-glass-website.git
cd vero-murano-glass-website
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

On macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Set the Flask app

On macOS/Linux:

```bash
export FLASK_APP=run.py
```

On Windows PowerShell:

```bash
$env:FLASK_APP="run.py"
```

### 6. Set up the database

Run the database migrations:

```bash
python -m flask db upgrade
```

This creates the local database tables based on the current migration files.

### 7. Add sample data

```bash
python seed.py
```

This adds sample categories and products to the local database for development.

### 8. Run the application

```bash
python run.py
```

Then open:

```text
http://127.0.0.1:5000/
```

## Database Notes

This project currently uses SQLite for local development.

The local database file is ignored by Git and should not be committed. Each developer can create their own local database by running:

```bash
python -m flask db upgrade
python seed.py
```

Database structure changes are managed using Flask-Migrate. When models are changed, a new migration should be created and committed.

Example:

```bash
python -m flask db migrate -m "Describe database change"
python -m flask db upgrade
```

## Git Workflow

This project uses a branch-based workflow.

Do not push directly to `main`, except for README-only updates.

For new features, create a branch using:

```text
feat/name-of-feature
```

For fixes, create a branch using:

```text
fix/name-of-fix
```

Example:

```bash
git checkout main
git pull origin main
git checkout -b feat/admin-dashboard
```

After completing the work:

```bash
git status
git add .
git commit -m "Add admin dashboard foundation"
git push origin feat/admin-dashboard
```

Then open a pull request on GitHub, review the changes, merge into `main`, pull the latest `main`, and delete the completed branch.

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