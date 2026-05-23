import logging
import requests
from datetime import datetime
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError

# ========== НАСТРОЙКИ ==========
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "-1003791907965"
INTERVAL_SECONDS = 60
# ================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_ton_price_usd() -> float | None:
    """Получает курс TON/USDT с Binance."""
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return float(response.json()["price"])
    except Exception as e:
        logger.error(f"Ошибка TON цены: {e}")
        return None


def get_uzs_rate() -> float | None:
    """Получает рыночный курс UZS через exchangerate-api (бесплатно, без ключа)."""
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data["rates"]["UZS"])
    except Exception as e:
        logger.error(f"Ошибка курса UZS: {e}")
        return None


def format_message(price_usd: float, uzs_rate: float) -> str:
    price_uzs = int(price_usd * uzs_rate)
    now = datetime.now().strftime("%H:%M")
    return (
        f"💎 <b>TON Price $ / UZS</b>\n"
        f"💵 <b>{price_usd:.2f}$</b>\n"
        f"🇺🇿 <b>{price_uzs:,} UZS</b>\n"
        f"🕐 {now}\n"
        f"<b>Made by core17</b>"
    )


async def send_price(context: ContextTypes.DEFAULT_TYPE) -> None:
    price = get_ton_price_usd()
    uzs_rate = get_uzs_rate()

    if price is None:
        logger.warning("Не удалось получить цену TON.")
        return
    if uzs_rate is None:
        logger.warning("Не удалось получить курс UZS, используем запасной 12900.")
        uzs_rate = 12900  # запасной курс если API недоступен

    message = format_message(price, uzs_rate)
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="HTML"
        )
        logger.info(f"Отправлено: {price:.2f}$ / {int(price * uzs_rate):,} UZS (курс: {uzs_rate:.0f})")
    except TelegramError as e:
        logger.error(f"Ошибка отправки: {e}")


async def start_command(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✅ Бот запущен! Каждую минуту отправляю курс TON в канал.")


async def price_command(update, context: ContextTypes.DEFAULT_TYPE) -> None:
    price = get_ton_price_usd()
    uzs_rate = get_uzs_rate()
    if price and uzs_rate:
        await update.message.reply_text(format_message(price, uzs_rate), parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Не удалось получить курс. Попробуй позже.")


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("price", price_command))

    job_queue = app.job_queue
    job_queue.run_repeating(
        send_price,
        interval=INTERVAL_SECONDS,
        first=5
    )

    logger.info("Бот запущен. Нажми Ctrl+C для остановки.") 
    app.run_polling()


if __name__ == "__main__":
    main()
