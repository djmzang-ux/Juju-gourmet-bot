import asyncio
from decimal import Decimal
from app.db import init_db, SessionLocal
from app.models import Product

PRODUCTS = [
    ("Céu Azul", 6, "Trufa de chocolate com recheio Céu Azul."),
    ("Chocolate", 6, "Trufa clássica de chocolate."),
    ("Coco Branco", 6, "Trufa de coco branco."),
    ("Coco Queimado", 6, "Trufa de coco queimado."),
    ("Ferrero Rocher c/ Nutella", 8, "Trufa especial de Ferrero Rocher com Nutella."),
    ("Limão", 6, "Trufa de limão."),
    ("Leite Condensado", 6, "Trufa de leite condensado."),
    ("Leite Ninho c/ Nutella", 7, "Trufa de Ninho com Nutella."),
    ("Maracujá", 6, "Trufa de maracujá."),
    ("Maracujá c/ Nutella", 7, "Trufa de maracujá com Nutella."),
    ("Oreo", 6, "Trufa de Oreo."),
    ("Ovomaltine", 6, "Trufa de Ovomaltine."),
    ("Pudim", 6, "Trufa sabor pudim."),
    ("Paçoca", 6, "Trufa de paçoca."),
    ("Pistache", 8, "Trufa de pistache."),
    ("Pistache c/ Nutella", 9, "Trufa de pistache com Nutella."),
    ("Chiclete Trufado", 6, "Trufa sabor chiclete."),
    ("Morango Trufado", 7, "Trufa de morango."),
    ("Morango do Amor", 8, "Morango do Amor."),
    ("Morango", 6, "Trufa de morango."),
    ("Morango c/ Nutella", 7, "Trufa de morango com Nutella."),
    ("Fini Dentadura", 6, "Trufa Fini Dentadura."),
]

async def main():
    await init_db()
    async with SessionLocal() as db:
        for name, price, description in PRODUCTS:
            p = Product(name=name, price=Decimal(str(price)), stock=100, description=description)
            db.add(p)
        await db.commit()
    print("Produtos cadastrados.")

if __name__ == "__main__":
    asyncio.run(main())
