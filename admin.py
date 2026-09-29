from decimal import Decimal
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from ..db import SessionLocal
from ..models import Product, Order, OrderItem
from ..config import settings
from ..keyboards import admin_keyboard, order_status_keyboard

router = Router()
admin_state: dict[int, dict] = {}

def is_admin(user_id: int) -> bool:
    return user_id == settings.admin_telegram_id

@router.message(F.text == "/admin")
async def admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔐 Painel administrativo", reply_markup=admin_keyboard())

@router.callback_query(F.data == "admin:products")
async def admin_products(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.answer()
    async with SessionLocal() as db:
        result = await db.execute(select(Product).order_by(Product.id))
        products = result.scalars().all()
    if not products:
        await call.message.answer("Nenhum produto cadastrado.")
        return
    text = "📦 *PRODUTOS*\n\n" + "\n".join(
        f"#{p.id} {p.name} — R$ {Decimal(p.price):.2f} — estoque {p.stock} — {'🟢' if p.active else '⚫'}"
        for p in products
    )
    await call.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data == "admin:addproduct")
async def admin_add_product(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    admin_state[call.from_user.id] = {"step": "name"}
    await call.answer()
    await call.message.answer("Nome do produto:")

@router.message()
async def admin_flow(message: Message):
    if not is_admin(message.from_user.id):
        return
    state = admin_state.get(message.from_user.id)
    if not state:
        return
    step = state["step"]
    if step == "name":
        state["name"] = message.text
        state["step"] = "price"
        await message.answer("Preço (ex.: 6.00):")
    elif step == "price":
        try:
            state["price"] = Decimal(message.text.replace(",", "."))
        except Exception:
            await message.answer("Preço inválido. Ex.: 6.00")
            return
        state["step"] = "stock"
        await message.answer("Estoque inicial:")
    elif step == "stock":
        try:
            state["stock"] = int(message.text)
        except Exception:
            await message.answer("Estoque inválido.")
            return
        state["step"] = "description"
        await message.answer("Descrição (ou - para deixar vazia):")
    elif step == "description":
        async with SessionLocal() as db:
            p = Product(
                name=state["name"],
                price=state["price"],
                stock=state["stock"],
                description="" if message.text == "-" else message.text,
                category="Trufas",
                active=True,
            )
            db.add(p)
            await db.commit()
        admin_state.pop(message.from_user.id, None)
        await message.answer(f"✅ Produto '{state['name']}' criado.")

@router.callback_query(F.data == "admin:orders")
async def admin_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.answer()
    async with SessionLocal() as db:
        result = await db.execute(select(Order).order_by(Order.created_at.desc()).limit(10))
        orders = result.scalars().all()
    if not orders:
        await call.message.answer("Nenhum pedido.")
        return
    for o in orders:
        await call.message.answer(
            f"📦 Pedido #{o.id}\n"
            f"Status: {o.status}\n"
            f"Pagamento: {o.payment_status}\n"
            f"Total: R$ {Decimal(o.total):.2f}",
            reply_markup=order_status_keyboard(o.id)
        )

@router.callback_query(F.data.startswith("status:"))
async def update_status(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    _, oid, status = call.data.split(":")
    async with SessionLocal() as db:
        order = await db.get(Order, int(oid))
        if not order:
            await call.answer("Pedido não encontrado.", show_alert=True)
            return
        order.status = status
        await db.commit()
        telegram_id = order.user.telegram_id
    await call.answer("Status atualizado.")
    await call.message.edit_text(call.message.text + f"\n\n✅ Novo status: {status}")

    try:
        labels = {
            "preparing": "👨‍🍳 Seu pedido está sendo preparado!",
            "out_for_delivery": "🛵 Seu pedido saiu para entrega!",
            "delivered": "🎉 Seu pedido foi entregue! Obrigado pela compra ❤️",
        }
        await call.bot.send_message(telegram_id, f"📦 Pedido #{oid}\n\n{labels.get(status, status)}")
    except Exception:
        pass

@router.callback_query(F.data == "admin:stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    await call.answer()
    async with SessionLocal() as db:
        count = (await db.execute(select(func.count(Order.id)))).scalar_one()
        total = (await db.execute(select(func.coalesce(func.sum(Order.total), 0)))).scalar_one()
    await call.message.answer(f"📊 *ESTATÍSTICAS*\n\nPedidos: {count}\nVendas: R$ {Decimal(total):.2f}", parse_mode="Markdown")

@router.message(F.text == "/products")
async def products_command(message: Message):
    if is_admin(message.from_user.id):
        await admin_products(await _fake_callback_not_needed(message))

async def _fake_callback_not_needed(message):
    return None
