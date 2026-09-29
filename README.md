# Juju Gourmet — Telegram Sales Bot

Bot de vendas para Telegram com:
- Catálogo de produtos
- Carrinho
- Checkout
- Endereço/retirada
- Pedidos
- Área administrativa via comandos
- Estoque
- Cupons
- Estrutura de pagamento Pix
- SQLite para desenvolvimento e PostgreSQL para produção

## 1. Requisitos

- Python 3.11+
- Conta Telegram
- Bot criado pelo @BotFather
- Opcional: conta Mercado Pago para Pix

## 2. Instalação

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Edite `.env`.

## 3. Configuração

Obrigatório:
- `BOT_TOKEN`: token entregue pelo BotFather
- `ADMIN_TELEGRAM_ID`: seu ID numérico do Telegram

Para descobrir seu ID, use um bot confiável de identificação de ID ou, depois de iniciar este bot, consulte os logs.

Banco local:
`DATABASE_URL=sqlite+aiosqlite:///./juju.db`

Produção:
`DATABASE_URL=postgresql+asyncpg://usuario:senha@host:5432/juju`

Pix:
- O projeto funciona inicialmente com pedido marcado como "aguardando pagamento".
- Para cobrança Pix automática, configure Mercado Pago e implemente/ative o adapter em `app/payments/mercadopago.py`.
- Nunca coloque Access Token no código ou publique `.env`.

## 4. Rodar

```bash
python -m app.main
```

No Telegram:
1. Abra seu bot.
2. `/start`
3. Use `/admin` com a conta definida em `ADMIN_TELEGRAM_ID`.

## 5. Comandos administrativos

- `/admin` — menu administrativo
- `/addproduct` — adiciona produto por conversa
- `/products` — lista produtos
- `/stock` — estoque
- `/orders` — pedidos recentes
- `/stats` — estatísticas

O painel também pode ser expandido para uma interface web posteriormente.

## 6. Estrutura

```text
app/
  main.py
  config.py
  db.py
  models.py
  handlers/
    user.py
    admin.py
  keyboards.py
  payments/
    base.py
    mercadopago.py
```

## 7. Segurança

Não compartilhe:
- BOT_TOKEN
- Mercado Pago Access Token
- DATABASE_URL com senha

Se um token do BotFather vazar, revogue/regere-o no BotFather.
