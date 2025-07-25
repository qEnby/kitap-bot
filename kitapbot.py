import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# === AYARLAR ===
TELEGRAM_TOKEN = "8482846041:AAGPz2QTexxnSXEyE3My3-1fixRF9xV4DrY"
GOOGLE_BOOKS_API_KEY = "AIzaSyD7VevJIB92rqUgbc3vt2lVLUrOyAi0mqQ"

# === GOOGLE BOOKS (Türkçe filtreli) ===
def search_google_books(query):
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&langRestrict=tr&key={GOOGLE_BOOKS_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "items" not in data:
        return None

    for item in data["items"]:
        book = item["volumeInfo"]
        if book.get("language") != "tr":
            continue

        title = book.get("title", "Bilinmiyor")
        authors = ", ".join(book.get("authors", ["Bilinmiyor"]))
        description = book.get("description", "Açıklama yok.")
        thumbnail = book.get("imageLinks", {}).get("thumbnail", None)
        preview_link = book.get("previewLink", None)
        is_readable = "preview only" not in preview_link.lower() if preview_link else False

        return {
            "source": "google",
            "title": title,
            "authors": authors,
            "description": description,
            "thumbnail": thumbnail,
            "link": preview_link if is_readable else None,
            "is_readable": is_readable,
            "is_pdf": False
        }

    return None

# === OPEN LIBRARY (Türkçe filtreli + PDF desteği) ===
def search_open_library(query):
    search_url = f"https://openlibrary.org/search.json?q={query}&language=tur"
    data = requests.get(search_url).json()
    if not data["docs"]:
        return None

    for doc in data["docs"]:
        if doc.get("language") and "tur" not in doc["language"]:
            continue

        title = doc.get("title", "Bilinmiyor")
        authors = ", ".join(doc.get("author_name", ["Bilinmiyor"]))
        olid = doc.get("edition_key", [None])[0]
        cover_id = doc.get("cover_i")
        thumbnail = f"http://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
        read_url = f"https://openlibrary.org/books/{olid}" if olid else None

        # Kitap detayları
        details_url = f"https://openlibrary.org/books/{olid}.json"
        details = requests.get(details_url).json()
        pdf_link = None

        if "ocaid" in details:
            ocaid = details["ocaid"]
            pdf_link = f"https://archive.org/download/{ocaid}/{ocaid}.pdf"

        return {
            "source": "openlibrary",
            "title": title,
            "authors": authors,
            "description": "Open Library'den alındı.",
            "thumbnail": thumbnail,
            "link": pdf_link if pdf_link else read_url,
            "is_readable": bool(pdf_link or doc.get("has_fulltext", False)),
            "is_pdf": bool(pdf_link)
        }

    return None

# === KULLANICI MESAJINI İŞLE ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    book = search_google_books(query) or search_open_library(query)

    if not book:
        await update.message.reply_text("📕 Üzgünüm, bu kitap bulunamadı.")
        return

    msg = f"📖 <b>{book['title']}</b>\n"
    msg += f"✍️ <i>{book['authors']}</i>\n\n"
    msg += f"📝 {book['description'][:1000]}...\n\n"

    if book["is_readable"]:
        if book["is_pdf"]:
            msg += f"📥 <a href='{book['link']}'>PDF indir</a>"
        else:
            msg += f"🔗 <a href='{book['link']}'>Okumak için tıkla</a>"
    else:
        msg += "🚫 Bu kitap sadece önizleme içeriyor."

    if book["thumbnail"]:
        await update.message.reply_photo(book["thumbnail"], caption=msg, parse_mode="HTML")
    else:
        await update.message.reply_text(msg, parse_mode="HTML")

# === /start KOMUTU ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📚 Merhaba! Bir kitap ismi gönder, sana bilgilerini ve varsa PDF'sini bulayım.")

# === BOTU BAŞLAT ===
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
