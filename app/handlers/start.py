from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = """*RDG - Random Dinner Generator*

Genera un menu settimanale casuale per ridurre la fatica decisionale.

*MENU*
/roll - Genera nuovo menu settimanale
/reroll <categoria|numero> - Rigenera piatti
/accept - Accetta menu e salvalo
/history - Vedi menu accettati

*RICETTE*
/list [categoria] - Vedi ricette
/add - Aggiungi ricetta

*INGREDIENTI ESTERNI*
/external <N> ing1, ing2 - Marca ingredienti da comprare altrove
/noexternal <N> - Nessun ingrediente esterno
/fill_missing - Mostra ricette mancanti
/skip - Ignora richiesta ingredienti

*WORKFLOW*
1. /roll
2. /reroll <cosa cambiare>
3. /accept
4. /external o /skip (se chiesto)
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
