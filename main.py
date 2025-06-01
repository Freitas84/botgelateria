import logging
import os
import json
import csv
import aiofiles
from fpdf import FPDF
from datetime import datetime
from telegram import (Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BotCommand, InputFile)
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackContext)
from fastapi import FastAPI
import uvicorn
import threading

TOKEN = "7992260209:AAFUZ_FAFzkciDPNPxrNNNAriw36zECNeJE"
ADMIN_ID = 6897041487
GRUPO_ID = -1001786862883

logging.basicConfig(level=logging.INFO)

DADOS_ARQUIVO = 'alunos.json'
PERGUNTAS_ARQUIVO = 'perguntas.json'
CONFIG_ARQUIVO = 'config.json'
FOTO_PATH = 'foto_bot.jpg'

if not os.path.exists(DADOS_ARQUIVO):
    with open(DADOS_ARQUIVO, 'w') as f:
        json.dump({}, f)
if not os.path.exists(PERGUNTAS_ARQUIVO):
    with open(PERGUNTAS_ARQUIVO, 'w') as f:
        json.dump(["Qual seu nome?", "De qual cidade você é?", "Qual o @ do Instagram da sua gelateria?"], f)
if not os.path.exists(CONFIG_ARQUIVO):
    with open(CONFIG_ARQUIVO, 'w') as f:
        json.dump({"abordagem": "Olá! Responda algumas perguntas rápidas para concluirmos seu cadastro no curso.", "agradecimento": "Obrigado por responder!"}, f)

def carregar_json(caminho):
    with open(caminho, 'r') as f:
        return json.load(f)

def salvar_json(caminho, dados):
    with open(caminho, 'w') as f:
        json.dump(dados, f, indent=2)

RESPOSTA = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    dados = carregar_json(DADOS_ARQUIVO)
    config = carregar_json(CONFIG_ARQUIVO)
    perguntas = carregar_json(PERGUNTAS_ARQUIVO)
    if user_id in dados:
        await update.message.reply_text("Você já respondeu ao formulário. Obrigado!")
        return ConversationHandler.END
    context.user_data['respostas'] = []
    context.user_data['pergunta_atual'] = 0
    await update.message.reply_text(config['abordagem'])
    await update.message.reply_text(perguntas[0])
    return RESPOSTA

async def coletar_respostas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = update.message.text
    context.user_data['respostas'].append(resposta)
    perguntas = carregar_json(PERGUNTAS_ARQUIVO)
    context.user_data['pergunta_atual'] += 1
    if context.user_data['pergunta_atual'] < len(perguntas):
        await update.message.reply_text(perguntas[context.user_data['pergunta_atual']])
        return RESPOSTA
    user_id = str(update.effective_user.id)
    dados = carregar_json(DADOS_ARQUIVO)
    dados[user_id] = {
        'nome': update.effective_user.full_name,
        'respostas': context.user_data['respostas'],
        'data': datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    salvar_json(DADOS_ARQUIVO, dados)
    config = carregar_json(CONFIG_ARQUIVO)
    await update.message.reply_text(config['agradecimento'])
    return ConversationHandler.END

async def painel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    botoes = [
        ["📤 Enviar para todos", "📊 Ver total"],
        ["📁 CSV", "📄 PDF", "🧷 Backup"],
        ["➕ Pergunta", "✏️ Editar", "❌ Excluir"],
        ["🔁 Reenviar", "✉️ Mensagem", "🖼️ Foto"],
        ["✍️ Abordagem", "🙏 Agradecimento"]
    ]
    await update.message.reply_text("Painel do Administrador:", reply_markup=ReplyKeyboardMarkup(botoes, one_time_keyboard=True))

async def gerar_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    dados = carregar_json(DADOS_ARQUIVO)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Respostas dos Alunos", ln=True, align='C')
    pdf.ln(10)
    for user_id, info in dados.items():
        pdf.cell(200, 10, txt=f"{info['nome']} ({info['data']}):", ln=True)
        for i, resposta in enumerate(info['respostas']):
            pdf.multi_cell(0, 10, txt=f"  {i+1}. {resposta}")
        pdf.ln(5)
    caminho_pdf = "respostas_alunos.pdf"
    pdf.output(caminho_pdf)
    await update.message.reply_document(InputFile(caminho_pdf))

async def responder_botao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if update.effective_user.id != ADMIN_ID:
        return
    if texto == "📄 PDF":
        await gerar_pdf(update, context)
    elif texto == "📊 Ver total":
        dados = carregar_json(DADOS_ARQUIVO)
        await update.message.reply_text(f"Total de alunos cadastrados: {len(dados)}")
    elif texto == "📁 CSV":
        dados = carregar_json(DADOS_ARQUIVO)
        with open("respostas_alunos.csv", "w", newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Nome", "Data"] + [f"Resposta {i+1}" for i in range(10)])
            for info in dados.values():
                writer.writerow([info['nome'], info['data']] + info['respostas'])
        await update.message.reply_document(InputFile("respostas_alunos.csv"))
    elif texto == "🧷 Backup":
        await update.message.reply_document(InputFile(DADOS_ARQUIVO))
    elif texto == "🔁 Reenviar":
        dados = carregar_json(DADOS_ARQUIVO)
        membros = await context.bot.get_chat_members_count(GRUPO_ID)
        enviados = 0
        for i in range(membros):
            membro = await context.bot.get_chat_member(GRUPO_ID, i)
            user_id = str(membro.user.id)
            if user_id not in dados and not membro.user.is_bot:
                try:
                    await context.bot.send_message(membro.user.id, carregar_json(CONFIG_ARQUIVO)['abordagem'])
                    enviados += 1
                except:
                    pass
        await update.message.reply_text(f"Formulário reenviado para {enviados} alunos.")
    elif texto == "✉️ Mensagem":
        await update.message.reply_text("Envie o ID do aluno seguido da mensagem, separado por '|'. Ex: 123456|Olá!")
    elif texto == "🖼️ Foto":
        await update.message.reply_text("Envie a nova imagem de perfil do bot.")
    elif texto == "✍️ Abordagem":
        await update.message.reply_text("Digite a nova mensagem de abordagem:")
    elif texto == "🙏 Agradecimento":
        await update.message.reply_text("Digite a nova mensagem de agradecimento:")
    elif texto == "➕ Pergunta":
        await update.message.reply_text("Digite a nova pergunta para adicionar ao formulário:")
    elif texto == "✏️ Editar":
        perguntas = carregar_json(PERGUNTAS_ARQUIVO)
        msg = "Perguntas atuais:\n"
        for i, p in enumerate(perguntas):
            msg += f"{i+1}. {p}\n"
        msg += "\nEnvie o número da pergunta a editar seguido do novo texto. Ex: 2|Qual sua cidade?"
        await update.message.reply_text(msg)
    elif texto == "❌ Excluir":
        await update.message.reply_text("Digite o ID do aluno a ser excluído:")
    else:
        await update.message.reply_text("Comando não reconhecido do painel.")

# FastAPI app para manter vivo
app_keep_alive = FastAPI()

@app_keep_alive.get("/")
def read_root():
    return {"status": "ok"}

def iniciar_fastapi():
    uvicorn.run(app_keep_alive, host="0.0.0.0", port=8080)

# Início da aplicação Telegram
if __name__ == '__main__':
    threading.Thread(target=iniciar_fastapi).start()

    from telegram.ext import Application
    app = ApplicationBuilder().token(TOKEN).build()

    conversa = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={RESPOSTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, coletar_respostas)]},
        fallbacks=[]
    )

    app.add_handler(conversa)
    app.add_handler(CommandHandler("painel", painel))
    app.add_handler(CommandHandler("pdf", gerar_pdf))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_botao))

    logging.info("Bot iniciado.")
    app.run_polling()
