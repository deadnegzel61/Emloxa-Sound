import discord
from discord import app_commands
from discord.ext import commands
import os
import subprocess
from pydub import AudioSegment

# Bot ayarları
class SesBotu(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        # Slash komutlarını sunuculara senkronize eder
        await self.tree.sync()

bot = SesBotu()

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı ve bot aktif!")

@bot.tree.command(name="bypass", description="Ses dosyasına Copyright veya Bait işlemi uygular")
@app_commands.describe(
    dosya="İşlem yapılacak .mp3 veya .ogg dosyası",
    mod="Uygulanacak işlem türü",
    bait_sayisi="Bait modunu seçtiyseniz 1 ile 5 arasında bir sayı seçin"
)
@app_commands.choices(mod=[
    app_commands.Choice(name="Copyright", value="copyright"),
    app_commands.Choice(name="Bait", value="bait")
])
@app_commands.choices(bait_sayisi=[
    app_commands.Choice(name="1", value=1),
    app_commands.Choice(name="2", value=2),
    app_commands.Choice(name="3", value=3),
    app_commands.Choice(name="4", value=4),
    app_commands.Choice(name="5", value=5),
])
async def bypass(interaction: discord.Interaction, dosya: discord.Attachment, mod: app_commands.Choice[str], bait_sayisi: app_commands.Choice[int] = None):
    # İşlemlerin uzun sürebileceğini Discord'a bildiriyoruz ki hata vermesin
    await interaction.response.defer()

    # Dosya uzantısı kontrolü
    if not dosya.filename.endswith(('.mp3', '.ogg')):
        return await interaction.followup.send("Lütfen sadece .mp3 veya .ogg formatında bir dosya yükle!", ephemeral=True)

    input_path = f"temp_{interaction.user.id}_{dosya.filename}"
    output_path = f"out_{interaction.user.id}.mp3"
    
    # Kullanıcının yüklediği dosyayı sunucuya kaydediyoruz
    await dosya.save(input_path)

    try:
        if mod.value == "copyright":
            # Audacity ayarlarının FFMPEG karşılıkları:
            # Tempo +14% (1.14), Pitch -8% (0.92), Speed 0.85
            # Matematiksel olarak birleşik oranlar:
            # Yeni Tempo = 1.14 * 0.85 = 0.969
            # Yeni Örnekleme Hızı (Pitch + Speed) = 44100 * 0.92 * 0.85 = 34486
            
            filter_complex = "asetrate=34486,aresample=44100,atempo=0.969"
            
            subprocess.run([
                "ffmpeg", "-y", "-i", input_path, 
                "-filter:a", filter_complex, 
                output_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        elif mod.value == "bait":
            if not bait_sayisi:
                return await interaction.followup.send("Bait modu için lütfen bir `Bait Sayısı` (1-5) seçin!", ephemeral=True)
            
            n = bait_sayisi.value
            start_file = f"bait-{n}-start.mp3"
            end_file = f"bait-{n}-end.mp3"

            # Dosyaların sunucuda olup olmadığını kontrol et
            if not os.path.exists(start_file) or not os.path.exists(end_file):
                return await interaction.followup.send(f"Hata: `{start_file}` veya `{end_file}` dosyaları sistemde bulunamadı. Lütfen GitHub deponuza ekleyin.", ephemeral=True)

            # Pydub ile sesleri yükle
            start_audio = AudioSegment.from_file(start_file)
            main_audio = AudioSegment.from_file(input_path)
            end_audio = AudioSegment.from_file(end_file)

            # Sesleri birleştir
            final_audio = start_audio + main_audio + end_audio

            # Süre sınırı kontrolü (6 dakika 59 saniye = 419 saniye = 419000 milisaniye)
            max_duration = 419 * 1000
            if len(final_audio) > max_duration:
                final_audio = final_audio[:max_duration]

            # Çıktıyı kaydet
            final_audio.export(output_path, format="mp3")

        # İşlem bitince dosyayı kullanıcıya gönder
        await interaction.followup.send(file=discord.File(output_path))

    except Exception as e:
        await interaction.followup.send(f"Bir hata oluştu: {str(e)}", ephemeral=True)

    finally:
        # Sunucuda yer kaplamaması için geçici dosyaları siliyoruz
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

# BOTU ÇALIŞTIRMA
bot.run("SENIN_BOT_TOKEN_BURAYA")
