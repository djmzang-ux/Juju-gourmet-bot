import os, sqlite3, asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
TOKEN=os.getenv('BOT_TOKEN','')
ADMIN_ID=int(os.getenv('ADMIN_ID','0'))
PIX_KEY=os.getenv('PIX_KEY','COLOQUE_SUA_CHAVE_PIX')
DB=os.getenv('DB_FILE','juju_gourmet.db')
if not TOKEN: raise RuntimeError('BOT_TOKEN não configurado')
bot=Bot(TOKEN); dp=Dispatcher()
PRODUCTS=[('Céu Azul',5),('Chocolate',5),('Coco Branco',5),('Coco Queimado',5),('Ferrero Rocher c/ Nutella',5),('Limão',5),('Leite Condensado',5),('Leite Ninho c/ Nutella',5),('Maracujá',5),('Maracujá c/ Nutella',5),('Oreo',5),('Ovomaltine',5),('Pudim',5),('Paçoca',5),('Pistache',5),('Pistache c/ Nutella',5),('Chiclete Trufado',5),('Morango Trufado',5),('Morango do Amor',5),('Morango',5),('Morango c/ Nutella',5),('Fini Dentadura',5)]

def conn():
 c=sqlite3.connect(DB); c.execute('CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT UNIQUE,price REAL)'); c.execute('CREATE TABLE IF NOT EXISTS cart(user_id INTEGER,product_id INTEGER,qty INTEGER,PRIMARY KEY(user_id,product_id))'); c.execute('CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,username TEXT,items TEXT,total REAL,address TEXT,status TEXT,created_at TEXT)')
 for n,p in PRODUCTS: c.execute('INSERT OR IGNORE INTO products(name,price) VALUES(?,?)',(n,p))
 c.commit(); return c

def menu():
 k=ReplyKeyboardBuilder(); [k.button(text=x) for x in ['🛍 Produtos','🛒 Meu carrinho','📦 Meus pedidos','🎁 Promoções','💬 Falar com atendente']]; k.adjust(2,2,1); return k.as_markup(resize_keyboard=True)

def prod_kb():
 c=conn(); rows=c.execute('SELECT id,name,price FROM products ORDER BY id').fetchall(); c.close(); k=InlineKeyboardBuilder()
 for i,n,p in rows: k.button(text=f'{n} — R$ {p:.2f}',callback_data=f'add:{i}')
 k.button(text='🛒 Ver carrinho',callback_data='cart'); k.adjust(1); return k.as_markup()

def cart_data(uid):
 c=conn(); rows=c.execute('SELECT p.name,p.price,ca.qty FROM cart ca JOIN products p ON p.id=ca.product_id WHERE ca.user_id=?',(uid,)).fetchall(); c.close(); total=sum(p*q for _,p,q in rows); return rows,total

@dp.message(Command('start'))
async def start(m:Message): conn().close(); await m.answer('🍫 *Juju Gourmet*\n\nBem-vindo! Escolha uma opção:',parse_mode='Markdown',reply_markup=menu())

@dp.message(F.text=='🛍 Produtos')
@dp.message(Command('produtos'))
async def products(m:Message): await m.answer('🍬 *Escolha seu produto:*',parse_mode='Markdown',reply_markup=prod_kb())

@dp.callback_query(F.data.startswith('add:'))
async def add(q:CallbackQuery):
 pid=int(q.data.split(':')[1]); c=conn(); r=c.execute('SELECT name FROM products WHERE id=?',(pid,)).fetchone(); c.execute('INSERT INTO cart VALUES(?,?,1) ON CONFLICT(user_id,product_id) DO UPDATE SET qty=qty+1',(q.from_user.id,pid)); c.commit(); c.close(); await q.answer(f'{r[0]} adicionado!')

async def show_cart(m:Message):
 rows,total=cart_data(m.from_user.id)
 if not rows: await m.answer('🛒 Seu carrinho está vazio.'); return
 t='🛒 *Seu carrinho:*\n\n'+''.join(f'• {q}x {n} — R$ {p*q:.2f}\n' for n,p,q in rows)+f'\n💰 *Total: R$ {total:.2f}*'
 k=InlineKeyboardBuilder(); k.button(text='✅ Finalizar pedido',callback_data='checkout'); k.button(text='🗑 Limpar',callback_data='clear'); k.adjust(1); await m.answer(t,parse_mode='Markdown',reply_markup=k.as_markup())

@dp.message(F.text=='🛒 Meu carrinho')
@dp.message(Command('carrinho'))
async def cart(m:Message): await show_cart(m)

@dp.callback_query(F.data=='cart')
async def cart_cb(q:CallbackQuery): await q.message.delete(); await show_cart(q.message); await q.answer()

@dp.callback_query(F.data=='clear')
async def clear(q:CallbackQuery): c=conn(); c.execute('DELETE FROM cart WHERE user_id=?',(q.from_user.id,)); c.commit(); c.close(); await q.message.edit_text('🛒 Carrinho limpo.'); await q.answer()

pending={}
@dp.callback_query(F.data=='checkout')
async def checkout(q:CallbackQuery):
 rows,total=cart_data(q.from_user.id)
 if not total: await q.answer('Carrinho vazio',show_alert=True); return
 pending[q.from_user.id]=total; await q.message.answer(f'📦 Total: *R$ {total:.2f}*\n\nEnvie seu endereço ou escreva *RETIRADA*.',parse_mode='Markdown'); await q.answer()

@dp.message(F.text=='📦 Meus pedidos')
@dp.message(Command('meuspedidos'))
async def orders(m:Message):
 c=conn(); rs=c.execute('SELECT id,total,status FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10',(m.from_user.id,)).fetchall(); c.close(); await m.answer('📦 Nenhum pedido.' if not rs else '📦 *Seus pedidos:*\n\n'+'\n'.join(f'#{i} — R$ {t:.2f} — {s}' for i,t,s in rs),parse_mode='Markdown')

@dp.message(F.text=='🎁 Promoções')
async def promos(m:Message): await m.answer('🎁 Consulte as promoções disponíveis com o atendente.')

@dp.message(F.text=='💬 Falar com atendente')
async def atend(m:Message): await m.answer('💬 Em breve colocaremos aqui o contato do atendente.')

@dp.message(Command('admin'))
async def admin(m:Message):
 if m.from_user.id!=ADMIN_ID: await m.answer('⛔ Acesso não autorizado.'); return
 await m.answer('👑 *Painel*\n/pedidos\n/stats\n/produtos_admin',parse_mode='Markdown')

@dp.message(Command('pedidos'))
async def admin_orders(m:Message):
 if m.from_user.id!=ADMIN_ID:return
 c=conn(); rs=c.execute('SELECT id,username,items,total,address,status FROM orders ORDER BY id DESC LIMIT 20').fetchall(); c.close();
 for i,u,it,t,a,s in rs: await m.answer(f'📦 #{i}\nCliente: @{u or "sem usuário"}\nItens: {it}\nTotal: R$ {t:.2f}\nEndereço: {a}\nStatus: {s}')

@dp.message(Command('stats'))
async def stats(m:Message):
 if m.from_user.id!=ADMIN_ID:return
 c=conn(); n,t=c.execute('SELECT COUNT(*),COALESCE(SUM(total),0) FROM orders').fetchone(); c.close(); await m.answer(f'📊 Pedidos: {n}\n💰 Faturamento: R$ {t:.2f}')

@dp.message(Command('produtos_admin'))
async def admin_products(m:Message):
 if m.from_user.id!=ADMIN_ID:return
 c=conn(); rs=c.execute('SELECT id,name,price FROM products').fetchall(); c.close(); await m.answer('\n'.join(f'{i} — {n} — R$ {p:.2f}' for i,n,p in rs))

@dp.message(F.text)
async def address(m:Message):
 if m.from_user.id not in pending:return
 total=pending.pop(m.from_user.id); addr=m.text; rows,_=cart_data(m.from_user.id); items=', '.join(f'{q}x {n}' for n,p,q in rows); c=conn(); cur=c.execute('INSERT INTO orders(user_id,username,items,total,address,status,created_at) VALUES(?,?,?,?,?,?,?)',(m.from_user.id,m.from_user.username or '',items,total,addr,'Aguardando pagamento',datetime.now().isoformat(timespec='minutes'))); oid=cur.lastrowid; c.execute('DELETE FROM cart WHERE user_id=?',(m.from_user.id,)); c.commit(); c.close(); await m.answer(f'✅ *Pedido #{oid} criado!*\n\n🍫 {items}\n💰 R$ {total:.2f}\n📍 {addr}\n\n💳 Pix:\n`{PIX_KEY}`\n\nApós pagar, envie o comprovante ao atendente.',parse_mode='Markdown')

async def main(): conn().close(); print('Juju Gourmet Bot iniciado'); await dp.start_polling(bot)
if __name__=='__main__': asyncio.run(main())
