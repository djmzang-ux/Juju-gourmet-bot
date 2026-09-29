import os
import sqlite3
import asyncio
from datetime import datetime
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from dotenv import load_dotenv

try:
    import qrcode
except ImportError:
    qrcode = None

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB = os.getenv("DB_FILE", "juju_gourmet.db")

PIX_KEY = "17 99777-1508"
PIX_NAME = "Pedro Henrique de Matos"
PIX_COPIA_COLA = (
    "00020101021126360014br.gov.bcb.pix0114+5517997771508"
    "5204000053039865802BR5925PEDRO HENRIQUE DE MATOS Z"
    "6009SAO PAULO622905251M3QFQHD2A4QEQG9D9MJP9NTQ63047A93"
)
FRETE = 10.00
ATENDENTE = "djalmazang"
QR_FILE = "pix_qrcode.png"

if not TOKEN:
    raise RuntimeError("BOT_TOKEN não configurado")

bot = Bot(TOKEN)
dp = Dispatcher()

PRODUCTS = [
    ("Céu Azul", 10),
    ("Chocolate", 10),
    ("Coco Branco", 10),
    ("Coco Queimado", 10),
    ("Ferrero Rocher c/ Nutella", 10),
    ("Limão", 10),
    ("Leite Condensado", 10),
    ("Leite Ninho c/ Nutella", 10),
    ("Maracujá", 10),
    ("Maracujá c/ Nutella", 10),
    ("Oreo", 10),
    ("Ovomaltine", 10),
    ("Pudim", 10),
    ("Paçoca", 10),
    ("Pistache", 10),
    ("Pistache c/ Nutella", 10),
    ("Chiclete Trufado", 10),
    ("Morango Trufado", 10),
    ("Morango do Amor", 10),
    ("Morango", 10),
    ("Morango c/ Nutella", 10),
    ("Fini Dentadura", 10),
    ("Trufa Ninho com Nutella", 10),
    ("Trufa Ninho com Ovomaltine", 10),
    ("Trufa Paçoca", 10),
]


def conn():
    c = sqlite3.connect(DB)
    c.execute(
        "CREATE TABLE IF NOT EXISTS products("
        "id INTEGER PRIMARY KEY,name TEXT UNIQUE,price REAL)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS cart("
        "user_id INTEGER,product_id INTEGER,qty INTEGER,"
        "PRIMARY KEY(user_id,product_id))"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS orders("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "user_id INTEGER,username TEXT,items TEXT,total REAL,"
        "address TEXT,status TEXT,created_at TEXT)"
    )

    for name, price in PRODUCTS:
        c.execute(
            "INSERT OR IGNORE INTO products(name,price) VALUES(?,?)",
            (name, price),
        )
        c.execute(
            "UPDATE products SET price=? WHERE name=?",
            (price, name),
        )

    c.commit()
    return c


def menu():
    k = ReplyKeyboardBuilder()
    k.button(text="🛍 Produtos")
    k.button(text="🛒 Meu carrinho")
    k.button(text="📦 Meus pedidos")
    k.button(text="🎁 Promoções")
    k.button(text="💬 Falar com atendente")
    k.adjust(2, 2, 1)
    return k.as_markup(resize_keyboard=True)


def start_kb():
    k = InlineKeyboardBuilder()
    k.button(text="🛍 Ver produtos", callback_data="products")
    k.button(text="🛒 Meu carrinho", callback_data="cart")
    k.button(
        text="💬 Falar com atendente",
        url=f"https://t.me/{ATENDENTE}",
    )
    k.adjust(1)
    return k.as_markup()


def prod_kb():
    c = conn()
    rows = c.execute(
        "SELECT id,name,price FROM products ORDER BY id"
    ).fetchall()
    c.close()

    k = InlineKeyboardBuilder()

    # Não existe botão de carrinho abaixo da lista de sabores.
    for product_id, name, price in rows:
        k.button(
            text=f"{name} — R$ {price:.2f}",
            callback_data=f"add:{product_id}",
        )

    k.button(text="🏠 Voltar ao início", callback_data="home")
    k.adjust(1)
    return k.as_markup()


def cart_data(user_id):
    c = conn()
    rows = c.execute(
        "SELECT p.name,p.price,ca.qty "
        "FROM cart ca JOIN products p ON p.id=ca.product_id "
        "WHERE ca.user_id=?",
        (user_id,),
    ).fetchall()
    c.close()

    subtotal = sum(price * qty for _, price, qty in rows)
    return rows, subtotal


def cart_kb():
    k = InlineKeyboardBuilder()
    k.button(text="✅ Finalizar pedido", callback_data="checkout")
    k.button(text="🛍 Continuar comprando", callback_data="products")
    k.button(text="🗑 Limpar carrinho", callback_data="clear")
    k.adjust(1)
    return k.as_markup()


def delivery_kb():
    k = InlineKeyboardBuilder()
    k.button(text="🚚 Entrega — R$ 10,00", callback_data="delivery")
    k.button(text="🏠 Retirada — GRÁTIS", callback_data="pickup")
    k.adjust(1)
    return k.as_markup()


def payment_kb():
    k = InlineKeyboardBuilder()
    k.button(
        text="💬 Enviar comprovante ao atendente",
        url=f"https://t.me/{ATENDENTE}",
    )
    k.button(text="🛍 Fazer novo pedido", callback_data="products")
    k.adjust(1)
    return k.as_markup()


def ensure_qr():
    if os.path.exists(QR_FILE):
        return True

    if qrcode is None:
        print("AVISO: pacote qrcode não instalado.")
        return False

    img = qrcode.make(PIX_COPIA_COLA)
    img.save(QR_FILE)
    return True


async def show_products_message(target):
    await target.answer(
        "🍫 <b>Escolha o sabor:</b>\n\n"
        "Todos os produtos estão por <b>R$ 10,00</b>.",
        parse_mode="HTML",
        reply_markup=prod_kb(),
    )


async def show_cart_message(target, user_id=None):
    # Em callbacks do Telegram, target.message pertence ao bot.
    # Por isso usamos query.from_user.id quando o carrinho é aberto por botão.
    if user_id is None:
        user_id = target.from_user.id

    rows, subtotal = cart_data(user_id)

    if not rows:
        k = InlineKeyboardBuilder()
        k.button(text="🛍 Ver produtos", callback_data="products")
        await target.answer(
            "🛒 Seu carrinho está vazio.\n\n"
            "Escolha seus produtos para começar.",
            reply_markup=k.as_markup(),
        )
        return

    text = "🛒 <b>Seu carrinho:</b>\n\n"
    for name, price, qty in rows:
        text += f"• {qty}x {escape(name)} — R$ {price * qty:.2f}\n"

    text += f"\n💰 <b>Subtotal: R$ {subtotal:.2f}</b>"
    text += "\n\nClique em <b>Finalizar pedido</b> para escolher entrega ou retirada."

    await target.answer(
        text,
        parse_mode="HTML",
        reply_markup=cart_kb(),
    )


def create_order(user_id, username, items, total, address):
    c = conn()
    cur = c.execute(
        "INSERT INTO orders("
        "user_id,username,items,total,address,status,created_at"
        ") VALUES(?,?,?,?,?,?,?)",
        (
            user_id,
            username,
            items,
            total,
            address,
            "Aguardando pagamento",
            datetime.now().isoformat(timespec="minutes"),
        ),
    )
    order_id = cur.lastrowid
    c.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
    c.commit()
    c.close()
    return order_id


pending = {}


@dp.message(Command("start"))
async def start(message: Message):
    conn().close()
    await message.answer(
        "🍫 <b>Juju Gourmet</b>\n\n"
        "Bem-vindo! 👋\n"
        "Faça seu pedido de forma rápida pelo botão abaixo.\n\n"
        "Escolha os produtos → confira o carrinho → escolha "
        "entrega ou retirada → pague pelo Pix.",
        parse_mode="HTML",
        reply_markup=start_kb(),
    )


@dp.message(F.text == "🛍 Produtos")
@dp.message(Command("produtos"))
async def products(message: Message):
    await show_products_message(message)


@dp.callback_query(F.data == "products")
async def products_cb(query: CallbackQuery):
    await query.answer()
    await show_products_message(query.message)


@dp.callback_query(F.data.startswith("add:"))
async def add(query: CallbackQuery):
    product_id = int(query.data.split(":")[1])

    c = conn()
    row = c.execute(
        "SELECT name,price FROM products WHERE id=?",
        (product_id,),
    ).fetchone()

    if not row:
        c.close()
        await query.answer("Produto não encontrado.", show_alert=True)
        return

    name, price = row

    c.execute(
        "INSERT INTO cart(user_id,product_id,qty) VALUES(?,?,1) "
        "ON CONFLICT(user_id,product_id) DO UPDATE SET qty=qty+1",
        (query.from_user.id, product_id),
    )
    c.commit()
    c.close()

    await query.answer(f"{name} adicionado!")

    # O botão de carrinho aparece depois da escolha do produto,
    # e não abaixo da lista de sabores.
    k = InlineKeyboardBuilder()
    k.button(text="🛒 Ver carrinho", callback_data="cart")
    k.button(text="➕ Continuar comprando", callback_data="products")
    k.adjust(1)

    await query.message.answer(
        f"✅ <b>{escape(name)}</b> adicionado ao carrinho.\n"
        f"Valor: R$ {price:.2f}",
        parse_mode="HTML",
        reply_markup=k.as_markup(),
    )


@dp.message(F.text == "🛒 Meu carrinho")
@dp.message(Command("carrinho"))
async def cart(message: Message):
    await show_cart_message(message)


@dp.callback_query(F.data == "cart")
async def cart_cb(query: CallbackQuery):
    await query.answer()
    # O usuário correto é query.from_user.id, e não query.message.from_user.id.
    await show_cart_message(query.message, user_id=query.from_user.id)


@dp.callback_query(F.data == "clear")
async def clear(query: CallbackQuery):
    c = conn()
    c.execute("DELETE FROM cart WHERE user_id=?", (query.from_user.id,))
    c.commit()
    c.close()

    await query.answer("Carrinho limpo!")
    k = InlineKeyboardBuilder()
    k.button(text="🛍 Ver produtos", callback_data="products")
    await query.message.answer(
        "🛒 Carrinho limpo.\n\nVocê pode escolher os produtos novamente.",
        reply_markup=k.as_markup(),
    )


@dp.callback_query(F.data == "checkout")
async def checkout(query: CallbackQuery):
    rows, subtotal = cart_data(query.from_user.id)

    if not rows:
        await query.answer("Seu carrinho está vazio.", show_alert=True)
        return

    pending[query.from_user.id] = {
        "subtotal": subtotal,
        "delivery": None,
    }

    await query.answer()
    await query.message.answer(
        f"📦 <b>Subtotal do pedido: R$ {subtotal:.2f}</b>\n\n"
        "Como você deseja receber seu pedido?",
        parse_mode="HTML",
        reply_markup=delivery_kb(),
    )


@dp.callback_query(F.data == "delivery")
async def delivery(query: CallbackQuery):
    data = pending.get(query.from_user.id)

    if not data:
        await query.answer(
            "Vamos começar o pedido novamente.",
            show_alert=True,
        )
        return

    data["delivery"] = True
    await query.answer()
    await query.message.answer(
        "🚚 <b>Entrega selecionada</b>\n\n"
        "Taxa de entrega: <b>R$ 10,00</b>\n\n"
        "Agora envie seu endereço completo.",
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "pickup")
async def pickup(query: CallbackQuery):
    data = pending.get(query.from_user.id)

    if not data:
        await query.answer(
            "Vamos começar o pedido novamente.",
            show_alert=True,
        )
        return

    data["delivery"] = False
    await query.answer()

    await finish_order(
        query.message,
        query.from_user,
        address="RETIRADA",
    )


async def finish_order(message, user, address):
    data = pending.pop(user.id, None)

    if not data:
        await message.answer(
            "Não encontrei um pedido pendente. "
            "Volte aos produtos e tente novamente."
        )
        return

    rows, subtotal = cart_data(user.id)

    if not rows:
        await message.answer("Seu carrinho está vazio.")
        return

    is_delivery = data["delivery"] is True
    fee = FRETE if is_delivery else 0.0
    total = subtotal + fee

    items = ", ".join(
        f"{qty}x {name}" for name, price, qty in rows
    )

    order_id = create_order(
        user_id=user.id,
        username=user.username or "",
        items=items,
        total=total,
        address=address,
    )

    payment_text = (
        f"💳 <b>Pagamento do pedido #{order_id}</b>\n\n"
        f"🍫 Produtos: R$ {subtotal:.2f}\n"
        f"{'🚚 Entrega' if is_delivery else '🏠 Retirada'}: R$ {fee:.2f}\n"
        f"💰 <b>Total a pagar: R$ {total:.2f}</b>\n\n"
        f"🔑 <b>Pix:</b> {escape(PIX_KEY)}\n"
        f"👤 <b>Nome:</b> {escape(PIX_NAME)}\n\n"
        f"📋 <b>Pix copia e cola:</b>\n"
        f"<code>{escape(PIX_COPIA_COLA)}</code>\n\n"
        "Você também pode escanear o QR Code abaixo.\n"
        "Depois do pagamento, envie o comprovante ao atendente."
    )

    await message.answer(
        f"✅ <b>Pedido #{order_id} criado!</b>\n\n"
        f"🍫 {escape(items)}\n"
        f"💰 Total: <b>R$ {total:.2f}</b>\n"
        f"📍 {'Entrega: ' + escape(address) if is_delivery else 'Retirada no local'}",
        parse_mode="HTML",
    )

    if ensure_qr():
        await message.answer_photo(
            FSInputFile(QR_FILE),
            caption=payment_text,
            parse_mode="HTML",
            reply_markup=payment_kb(),
        )
    else:
        await message.answer(
            payment_text,
            parse_mode="HTML",
            reply_markup=payment_kb(),
        )

    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔔 <b>Novo pedido #{order_id}</b>\n\n"
                f"Cliente: @{escape(user.username or 'sem usuário')}\n"
                f"Itens: {escape(items)}\n"
                f"Total: R$ {total:.2f}\n"
                f"Entrega/retirada: {escape(address)}",
                parse_mode="HTML",
            )
        except Exception as exc:
            print(f"Não foi possível avisar o administrador: {exc}")


@dp.message(F.text == "📦 Meus pedidos")
@dp.message(Command("meuspedidos"))
async def orders(message: Message):
    c = conn()
    rows = c.execute(
        "SELECT id,total,status FROM orders "
        "WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (message.from_user.id,),
    ).fetchall()
    c.close()

    if not rows:
        await message.answer("📦 Você ainda não fez nenhum pedido.")
        return

    text = "📦 <b>Seus pedidos:</b>\n\n"
    text += "\n".join(
        f"#{order_id} — R$ {total:.2f} — {escape(status)}"
        for order_id, total, status in rows
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🎁 Promoções")
async def promos(message: Message):
    k = InlineKeyboardBuilder()
    k.button(text="💬 Falar com atendente", url=f"https://t.me/{ATENDENTE}")
    await message.answer(
        "🎁 <b>Promoções</b>\n\n"
        "Consulte as promoções disponíveis com o atendente.",
        parse_mode="HTML",
        reply_markup=k.as_markup(),
    )


@dp.message(F.text == "💬 Falar com atendente")
async def atend(message: Message):
    k = InlineKeyboardBuilder()
    k.button(text="💬 Abrir atendente", url=f"https://t.me/{ATENDENTE}")
    await message.answer(
        "💬 <b>Falar com atendente</b>\n\n"
        "Clique no botão abaixo para abrir o Telegram do atendente.",
        parse_mode="HTML",
        reply_markup=k.as_markup(),
    )


@dp.callback_query(F.data == "home")
async def home(query: CallbackQuery):
    await query.answer()
    await query.message.answer(
        "🍫 <b>Juju Gourmet</b>\n\nEscolha uma opção:",
        parse_mode="HTML",
        reply_markup=start_kb(),
    )


@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Acesso não autorizado.")
        return

    await message.answer(
        "👑 <b>Painel administrativo</b>\n\n"
        "/pedidos\n/stats\n/produtos_admin",
        parse_mode="HTML",
    )


@dp.message(Command("pedidos"))
async def admin_orders(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    c = conn()
    rows = c.execute(
        "SELECT id,username,items,total,address,status "
        "FROM orders ORDER BY id DESC LIMIT 20"
    ).fetchall()
    c.close()

    if not rows:
        await message.answer("📦 Nenhum pedido ainda.")
        return

    for order_id, username, items, total, address, status in rows:
        await message.answer(
            f"📦 <b>Pedido #{order_id}</b>\n"
            f"Cliente: @{escape(username or 'sem usuário')}\n"
            f"Itens: {escape(items)}\n"
            f"Total: R$ {total:.2f}\n"
            f"Endereço: {escape(address)}\n"
            f"Status: {escape(status)}",
            parse_mode="HTML",
        )


@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    c = conn()
    count, total = c.execute(
        "SELECT COUNT(*),COALESCE(SUM(total),0) FROM orders"
    ).fetchone()
    c.close()

    await message.answer(
        f"📊 <b>Estatísticas</b>\n\n"
        f"Pedidos: {count}\n"
        f"Faturamento: R$ {total:.2f}",
        parse_mode="HTML",
    )


@dp.message(Command("produtos_admin"))
async def admin_products(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    c = conn()
    rows = c.execute(
        "SELECT id,name,price FROM products ORDER BY id"
    ).fetchall()
    c.close()

    text = "\n".join(
        f"{product_id} — {escape(name)} — R$ {price:.2f}"
        for product_id, name, price in rows
    )
    await message.answer(
        f"📋 <b>Produtos</b>\n\n{text}",
        parse_mode="HTML",
    )


@dp.message(F.text)
async def address(message: Message):
    data = pending.get(message.from_user.id)

    if not data:
        return

    if data["delivery"] is True:
        address_text = message.text.strip()

        if len(address_text) < 5:
            await message.answer(
                "📍 Por favor, envie um endereço mais completo."
            )
            return

        await finish_order(
            message,
            message.from_user,
            address=address_text,
        )


async def main():
    conn().close()
    ensure_qr()
    print("Juju Gourmet Bot iniciado")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
