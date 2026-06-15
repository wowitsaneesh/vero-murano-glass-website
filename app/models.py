from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False, default="customer")

    phone = db.Column(db.String(30), nullable=True)
    street_address = db.Column(db.String(200), nullable=True)
    address_line_2 = db.Column(db.String(200), nullable=True)
    suburb = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(10), nullable=True)
    postcode = db.Column(db.String(4), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email}>"
    
class PendingSignup(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    otp_hash = db.Column(
        db.String(255),
        nullable=False
    )

    otp_expires_at = db.Column(
        db.DateTime,
        nullable=False
    )

    otp_sent_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    failed_attempts = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def set_otp(self, otp):
        self.otp_hash = generate_password_hash(otp)

    def check_otp(self, otp):
        return check_password_hash(self.otp_hash, otp)


class Category(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    products = db.relationship("Product", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"


class Product(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    

    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)

    media = db.relationship(
        "ProductMedia",
        backref="product",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Product {self.name}>"
    
class ProductMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    media_type = db.Column(
        db.String(20),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

class OrderEnquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    customer_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    message = db.Column(db.Text, nullable=True)

    subtotal = db.Column(db.Float, nullable=False)
    gst = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)

    status = db.Column(
        db.String(20),
        nullable=False,
        default="New"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    items = db.relationship(
        "OrderItem",
        backref="order_enquiry",
        lazy=True,
        cascade="all, delete-orphan"
    )


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    product_name = db.Column(
        db.String(150),
        nullable=False
    )

    unit_price = db.Column(
        db.Float,
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    line_total = db.Column(
        db.Float,
        nullable=False
    )

    order_enquiry_id = db.Column(
        db.Integer,
        db.ForeignKey("order_enquiry.id"),
        nullable=False
    )