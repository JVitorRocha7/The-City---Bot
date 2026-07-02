import discord
import yt_dlp
import random
from discord.ext import commands

# yt_dlp extrai informações e URLs de streams do YouTube sem baixar o arquivo
# random é usado para embaralhar a fila no tcmix

YDL_OPTS = {
    "format": "bestaudio/best",     # melhor qualidade de áudio disponível
    "noplaylist": False,             # não ignora playlists
    "quiet": True,                  # sem logs desnecessários no terminal
    "default_search": "ytsearch",  # busca no YouTube se não for URL
}

FFMPEG_OPTS = {
    # reconecta automaticamente se a conexão com o stream cair
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",  # -vn = no video, só áudio
}

# dicionário global que guarda o estado de música de cada servidor
# chave: guild_id | valor: dicionário com fila, estado e modo de loop
filas = {}

def get_fila(guild_id):
    """
    Retorna o estado de música do servidor.
    Se não existir ainda, cria um novo com valores padrão.
    
    loop_musica: loopa só a música atual (tcloop)
    loop_fila: loopa a fila inteira (tcloop all)
    historico: guarda as músicas tocadas para o loop all funcionar
    """
    if guild_id not in filas:
        filas[guild_id] = {
            "fila": [],           # lista de músicas aguardando
            "tocando": None,      # música tocando agora
            "loop_musica": False, # modo loop música única
            "loop_fila": False,   # modo loop fila completa
            "historico": [],      # músicas já tocadas (usado no loop all)
        }
    return filas[guild_id]

def tocar_proxima(vc, guild_id, canal_texto):
    """
    Chamada automaticamente pelo discord.py quando uma música termina.
    Decide o que tocar a seguir baseado no modo de loop ativo.
    
    Fluxo:
    1. Se loop_musica ativo → toca a mesma música de novo
    2. Se loop_fila ativo → move a música atual pro fim da fila e toca a próxima
    3. Se não tiver loop → toca a próxima da fila normalmente
    """
    import asyncio

    estado = get_fila(guild_id)

    # --- LOOP MÚSICA ÚNICA ---
    # toca a mesma música infinitamente até o usuário desativar
    if estado["loop_musica"] and estado["tocando"]:
        musica = estado["tocando"]
        vc.play(
            discord.FFmpegPCMAudio(musica["url"], **FFMPEG_OPTS),
            after=lambda e: tocar_proxima(vc, guild_id, canal_texto)
        )
        return  # sai sem avisar no chat pra não spammar mensagens

    # --- LOOP FILA COMPLETA ---
    # quando uma música termina, vai pro fim da fila em vez de sumir
    if estado["loop_fila"] and estado["tocando"]:
        # adiciona a música que acabou no fim da fila
        estado["fila"].append(estado["tocando"])

    # --- TOCA PRÓXIMA (comum ao loop_fila e sem loop) ---
    if estado["fila"]:
        proxima = estado["fila"].pop(0)  # remove o primeiro item da fila
        estado["tocando"] = proxima

        vc.play(
            discord.FFmpegPCMAudio(proxima["url"], **FFMPEG_OPTS),
            after=lambda e: tocar_proxima(vc, guild_id, canal_texto)
        )

        # envia mensagem no canal de texto
        # run_coroutine_threadsafe é necessário porque o 'after' roda numa thread separada
        # não é possível usar 'await' diretamente aqui
        asyncio.run_coroutine_threadsafe(
            canal_texto.send(f"🎵 Tocando agora: **{proxima['titulo']}**"),
            vc.loop
        )
    else:
        # fila vazia e sem loop — para tudo
        estado["tocando"] = None


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def buscar_musica(self, query):
        """
        Busca uma música no YouTube usando yt_dlp.
        Retorna um dicionário com título e URL do stream, ou None se não encontrar.
        Separado em método próprio pra ser reutilizado em vários comandos.
        """
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if not info or "entries" not in info or not info["entries"]:
                return None
            video = info["entries"][0]
            return {
                "titulo": video.get("title", "Desconhecido"),
                "url": video["url"],
                "query": query
            }

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        msg = message.content.strip()
        guild_id = message.guild.id
        estado = get_fila(guild_id)

        # ============================================================
        # COMANDO: tcplay <nome ou URL>
        # Se nada tiver tocando, toca direto.
        # Se já tiver tocando, adiciona na fila.
        # ============================================================
        if msg.lower().startswith("tcplay "):
            query = msg[7:].strip()

            if not message.author.voice:
                await message.reply("Você precisa estar em um canal de voz.")
                return

            canal = message.author.voice.channel

            if message.guild.voice_client:
                await message.guild.voice_client.move_to(canal)
                vc = message.guild.voice_client
            else:
                vc = await canal.connect()

            await message.reply(f"🔍 Buscando **{query}**...")

            musica = await self.buscar_musica(query)
            if not musica:
                await message.reply("Música não encontrada.")
                return

            if vc.is_playing() or vc.is_paused():
                # já tá tocando algo — adiciona na fila
                estado["fila"].append(musica)
                pos = len(estado["fila"])
                await message.reply(f"➕ **{musica['titulo']}** adicionada na fila (posição {pos})")
            else:
                # nada tocando — toca direto
                estado["tocando"] = musica
                vc.play(
                    discord.FFmpegPCMAudio(musica["url"], **FFMPEG_OPTS),
                    after=lambda e: tocar_proxima(vc, guild_id, message.channel)
                )
                await message.reply(f"🎵 Tocando: **{musica['titulo']}**")

        # ============================================================
        # COMANDO: tcqueue
        # Mostra a música atual e a fila de próximas
        # ============================================================
        elif msg.lower() == "tcqueue":
            tocando = estado["tocando"]
            fila = estado["fila"]

            if not tocando and not fila:
                await message.reply("A fila está vazia.")
                return

            linhas = []

            # indica os modos de loop ativos
            if estado["loop_musica"]:
                linhas.append("🔂 **Loop música ativo**")
            if estado["loop_fila"]:
                linhas.append("🔁 **Loop fila ativo**")

            if tocando:
                linhas.append(f"\n🎵 **Tocando agora:** {tocando['titulo']}")

            if fila:
                linhas.append("\n**Próximas:**")
                for i, musica in enumerate(fila, 1):
                    linhas.append(f"`{i}.` {musica['titulo']}")

            await message.reply("\n".join(linhas))

        # ============================================================
        # COMANDO: tcremove <número>
        # Remove uma música específica da fila pelo número do tcqueue
        # ============================================================
        elif msg.lower().startswith("tcremove "):
            try:
                numero = int(msg[9:].strip())
            except ValueError:
                await message.reply("Usa um número. Ex: `tcremove 2`")
                return

            fila = estado["fila"]

            if numero < 1 or numero > len(fila):
                await message.reply(f"Número inválido. A fila tem {len(fila)} música(s).")
                return

            # índice 0 = posição 1 na fila exibida
            removida = fila.pop(numero - 1)
            await message.reply(f"🗑 **{removida['titulo']}** removida da fila.")

        # ============================================================
        # COMANDO: tcmix
        # Embaralha a ordem das músicas na fila aleatoriamente
        # random.shuffle modifica a lista diretamente (in-place)
        # ============================================================
        elif msg.lower() == "tcmix":
            fila = estado["fila"]
            if not fila:
                await message.reply("A fila está vazia.")
                return
            random.shuffle(fila)
            await message.reply(f"🔀 Fila embaralhada! {len(fila)} música(s) na fila.")

        # ============================================================
        # COMANDO: tcloop
        # Ativa/desativa o loop da música atual
        # Funciona como toggle — chama de novo pra desativar
        # ============================================================
        elif msg.lower() == "tcloop":
            # toggle: se tava True vira False, se tava False vira True
            estado["loop_musica"] = not estado["loop_musica"]
            
            # desativa loop_fila se ativar loop_musica (são mutuamente exclusivos)
            if estado["loop_musica"]:
                estado["loop_fila"] = False
                await message.reply("🔂 Loop da música ativado.")
            else:
                await message.reply("🔂 Loop da música desativado.")

        # ============================================================
        # COMANDO: tcloop all
        # Ativa/desativa o loop da fila inteira
        # Quando uma música termina, vai pro fim da fila em vez de sumir
        # ============================================================
        elif msg.lower() == "tcloop all":
            estado["loop_fila"] = not estado["loop_fila"]

            # desativa loop_musica se ativar loop_fila
            if estado["loop_fila"]:
                estado["loop_musica"] = False
                await message.reply("🔁 Loop da fila ativado.")
            else:
                await message.reply("🔁 Loop da fila desativado.")

        # ============================================================
        # COMANDO: tcskip
        # Pula a música atual — o 'after' chama tocar_proxima automaticamente
        # ============================================================
        elif msg.lower() == "tcskip":
            vc = message.guild.voice_client
            if vc and vc.is_playing():
                # desativa loop_musica temporariamente pra não repetir a mesma
                estado["loop_musica"] = False
                vc.stop()  # stop dispara o 'after' que toca a próxima
                await message.reply("⏭ Pulando...")
            else:
                await message.reply("Nada tocando.")

        # ============================================================
        # COMANDO: tcstop
        # Para tudo, limpa a fila e reseta os loops
        # ============================================================
        elif msg.lower() == "tcstop":
            vc = message.guild.voice_client
            estado["fila"].clear()
            estado["tocando"] = None
            estado["loop_musica"] = False
            estado["loop_fila"] = False
            if vc and vc.is_playing():
                vc.stop()
            await message.reply("⏹ Parado e fila limpa.")

        # ============================================================
        # COMANDOS: tcpause / tcresume / tcleave
        # ============================================================
        elif msg.lower() == "tcpause":
            vc = message.guild.voice_client
            if vc and vc.is_playing():
                vc.pause()
                await message.reply("⏸ Pausado.")

        elif msg.lower() == "tcresume":
            vc = message.guild.voice_client
            if vc and vc.is_paused():
                vc.resume()
                await message.reply("▶ Retomado.")

        elif msg.lower() == "tcleave":
            vc = message.guild.voice_client
            estado["fila"].clear()
            estado["tocando"] = None
            estado["loop_musica"] = False
            estado["loop_fila"] = False
            if vc:
                await vc.disconnect()
            await message.reply("👋 Saí do canal.")


async def setup(bot):
    await bot.add_cog(Music(bot))