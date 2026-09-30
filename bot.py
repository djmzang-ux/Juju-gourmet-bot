import os
import sqlite3
import asyncio
from io import BytesIO
from datetime import datetime
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile, InlineKeyboardButton, CopyTextButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from dotenv import load_dotenv

import base64
import qrcode

try:
    import qrcode
except ImportError:
    qrcode = None

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB = os.getenv("DB_FILE", "juju_gourmet.db")

FRETE = 10.00
ATENDENTE = "djalmazang"
QR_FILE = "pix_qrcode.png"
PIX_QR_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAeoAAAHqAQAAAADjFjCXAAAEMElEQVR4nO2dTY6jMBCFXw1IWRqpD5CjwA3mSK0+0twAjpIDRLKXkUA1C5d/Qs8qZpSO8mqBCPDJjVQq86rKblE02PKrhQaIEydOnDhx4sSJH4uLWQ8s0gMI9jNeixbKDRGZjhud+Jvio6qqekAmbILlrKqzuwngVgDx2k1kQqeqqnqPN45O/E3xYOFLZwDyeRGRz8tJAWwiUzhVUreOfz/jjyf+Ynj/r4u6DN0KhE10+d0pENKNfHbM6MTfE997nQDdKnBXAdCtMl4EGOebYPQbZPxz6OjE3xNPXucUQAD2SePlbFfKjfqRl3534k/GFxERGQCZQg+Ml5Ni9ADGSw+ZwknTx90WJeyhoxN/MzzGujqQhU0AdxMsZ5Ov8dpyvonug+FLvzvxZ+GIeZDRd/GgMzoF0MVEis4AdM4/48O6xjOdX/rdiT8LN/eJKThnLmWTq+9UNXliydLpHJ+j1xF/1GqvS2HODjFB3Gn1SPZJxjriDWbu41YrUMxOVVVXpGtrnoTzhFseful3J/4sPKoJGf0GRfhYgdCvMs4AYsALHyrjbJljgbv2Ml5OKoeMTvw98TTDelSxDmWGjVNqOXgTF4x1xBusaNgoGqJU8IDp2vLB51LNf1SqCeItZrWJZYAonIfAbb0uA2BqIgwAnIci9Cvgrr0uwzWVNF763Yk/C6/VBJDTIr5LkiKl6oAYCVeTFNSwxB+3b6m6LFrhdkI2nZnMpdcRf9SKh6UIZ05oCsOjdjPNmWN6HfFGXNWbaJUJgM5BrA4bv/CwSTmIDBur/8RbrGROTMPC8sAprgGo6xUlkcxYR/xRSw5UvtzyDKsr7OMuPpcFB6gmiDdZ9V1nluSrxj4UwLRGTt/lM3od8cdsX5vQ1PNUhzmfDrn7hLGOeINZrANQBKqlSu47nWagKosx1hFvMAtaRSoAiGHu3uFM5qYCLWMd8Qar58tduTW5WRSt5n+lLYBeR/xBu1uZ6K6yW0GhACCAQOGuomO833HtP/EWq9REtVrC1Y0nllLxqNpNGOuIN1idJXa1S9n9JGRTWTYl8uh1xBtxmQAAQcT2dMImqQ+lU/n0ABBOGpfHipw4wxJvsUpIVD0nvvR35rNUqojGWEf8cYv5OsvD3YnW3HNS1ihGhLUJ4m14nTmxfHFyqeyOpeezNLQzX0e8wUptArtu4Tl1daZ6WQqHuQ+PXke8BR9z+mRME6lpCJjW0K8hr8x2N/bXET8AT3t1yhTypsNxPWwfWzvl89LHvZ+imj10dOLvjVer++PmsC6tgv0aNomfeV9nxjriR+IypXKXfsnJUirLkDrtlqFTmdCpTP9jdOLvgX/bq3MZOtgc6jwE6Fddps02jAW2XpffeRu7l3534s/C9xq2anLK6ePU81SmXubriLdY1WTygPG/1xEnTpw4ceLEif8U/C9I5iPW6OlBawAAAABJRU5ErkJggg=="

if not TOKEN:
    raise RuntimeError("BOT_TOKEN não configurado")

bot = Bot(TOKEN)
dp = Dispatcher()

PRODUCTS = [
    ("CÃ©u Azul", 10),
    ("Chocolate", 10),
    ("Coco Branco", 10),
    ("Coco Queimado", 10),
    ("Ferrero Rocher c/ Nutella", 10),
    ("LimÃ£o", 10),
    ("Leite Condensado", 10),
    ("Leite Ninho c/ Nutella", 10),
    ("MaracujÃ¡", 10),
    ("MaracujÃ¡ c/ Nutella", 10),
    ("Oreo", 10),
    ("Ovomaltine", 10),
    ("Pudim", 10),
    ("PaÃ§oca", 10),
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
    ("Trufa PaÃ§oca", 10),
    ("Pastel de Ninho com Nutella", 12),
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
    k.button(text="ð Produtos")
    k.button(text="ð Meu carrinho")
    k.button(text="ð¦ Meus pedidos")
    k.button(text="ð PromoÃ§Ãµes")
    k.button(text="ð¬ Falar com atendente")
    k.adjust(2, 2, 1)
    return k.as_markup(resize_keyboard=True)


def start_kb():
    k = InlineKeyboardBuilder()
    k.button(text="ð Ver produtos", callback_data="products")
    k.button(text="ð° Outras delÃ­cias", callback_data="other")
    k.button(text="ð Meu carrinho", callback_data="cart")
    k.button(
        text="ð¬ Falar com atendente",
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
    outras = {
        "Trufa Ninho com Nutella",
        "Trufa Ninho com Ovomaltine",
        "Trufa PaÃ§oca",
        "Pastel de Ninho com Nutella",
    }

    # As trufas e o pastel ficam na aba "Outras delÃ­cias".
    for product_id, name, price in rows:
        if name in outras:
            continue
        k.button(
            text=f"{name} â R$ {price:.2f}",
            callback_data=f"add:{product_id}",
        )

    k.button(text="ð° Outras delÃ­cias", callback_data="other")
    k.button(text="ð  Voltar ao inÃ­cio", callback_data="home")
    k.adjust(1)
    return k.as_markup()


def other_kb():
    c = conn()
    nomes = (
        "Trufa Ninho com Nutella",
        "Trufa Ninho com Ovomaltine",
        "Trufa PaÃ§oca",
        "Pastel de Ninho com Nutella",
    )
    placeholders = ",".join("?" for _ in nomes)
    rows = c.execute(
        f"SELECT id,name,price FROM products WHERE name IN ({placeholders}) ORDER BY id",
        nomes,
    ).fetchall()
    c.close()

    k = InlineKeyboardBuilder()
    for product_id, name, price in rows:
        k.button(
            text=f"{name} â R$ {price:.2f}",
            callback_data=f"add:{product_id}",
        )

    k.button(text="ð Ver carrinho", callback_data="cart")
    k.button(text="ð Continuar comprando", callback_data="products")
    k.button(text="ð  Voltar ao inÃ­cio", callback_data="home")
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
    k.button(text="â Finalizar pedido", callback_data="checkout")
    k.button(text="ð Continuar comprando", callback_data="products")
    k.button(text="ð Limpar carrinho", callback_data="clear")
    k.adjust(1)
    return k.as_markup()


def delivery_kb():
    k = InlineKeyboardBuilder()
    k.button(text="ð Entrega â R$ 10,00", callback_data="delivery")
    k.button(text="ð  Retirada â GRÃTIS", callback_data="pickup")
    k.adjust(1)
    return k.as_markup()


def payment_kb():
    k = InlineKeyboardBuilder()
    k.button(
        text="ð¬ Enviar comprovante ao atendente",
        url=f"https://t.me/{ATENDENTE}",
    )
    k.button(text="ð Fazer novo pedido", callback_data="products")
    k.adjust(1)
    return k.as_markup()


def pix_tlv(tag, value):
    value = str(value)
    return f"{tag}{len(value):02d}{value}"


def pix_crc16(payload):
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def pix_payload_com_valor(total):
    merchant_account = (
        pix_tlv("00", "br.gov.bcb.pix")
        + pix_tlv("01", "+5517997771508")
    )
    payload = (
        pix_tlv("00", "01")
        + pix_tlv("01", "11")
        + pix_tlv("26", merchant_account)
        + pix_tlv("52", "0000")
        + pix_tlv("53", "986")
        + pix_tlv("54", f"{total:.2f}")
        + pix_tlv("58", "BR")
        + pix_tlv("59", "PEDRO HENRIQUE DE MATOS Z")
        + pix_tlv("60", "SAO PAULO")
        + pix_tlv("62", pix_tlv("05", "***"))
    )
    return payload + "6304" + pix_crc16(payload + "6304")



async def show_products_message(target):
    await target.answer(
        "ð« <b>Escolha o sabor:</b>\n\n"
        "Todos os produtos estÃ£o por <b>R$ 10,00</b>.",
        parse_mode="HTML",
        reply_markup=prod_kb(),
    )


async def show_cart_message(target, user_id=None):
    # Em callbacks do Telegram, target.message pertence ao bot.
    # Por isso usamos query.from_user.id quando o carrinho Ã© aberto por botÃ£o.
    if user_id is None:
        user_id = target.from_user.id

    rows, subtotal = cart_data(user_id)

    if not rows:
        k = InlineKeyboardBuilder()
        k.button(text="ð Ver produtos", callback_data="products")
        await target.answer(
            "ð Seu carrinho estÃ¡ vazio.\n\n"
            "Escolha seus produtos para comeÃ§ar.",
            reply_markup=k.as_markup(),
        )
        return

    text = "ð <b>Seu carrinho:</b>\n\n"
    for name, price, qty in rows:
        text += f"â¢ {qty}x {escape(name)} â R$ {price * qty:.2f}\n"

    text += f"\nð° <b>Subtotal: R$ {subtotal:.2f}</b>"
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
        "ð« <b>Juju Gourmet</b>\n\n"
        "Bem-vindo!👋🏻\n"
        "FaÃ§a seu pedido de forma rÃ¡pida pelo botÃ£o abaixo.\n\n"
        "Escolha os produtos â confira o carrinho â escolha "
        "entrega ou retirada â pague pelo Pix.",
        parse_mode="HTML",
        reply_markup=start_kb(),
    )


@dp.message(F.text == "ð Produtos")
@dp.message(Command("produtos"))
async def products(message: Message):
    await show_products_message(message)


@dp.callback_query(F.data == "products")
async def products_cb(query: CallbackQuery):
    await query.answer()
    await show_products_message(query.message)


@dp.callback_query(F.data == "other")
async def other_cb(query: CallbackQuery):
    await query.answer()
    await query.message.answer(
        "ð° <b>Outras delÃ­cias:</b>\n\nEscolha uma opÃ§Ã£o abaixo.",
        parse_mode="HTML",
        reply_markup=other_kb(),
    )


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
        await query.answer("Produto nÃ£o encontrado.", show_alert=True)
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

    # O botÃ£o de carrinho aparece depois da escolha do produto,
    # e nÃ£o abaixo da lista de sabores.
    k = InlineKeyboardBuilder()
    k.button(text="ð Ver carrinho", callback_data="cart")
    k.button(text="â Continuar comprando", callback_data="products")
    k.adjust(1)

    await query.message.answer(
        f"â <b>{escape(name)}</b> adicionado ao carrinho.\n"
        f"Valor: R$ {price:.2f}",
        parse_mode="HTML",
        reply_markup=k.as_markup(),
    )


@dp.message(F.text == "ð Meu carrinho")
@dp.message(Command("carrinho"))
async def cart(message: Message):
    await show_cart_message(message)


@dp.callback_query(F.data == "cart")
async def cart_cb(query: CallbackQuery):
    await query.answer()
    # O usuÃ¡rio correto Ã© query.from_user.id, e nÃ£o query.message.from_user.id.
    await show_cart_message(query.message, user_id=query.from_user.id)


@dp.callback_query(F.data == "clear")
async def clear(query: CallbackQuery):
    c = conn()
    c.execute("DELETE FROM cart WHERE user_id=?", (query.from_user.id,))
    c.commit()
    c.close()

    await query.answer("Carrinho limpo!")
    k = InlineKeyboardBuilder()
    k.button(text="ð Ver produtos", callback_data="products")
    await query.message.answer(
        "ð Carrinho limpo.\n\nVocÃª pode escolher os produtos novamente.",
        reply_markup=k.as_markup(),
    )


@dp.callback_query(F.data == "checkout")
async def checkout(query: CallbackQuery):
    rows, subtotal = cart_data(query.from_user.id)

    if not rows:
        await query.answer("Seu carrinho estÃ¡ vazio.", show_alert=True)
        return

    pending[query.from_user.id] = {
        "subtotal": subtotal,
        "delivery": None,
    }

    await query.answer()
    await query.message.answer(
        f"ð¦ <b>Subtotal do pedido: R$ {subtotal:.2f}</b>\n\n"
        "Como vocÃª deseja receber seu pedido?",
        parse_mode="HTML",
        reply_markup=delivery_kb(),
    )


@dp.callback_query(F.data == "delivery")
async def delivery(query: CallbackQuery):
    data = pending.get(query.from_user.id)

    if not data:
        await query.answer(
            "Vamos comeÃ§ar o pedido novamente.",
            show_alert=True,
        )
        return

    data["delivery"] = True
    await query.answer()
    await query.message.answer(
        "ð <b>Entrega selecionada</b>\n\n"
        "Taxa de entrega: <b>R$ 10,00</b>\n\n"
        "Agora envie seu endereÃ§o completo.",
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "pickup")
async def pickup(query: CallbackQuery):
    data = pending.get(query.from_user.id)

    if not data:
        await query.answer(
            "Vamos comeÃ§ar o pedido novamente.",
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
            "NÃ£o encontrei um pedido pendente. "
            "Volte aos produtos e tente novamente."
        )
        return

    rows, subtotal = cart_data(user.id)

    if not rows:
        await message.answer("Seu carrinho estÃ¡ vazio.")
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

    # Pagamento em trÃªs partes: dados do Pix, QR Code e copia e cola.
    # Gera um Pix copia e cola especÃ­fico deste pedido, com o valor jÃ¡ preenchido.
    pix_code = pix_payload_com_valor(total)

    await message.answer(
        f"â <b>Pedido #{order_id} criado!</b>\n\n"
        f"ð« {escape(items)}\n"
        f"ð° Total: <b>R$ {total:.2f}</b>\n"
        f"ð {'Entrega: ' + escape(address) if is_delivery else 'Retirada no local'}",
        parse_mode="HTML",
    )

    # Primeiro enviamos o pagamento em TEXTO. Assim, mesmo que o QR Code
    # ou algum recurso visual dÃª erro, o cliente sempre recebe o Pix.
    copy_k = InlineKeyboardBuilder()
    try:
        copy_k.add(
            InlineKeyboardButton(
                text="ð Copiar Pix copia e cola",
                copy_text=CopyTextButton(text=pix_code),
            )
        )
    except Exception as exc:
        print(f"Aviso: botÃ£o de copiar nÃ£o pÃ´de ser criado: {exc}")

    copy_k.button(
        text="ð¬ Enviar comprovante ao atendente",
        url=f"https://t.me/{ATENDENTE}",
    )
    copy_k.button(text="ð Fazer novo pedido", callback_data="products")
    copy_k.adjust(1)

    await message.answer(
        f"ð³ <b>Pagamento do pedido #{order_id}</b>\n\n"
        f"ð° <b>Total a pagar: R$ {total:.2f}</b>\n\n"
        f"ð <b>Pix copia e cola:</b>\n"
        f"<code>{escape(pix_code)}</code>\n\n"
        f"ð° <b>Valor jÃ¡ incluÃ­do: R$ {total:.2f}</b>\n\n"
        "Use o botÃ£o abaixo para copiar o Pix.",
        parse_mode="HTML",
        reply_markup=copy_k.as_markup(),
    )

    # Depois tentamos enviar o QR Code. Se houver qualquer problema, o
    # pagamento em texto acima continua disponÃ­vel.
    if qrcode is not None:
        try:
            qr_image = qrcode.make(pix_code)
            qr_buffer = BytesIO()
            qr_image.save(qr_buffer, format="PNG")
            qr_buffer.seek(0)
            await message.answer_photo(
                BufferedInputFile(
                    qr_buffer.getvalue(),
                    filename=f"pix_pedido_{order_id}.png",
                ),
                caption=(
                    f"ð· <b>QR Code do Pix</b>\n"
                    f"Pedido #{order_id}\n"
                    f"ð° Valor jÃ¡ preenchido: <b>R$ {total:.2f}</b>\n\n"
                    "Escaneie o QR Code para pagar."
                ),
                parse_mode="HTML",
            )
        except Exception as exc:
            print(f"Aviso: QR Code nÃ£o pÃ´de ser enviado: {exc}")
            await message.answer(
                "â ï¸ NÃ£o consegui enviar a imagem do QR Code, mas o Pix copia e cola acima estÃ¡ pronto para pagamento.",
                parse_mode="HTML",
            )
    else:
        await message.answer(
            "â ï¸ A biblioteca do QR Code nÃ£o estÃ¡ instalada, mas o Pix copia e cola acima estÃ¡ pronto para pagamento.",
            parse_mode="HTML",
        )

    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"ð <b>Novo pedido #{order_id}</b>\n\n"
                f"Cliente: @{escape(user.username or 'sem usuÃ¡rio')}\n"
                f"Itens: {escape(items)}\n"
                f"Total: R$ {total:.2f}\n"
                f"Entrega/retirada: {escape(address)}",
                parse_mode="HTML",
            )
        except Exception as exc:
            print(f"NÃ£o foi possÃ­vel avisar o administrador: {exc}")


@dp.message(F.text == "ð¦ Meus pedidos")
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
        await message.answer("ð¦ VocÃª ainda nÃ£o fez nenhum pedido.")
        return

    text = "ð¦ <b>Seus pedidos:</b>\n\n"
    text += "\n".join(
        f"#{order_id} â R$ {total:.2f} â {escape(status)}"
        for order_id, total, status in rows
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "ð PromoÃ§Ãµes")
async def promos(message: Message):
    k = InlineKeyboardBuilder()
    k.button(text="ð¬ Falar com atendente", url=f"https://t.me/{ATENDENTE}")
    await message.answer(
        "ð <b>PromoÃ§Ãµes</b>\n\n"
        "Consulte as promoÃ§Ãµes disponÃ­veis com o atendente.",
        parse_mode="HTML",
        reply_markup=k.as_markup(),
    )


@dp.message(F.text == "ð¬ Falar com atendente")
async def atend(message: Message):
    k = InlineKeyboardBuilder()
    k.button(text="ð¬ Abrir atendente", url=f"https://t.me/{ATENDENTE}")
    await message.answer(
        "ð¬ <b>Falar com atendente</b>\n\n"
        "Clique no botÃ£o abaixo para abrir o Telegram do atendente.",
        parse_mode="HTML",
        reply_markup=k.as_markup(),
    )


@dp.callback_query(F.data == "home")
async def home(query: CallbackQuery):
    await query.answer()
    await query.message.answer(
        "ð« <b>Juju Gourmet</b>\n\nEscolha uma opÃ§Ã£o:",
        parse_mode="HTML",
        reply_markup=start_kb(),
    )


@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("â Acesso nÃ£o autorizado.")
        return

    await message.answer(
        "ð <b>Painel administrativo</b>\n\n"
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
        await message.answer("ð¦ Nenhum pedido ainda.")
        return

    for order_id, username, items, total, address, status in rows:
        await message.answer(
            f"ð¦ <b>Pedido #{order_id}</b>\n"
            f"Cliente: @{escape(username or 'sem usuÃ¡rio')}\n"
            f"Itens: {escape(items)}\n"
            f"Total: R$ {total:.2f}\n"
            f"EndereÃ§o: {escape(address)}\n"
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
        f"ð <b>EstatÃ­sticas</b>\n\n"
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
        f"{product_id} â {escape(name)} â R$ {price:.2f}"
        for product_id, name, price in rows
    )
    await message.answer(
        f"ð <b>Produtos</b>\n\n{text}",
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
                "ð Por favor, envie um endereÃ§o mais completo."
            )
            return

        await finish_order(
            message,
            message.from_user,
            address=address_text,
        )


async def main():
    conn().close()
    print("Juju Gourmet Bot iniciado")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
