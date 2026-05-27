from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = """
🤖 *RDG — Random Dinner Generator*

Genera un menu settimanale casuale per ridurre la fatica decisionale.

*Comandi Menu:*

/roll - Genera un nuovo menu settimanale
/reroll <categoria|numero> - Rigenera piatti
  • /reroll pesce - Rigenera il piatto di pesce
  • /reroll 3 - Rigenera il piatto alla posizione 3
/accept - Accetta il menu e salvalo in storia
/history - Vedi i menu accettati

*Comandi Ricette:*

/list [categoria] - Vedi tutte le ricette o filtra per categoria
/add - Aggiungi una nuova ricetta

*Comandi Ingredienti Esterni:*

/external <N> ing1, ing2 - Marca ingredienti da acquistare altrove
  • /external 1 salmone fresco, aneto
/noexternal <N> - Marca ricetta senza ingredienti esterni
  • /noexternal 2
/fill_missing - Mostra ricette con ingredienti ancora sconosciuti
/skip - Ignora la richiesta di ingredienti esterni

*Uso rapido:*
1️⃣ /roll
2️⃣ /reroll <cosa ti piace cambiare>
3️⃣ /accept
4️⃣ /external o /skip (se chiesto)
Done! 🎉
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        f"Ciao! 👋\n\n{HELP_TEXT}",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
