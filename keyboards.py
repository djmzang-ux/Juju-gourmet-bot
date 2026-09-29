from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍️ Ver produtos"), KeyboardButton(text="🛒 Meu carrinho")],
            [KeyboardButton(text="🔥 Promoções"), KeyboardButton(text="📦 Meus pedidos")],
            [KeyboardButton(text="📍 Como receber"), KeyboardButton(text="💬 Falar com atendente")],
        ],
        resize_keyboard=True
    )

def product_keyboard(product_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Adicionar ao carrinho", callback_data=f"add:{product_id}")],
    ])

def cart_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Adicionar produtos", callback_data="catalog")],
        [InlineKeyboardButton(text="🗑️ Limpar carrinho", callback_data="cart_clear")],
        [InlineKeyboardButton(text="✅ Finalizar pedido", callback_data="checkout")],
    ])

def fulfillment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛵 Entrega", callback_data="fulfillment:delivery")],
        [InlineKeyboardButton(text="🏪 Retirada", callback_data="fulfillment:pickup")],
    ])

def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Pagar com Pix", callback_data="pay:pix")],
        [InlineKeyboardButton(text="💵 Pagar na entrega", callback_data="pay:cash")],
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Produtos", callback_data="admin:products")],
        [InlineKeyboardButton(text="🛒 Pedidos", callback_data="admin:orders")],
        [InlineKeyboardButton(text="📊 Estatísticas", callback_data="admin:stats")],
        [InlineKeyboardButton(text="➕ Novo produto", callback_data="admin:addproduct")],
    ])

def order_status_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍🍳 Preparando", callback_data=f"status:{order_id}:preparing")],
        [InlineKeyboardButton(text="🛵 Saiu para entrega", callback_data=f"status:{order_id}:out_for_delivery")],
        [InlineKeyboardButton(text="✅ Entregue", callback_data=f"status:{order_id}:delivered")],
    ])
