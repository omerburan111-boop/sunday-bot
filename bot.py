import re
import json
import os
import math
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# --- KALICI HAFIZA VE YÖNETİM KURULU ---
VERI_DOSYASI = "katilimcilar.json"
# Senin ID'n ve diğer 4 yöneticinin ID'leri
ADMINLER = [2073140443, 8766027090, 6989660804, 5656861374, 1293227694]
TOKEN = "8846445960:AAFbbUCtECgiNC6snkMjt93eYLb5JykcVKw"

def veri_yukle():
    if os.path.exists(VERI_DOSYASI):
        with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

def veri_kaydet(data):
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

katilimcilar = veri_yukle()

# --- KOMUT FONKSİYONLARI ---
async def help_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = (
        "🤖 <b>SUNDAY CITY ETKİNLİK BOTU</b> 🤖\n\n"
        "👤 <b>ÜYE KOMUTLARI:</b>\n"
        "🔸 <code>/parti [Oyunİsmi] [Sayı]</code>\n"
        "🔸 <code>/duzenle [Oyunİsmi] [Sayı]</code>\n\n"
        "👑 <b>YÖNETİCİ KOMUTLARI:</b>\n"
        "🔹 <code>/liste</code> (Otomatik 19 sınırına göre böler)\n"
        "🔹 <code>/liste [Sayı]</code> (Örn: /liste 4)\n"
        "🔹 <code>/all</code> (Herkesi etiketler)\n"
        "🔹 <code>/temizle</code> (Listeyi sıfırlar)"
    )
    await update.message.reply_text(mesaj, parse_mode=ParseMode.HTML)

async def parti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global katilimcilar
    katilimcilar = veri_yukle()
    user_id = str(update.effective_user.id)
    if user_id in katilimcilar:
        await update.message.reply_text("Zaten listedesin!")
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /parti IYISUNDAY 3")
        return
    eslesme = re.match(r"^(.*?)\s+(\d+)$", " ".join(context.args))
    if not eslesme:
        await update.message.reply_text("Hata! Rakamı unuttun. Örn: /parti IYISUNDAY 3")
        return
    katilimcilar[user_id] = [update.effective_user.full_name, eslesme.group(1), int(eslesme.group(2))]
    veri_kaydet(katilimcilar)
    await update.message.reply_text("✅ Kayıt Başarılı!")

async def duzenle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global katilimcilar
    katilimcilar = veri_yukle()
    user_id = str(update.effective_user.id)
    if user_id not in katilimcilar:
        await update.message.reply_text("Listede yoksun!")
        return
    eslesme = re.match(r"^(.*?)\s+(\d+)$", " ".join(context.args))
    if not eslesme:
        await update.message.reply_text("Hata! Örn: /duzenle IYISUNDAY 4")
        return
    katilimcilar[user_id] = [update.effective_user.full_name, eslesme.group(1), int(eslesme.group(2))]
    veri_kaydet(katilimcilar)
    await update.message.reply_text("🔄 Bilgilerin güncellendi!")

async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # YENİ YÖNETİCİ KONTROLÜ
    if update.effective_user.id not in ADMINLER: return
    
    global katilimcilar
    katilimcilar = veri_yukle()
    if not katilimcilar:
        await update.message.reply_text("Liste boş!")
        return

    toplam_parti = sum(v[2] for v in katilimcilar.values())
    grup_sayisi = 0
    if context.args and context.args[0].isdigit():
        grup_sayisi = int(context.args[0])
    else:
        komut = update.message.text.replace("/liste", "").strip()
        if komut.isdigit(): grup_sayisi = int(komut)

    min_gerekli_grup = max(1, math.ceil(toplam_parti / 19))
    if grup_sayisi == 0:
        grup_sayisi = min_gerekli_grup
    
    if toplam_parti > grup_sayisi * 19:
        await update.message.reply_text(
            f"🛑 <b>HATA! KAPASİTE AŞILDI!</b>\n\n"
            f"Şu an listede toplam <b>{toplam_parti}</b> parti var.\n"
            f"Bunu {grup_sayisi} gruba bölersek 19 kişi sınırı aşılır!\n\n"
            f"Sınırı aşmamak için en az <b>{min_gerekli_grup}</b> gruba bölmelisin.", 
            parse_mode=ParseMode.HTML
        )
        return

    if grup_sayisi > 8:
        await update.message.reply_text("Max 8 grup olabilir!")
        return

    gruplar = [{"toplam": 0, "uyeler": {}} for _ in range(grup_sayisi)]
    sirali_liste = sorted(katilimcilar.values(), key=lambda x: x[2], reverse=True)

    for tel_isim, oyun_isim, sayi in sirali_liste:
        key_user = f"{tel_isim}_{oyun_isim}"
        for _ in range(sayi):
            uygun_gruplar = [g for g in gruplar if g["toplam"] < 19]
            if not uygun_gruplar: uygun_gruplar = gruplar
            
            min_toplam = min(g["toplam"] for g in uygun_gruplar)
            min_gruplar = [g for g in uygun_gruplar if g["toplam"] == min_toplam]
            
            secilen_grup = min(min_gruplar, key=lambda g: g["uyeler"].get(key_user, {}).get("sayi", 0))
            
            secilen_grup["toplam"] += 1
            if key_user not in secilen_grup["uyeler"]:
                secilen_grup["uyeler"][key_user] = {"tel": tel_isim, "oyun": oyun_isim, "sayi": 0}
            secilen_grup["uyeler"][key_user]["sayi"] += 1

    mesaj = f"⚔️ <b>{grup_sayisi} GRUPLU ADİL DAĞILIM</b> ⚔️\n\n"
    for i, g in enumerate(gruplar, 1):
        mesaj += f"🛡 <b>{i}. GRUP</b> ({g['toplam']}/19)\n"
        for d in g["uyeler"].values():
            mesaj += f"  ├ 👤 {d['tel']} ➡️ 🎮 {d['oyun']} <b>[{d['sayi']}]</b>\n"
        mesaj += "\n"
    mesaj += f"📊 <b>Genel Toplam:</b> {toplam_parti} Parti"
    await update.message.reply_text(mesaj, parse_mode=ParseMode.HTML)

async def all_etiketle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # YENİ YÖNETİCİ KONTROLÜ
    if update.effective_user.id not in ADMINLER: return
    
    global katilimcilar
    katilimcilar = veri_yukle()
    if not katilimcilar: return
    etiketler = [f'<a href="tg://user?id={u}">{v[0]}</a>' for u, v in katilimcilar.items()]
    await update.message.reply_text("📣 <b>TOPLANIN!</b>\n\n" + ", ".join(etiketler), parse_mode=ParseMode.HTML)

async def temizle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # YENİ YÖNETİCİ KONTROLÜ
    if update.effective_user.id not in ADMINLER: return
    
    veri_kaydet({})
    await update.message.reply_text("Liste sıfırlandı! 🧹")

# --- RENDER İÇİN ARKA PLAN FLASK SUNUCUSU ---
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Bot 7/24 Aktif ve Yönetim Kurulu Görevde! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler(["start", "help"], help_komutu))
    app.add_handler(CommandHandler("parti", parti))
    app.add_handler(CommandHandler("duzenle", duzenle))
    app.add_handler(CommandHandler(["liste", "liste2", "liste3", "liste4", "liste5", "liste6", "liste7", "liste8"], liste))
    app.add_handler(CommandHandler("all", all_etiketle))
    app.add_handler(CommandHandler("temizle", temizle))
    
    # Flask sunucusunu arka planda başlat
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Bot Kesintisiz Polling Modunda Başlıyor...")
    app.run_polling()

if __name__ == '__main__':
    main()
