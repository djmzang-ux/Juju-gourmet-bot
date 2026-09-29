from decimal import Decimal
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from ..db import SessionLocal
from ..models import User, Product, Order, OrderItem
from ..config import settings
from ..keyboards import main_menu, product_keyboard, cart_keyboard, fulfillment_keyboard, payment_keyboard

router = Router()

# Carrinho em memória por usuário para manter o MVP simples.
# Em produção de múltiplas instâncias, mover para Redis/DB.
carts: dict[int, dict[int, int]] = {}
checkout_state: dict[int, dict] = {}

async def get_or_create_user(message: Message):
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=message.from_user.id, name=message.from_user.full_name)
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

@router.message(CommandStart())
async def start(message: Message):
    await get_or_create_user(message)
    await message.answer(
        f"🍫 Bem-vindo à {settings.store_name}!\n\nEscolha uma opção:",
        reply_markup=main_menu()
    )

@router.message(F.text == "🛍️ Ver produtos")
async def catalog(message: Message):
    async with SessionLocal() as db:
        result = await db.execute(select(Product).where(Product.active == True).order_by(Product.name))
        products = result.scalars().all()
    if not products:
        await message.answer("No momento não há produtos disponíveis.")
        return
    await message.answer("🍫 *CATÁLOGO*", parse_mode="Markdown")
    for p in products:
        text = (
            f"🍫 *{p.name}*\n"
            f"{p.description or ''}\n"
            f"💰 R$ {Decimal(p.price):.2f}\n"
            f"📦 Disponível: {p.stock}"
        )
        if p.stock > 0:
            await message.answer(text, parse_mode="Markdown", reply_markup=product_keyboard(p.id))
        else:
            await message.answer(text + "\n\n⚫ ESGOTADO", parse_mode="Markdown")

@router.callback_query(F.data == "catalog")
async def catalog_callback(call: CallbackQuery):
    await call.answer()
    await catalog(call.message)

@router.callback_query(F.data.startswith("add:"))
async def add_product(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    async with SessionLocal() as db:
        p = await db.get(Product, pid)
        if not p or not p.active or p.stock <= 0:
            await call.answer("Produto indisponível.", show_alert=True)
            return
        user_cart = carts.setdefault(call.from_user.id, {})
        current = user_cart.get(pid, 0)
        if current >= p.stock:
            await call.answer("Quantidade máxima disponível atingida.", show_alert=True)
            return
        user_cart[pid] = current + 1
    await call.answer("Adicionado ao carrinho! 🛒")

@router.message(F.text == "🛒 Meu carrinho")
async def cart(message: Message):
    await send_cart(message)

async def send_cart(message: Message):
    cart_data = carts.get(message.from_user.id, {})
    if not cart_data:
        await message.answer("🛒 Seu carrinho está vazio.")
        return
    total = Decimal("0")
    lines = ["🛒 *SEU CARRINHO*\n"]
    async with SessionLocal() as db:
        for pid, qty in cart_data.items():
            p = await db.get(Product, pid)
            if not p:
                continue
            subtotal = Decimal(p.price) * qty
            total += subtotal
            lines.append(f"{qty}x {p.name} — R$ {subtotal:.2f}")
    lines.append(f"\n💰 *TOTAL: R$ {total:.2f}*")
    await message.answer("\n".join(lines), parse_mode="Markdown", reply_markup=cart_keyboard())

@router.callback_query(F.data == "cart_clear")
async def cart_clear(call: CallbackQuery):
    carts.pop(call.from_user.id, None)
    await call.answer("Carrinho limpo.")
    await call.message.edit_text("🛒 Carrinho vazio.")

@router.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery):
    if not carts.get(call.from_user.id):
        await call.answer("Seu carrinho está vazio.", show_alert=True)
        return
    checkout_state[call.from_user.id] = {}
    await call.answer()
    await call.message.answer(
        "📦 Como deseja receber seu pedido?",
        reply_markup=fulfillment_keyboard()
    )

@router.callback_query(F.data.startswith("fulfillment:"))
async def fulfillment(call: CallbackQuery):
    method = call.data.split(":")[1]
    checkout_state.setdefault(call.from_user.id, {})["fulfillment"] = method
    await call.answer()
    if method == "delivery":
        await call.message.answer("📍 Envie seu endereço completo (rua, número, bairro e referência):")
        checkout_state[call.from_user.id]["awaiting"] = "address"
    else:
        checkout_state[call.from_user.id]["address"] = "RETIRADA"
        await call.message.answer("📱 Envie seu telefone para contato:")
        checkout_state[call.from_user.id]["awaiting"] = "phone"

@router.message()
async def checkout_text(message: Message):
    state = checkout_state.get(message.from_user.id)
    if not state:
        return
    awaiting = state.get("awaiting")
    if awaiting == "address":
        state["address"] = message.text
        state["awaiting"] = "phone"
        await message.answer("📱 Agora envie seu telefone para contato:")
        return
    if awaiting == "phone":
        state["phone"] = message.text
        state["awaiting"] = None
        await show_order_summary(message)

async def show_order_summary(message: Message):
    uid = message.from_user.id
    cart_data = carts.get(uid, {})
    state = checkout_state.get(uid, {})
    subtotal = Decimal("0")
    lines = ["📋 *RESUMO DO PEDIDO*\n"]
    async with SessionLocal() as db:
        for pid, qty in cart_data.items():
            p = await db.get(Product, pid)
            if p:
                value = Decimal(p.price) * qty
                subtotal += value
                lines.append(f"{qty}x {p.name} — R$ {value:.2f}")
    delivery = settings.delivery_fee if state.get("fulfillment") == "delivery" else Decimal("0")
    total = subtotal + delivery
    lines += [
        f"\nProdutos: R$ {subtotal:.2f}",
        f"Entrega: R$ {delivery:.2f}",
        f"💰 *TOTAL: R$ {total:.2f}*",
        f"\n📍 {state.get('address')}",
        f"📱 {state.get('phone')}",
    ]
    # Use payment keyboard after summary.
    await message.answer("\n".join(lines), parse_mode="Markdown", reply_markup=payment_keyboard())

@router.callback_query(F.data == "pay:cash")
async def pay_cash(call: CallbackQuery):
    await create_order(call, payment_status="cash_on_delivery")

@router.callback_query(F.data == "pay:pix")
async def pay_pix(call: CallbackQuery):
    # MVP: creates order. Payment provider can be enabled via payments adapter.
    await create_order(call, payment_status="pending")

async def create_order(call: CallbackQuery, payment_status: str):
    uid = call.from_user.id
    cart_data = carts.get(uid, {})
    state = checkout_state.get(uid, {})
    if not cart_data:
        await call.answer("Carrinho vazio.", show_alert=True)
        return

    async with SessionLocal() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == uid))
        user = user_result.scalar_one()
        subtotal = Decimal("0")
        order = Order(
            user_id=user.id,
            status="pending_payment" if payment_status == "pending" else "confirmed",
            fulfillment=state.get("fulfillment", "delivery"),
            address=state.get("address"),
            phone=state.get("phone"),
            payment_status=payment_status,
        )
        db.add(order)
        await db.flush()

        for pid, qty in cart_data.items():
            p = await db.get(Product, pid)
            if not p or not p.active or p.stock < qty:
                await call.answer(f"Produto indisponível: {p.name if p else pid}", show_alert=True)
                await db.rollback()
                return
            subtotal += Decimal(p.price) * qty
            p.stock -= qty
            db.add(OrderItem(
                order_id=order.id,
                product_id=p.id,
                product_name=p.name,
                quantity=qty,
                unit_price=p.price,
            ))

        delivery = settings.delivery_fee if state.get("fulfillment") == "delivery" else Decimal("0")
        order.subtotal = subtotal
        order.delivery_fee = delivery
        order.total = subtotal + delivery
        await db.commit()
        order_id = order.id
        total = order.total

    carts.pop(uid, None)
    checkout_state.pop(uid, None)

    if payment_status == "cash_on_delivery":
        await call.message.answer(
            f"✅ *PEDIDO #{order_id} CONFIRMADO!*\n\n"
            f"💰 Total: R$ {Decimal(total):.2f}\n"
            f"💵 Pagamento: na entrega\n\n"
            "Seu pedido foi enviado para preparação.",
            parse_mode="Markdown"
        )
    else:
        await call.message.answer(
            f"💳 *PEDIDO #{order_id} CRIADO*\n\n"
            f"Valor: R$ {Decimal(total):.2f}\n\n"
            "O pagamento Pix automático deve ser conectado ao provedor configurado. "
            "No MVP, o pedido fica aguardando confirmação.",
            parse_mode="Markdown"
        )
