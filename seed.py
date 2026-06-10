from app import app, db
from app.models import Category, Product, User


with app.app_context():
    # Clear existing data
    Product.query.delete()
    Category.query.delete()
    User.query.delete()

    # Create categories
    necklaces = Category(name="Necklaces")
    bracelets = Category(name="Bracelets")
    earrings = Category(name="Earrings")
    rings = Category(name="Rings")

    db.session.add_all([necklaces, bracelets, earrings, rings])
    db.session.commit()

    # Create development admin user
    admin_user = User(
        name="Andrea",
        email="admin@veromurano.com",
        role="admin"
    )
    admin_user.set_password("admin123")

    db.session.add(admin_user)
    db.session.commit()

    # Create products
    products = [
        Product(
            name="Murano-Inspired Glass Necklace",
            description="A handcrafted Murano-inspired glass necklace with elegant colour details.",
            price=89.00,
            image_url=None,
            category_id=necklaces.id,
        ),
        Product(
            name="Blue Glass Bracelet",
            description="A delicate blue glass bracelet inspired by Venetian glasswork.",
            price=65.00,
            image_url=None,
            category_id=bracelets.id,
        ),
        Product(
            name="Handcrafted Glass Earrings",
            description="Lightweight handcrafted glass earrings with a colourful finish.",
            price=45.00,
            image_url=None,
            category_id=earrings.id,
        ),
    ]

    db.session.add_all(products)
    db.session.commit()

    print("Sample database data added successfully.")