from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = """RDG - Random Dinner Generator

Genera un menu settimanale casuale per ridurre la fatica decisionale.

MENU:
/roll - Genera nuovo menu settimanale
/reroll - Rigenera piatti (es: /reroll 3 oppure /reroll 1 2 4)
/accept - Accetta menu e salvalo
/history - Vedi ultimo menu accettato (es: /history 3 per gli ultimi 3)

RICETTE:
/list - Vedi ricette
/ingredients - Vedi ricette con ingredienti esterni
/add - Aggiungi ricetta
/edit - Modifica ricetta (es: /edit "Pasta Carbonara")

SHOPPING:
/remember - Vedi/aggiungi articoli da comprare (es: /remember olio d'oliva, caffè)
/bought - Segna articoli come comprati e ripristina ricette

INGREDIENTI ESTERNI:
/external - Marca ingredienti da comprare altrove
  Batch: /external 1 salmone, aneto; 2 turmerico
  Singolo: /external 1 salmone, aneto
/noexternal - Nessun ingrediente esterno (es: /noexternal 2 oppure /noexternal 1 2 4)
/fill_missing - Mostra ricette mancanti e riempi una alla volta
/skip - Ignora richiesta ingredienti

WORKFLOW:
1. /roll
2. /reroll (multiple o singole posizioni)
3. /accept
4. /external, /noexternal, o /skip per ingredienti
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(HELP_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(HELP_TEXT)
