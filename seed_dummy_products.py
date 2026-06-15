import random

from app import app, db
from app.models import Category, Product


PRODUCTS_PER_CATEGORY = 50
SEED_MARKER = "[DUMMY-SEED]"

CATEGORY_DATA = {
    "Necklaces": {
        "product_types": [
            "Pendant Necklace",
            "Glass Bead Necklace",
            "Statement Necklace",
            "Teardrop Necklace",
            "Venetian Necklace",
        ],
        "price_range": (69, 249),
    },
    "Bracelets": {
        "product_types": [
            "Charm Bracelet",
            "Glass Bead Bracelet",
            "Cuff Bracelet",
            "Link Bracelet",
            "Venetian Bracelet",
        ],
        "price_range": (45, 179),
    },
    "Earrings": {
        "product_types": [
            "Drop Earrings",
            "Stud Earrings",
            "Hoop Earrings",
            "Dangle Earrings",
            "Teardrop Earrings",
        ],
        "price_range": (39, 159),
    },
    "Rings": {
        "product_types": [
            "Glass Stone Ring",
            "Cocktail Ring",
            "Band Ring",
            "Statement Ring",
            "Mosaic Ring",
        ],
        "price_range": (35, 149),
    },
    "Pendants": {
        "product_types": [
            "Heart Pendant",
            "Oval Pendant",
            "Flower Pendant",
            "Mosaic Pendant",
            "Teardrop Pendant",
        ],
        "price_range": (49, 189),
    },
    "Brooches": {
        "product_types": [
            "Floral Brooch",
            "Butterfly Brooch",
            "Mosaic Brooch",
            "Leaf Brooch",
            "Abstract Brooch",
        ],
        "price_range": (55, 199),
    },
    "Cufflinks": {
        "product_types": [
            "Round Cufflinks",
            "Square Cufflinks",
            "Mosaic Cufflinks",
            "Venetian Cufflinks",
            "Glass Inlay Cufflinks",
        ],
        "price_range": (59, 189),
    },
    "Home Décor": {
        "product_types": [
            "Decorative Bowl",
            "Glass Ornament",
            "Miniature Sculpture",
            "Decorative Plate",
            "Glass Figurine",
        ],
        "price_range": (79, 399),
    },
    "Vases": {
        "product_types": [
            "Bud Vase",
            "Flared Vase",
            "Mosaic Vase",
            "Sculptural Vase",
            "Venetian Table Vase",
        ],
        "price_range": (129, 599),
    },
    "Gift Sets": {
        "product_types": [
            "Jewellery Gift Set",
            "Pendant and Earring Set",
            "Bracelet Gift Set",
            "Murano Keepsake Set",
            "Celebration Gift Set",
        ],
        "price_range": (99, 349),
    },
}

COLOURS = [
    "Azure",
    "Ruby",
    "Emerald",
    "Amber",
    "Amethyst",
    "Rose",
    "Lagoon Blue",
    "Midnight",
    "Ivory",
    "Aqua",
]

STYLES = [
    "Venetian",
    "Millefiori",
    "Murano-Inspired",
    "Golden Foil",
    "Silver Foil",
    "Mosaic",
    "Artisan",
    "Classic",
    "Contemporary",
    "Luminous",
]

DESCRIPTIONS = [
    (
        "A handcrafted Murano-inspired piece featuring layered glass tones "
        "and refined Venetian-style detailing."
    ),
    (
        "An elegant glass design created with vibrant colour, delicate "
        "patterns, and a polished artisan finish."
    ),
    (
        "A distinctive statement piece inspired by traditional Venetian "
        "glassmaking and modern Italian design."
    ),
    (
        "Richly coloured glass elements give this piece a luminous finish "
        "suited to both everyday wear and special occasions."
    ),
    (
        "Designed with carefully arranged glass details, subtle texture, "
        "and an elegant handcrafted appearance."
    ),
    (
        "A colourful Murano-inspired creation combining timeless form with "
        "a contemporary decorative finish."
    ),
]


def rounded_price(minimum, maximum):
    price = random.randint(minimum, maximum)

    endings = [0, 5, 9]
    price = (price // 10) * 10 + random.choice(endings)

    return float(max(minimum, min(price, maximum)))


def create_product_name(category_name, product_types, index):
    colour = COLOURS[(index - 1) % len(COLOURS)]
    style = STYLES[((index - 1) // len(COLOURS)) % len(STYLES)]
    product_type = product_types[(index - 1) % len(product_types)]

    return f"{colour} {style} {product_type} {index:02d}"


def seed_products():
    random.seed(2026)

    created_categories = 0
    created_products = 0

    for category_name, category_info in CATEGORY_DATA.items():
        category = Category.query.filter_by(
            name=category_name
        ).first()

        if category is None:
            category = Category(name=category_name)
            db.session.add(category)
            db.session.flush()

            created_categories += 1

        existing_seeded_products = Product.query.filter(
            Product.category_id == category.id,
            Product.description.contains(SEED_MARKER),
        ).all()

        for product in existing_seeded_products:
            db.session.delete(product)

        db.session.flush()

        for index in range(1, PRODUCTS_PER_CATEGORY + 1):
            product_name = create_product_name(
                category_name,
                category_info["product_types"],
                index,
            )

            description = (
                f"{random.choice(DESCRIPTIONS)} "
                f"Part of the {category_name} collection. "
                f"{SEED_MARKER}"
            )

            product = Product(
                name=product_name,
                description=description,
                price=rounded_price(
                    category_info["price_range"][0],
                    category_info["price_range"][1],
                ),
                category_id=category.id,
            )

            db.session.add(product)
            created_products += 1

    db.session.commit()

    print("Dummy catalogue created successfully.")
    print(f"New categories created: {created_categories}")
    print(f"Dummy products created: {created_products}")
    print(
        f"Expected dummy total: "
        f"{len(CATEGORY_DATA) * PRODUCTS_PER_CATEGORY}"
    )


if __name__ == "__main__":
    with app.app_context():
        seed_products()