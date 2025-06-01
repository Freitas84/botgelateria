import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    if message.chat.type == "private":
        await message.answer("Olá! Bem-vindo ao bot da Gelateria. Aguarde instruções do administrador.")

@dp.message_handler(commands=['painel'])
async def painel_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Acesso restrito.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📩 Enviar formulário", "📊 Ver total de alunos")
    markup.add("⚙️ Alterar mensagem", "📁 Baixar CSV")
    markup.add("🔄 Reenviar para pendentes", "✉️ Mensagem individual")
    await message.answer("Painel Administrativo:", reply_markup=markup)

@dp.message_handler(lambda m: m.text == "📊 Ver total de alunos")
async def ver_total(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    # Simulação simples
    await message.answer("Total de alunos registrados: 42")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)