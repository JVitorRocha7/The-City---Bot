import discord
import yt_dlp
import random
from discord.ext import commands

# yt_dlp extrai infos e url de streams do YT sem baixar o arquivo
# random para embaralhar a fila no tcmix

YDL_OPTS = {
    "format": "bestaudio/best",         # melhor qualidade de audio
    "noplaylist": False,                # nao ignorar playlist
    "quiet": True,                      # sem logs desnecessaria
    "default_search": "ytsearch",       # buscar no yt se nao for url
}

FFMPEG_OPTS = {
    # Reconecta auto se a conexao cair
    "before_options": "-reconnect 1 - reonnect_streamed 1 - reconnect_delay_max 5",
    "options": "-vn", # -vn = sem video, so audio
}

# dicionario global que guarda o estado de musica de cada server
# chave: guild_id | valor: dicionario com fila, estado e modo de loop
filas = {}

def get_fila(guild_id):
    """
    Retorna o estado de música do servidor
    se nao existir ainda, cria um novo.
    
    loop_musica: loopar so a musica atual (tcloop)
    loop_fila: loopar todas as musicas na fila (tcloop all)
    historico: guardar as musicas tocadas pro loop all funfar
    """
    if guild_id not in filas:
        filas[guild_id] = {
            "fila": [],                 #Lista de musicas aguardando
            "tocando": None,            # musica tocando agora
            "loop_musica": False,       # modo loop musica unica    
            "loop_fila": False,         # mood loop fila toda    
            "historico": [],            # musicas ja tocadas (usado no loop all)
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

    # Loop musica unica
    # toca a mesma musica infinitamente ate o usuario desligar

    if estado["loop_musica"] and estado["tocando"]:
        musica = estado["tocando"]
        vc.play(
            discord.FFmpegAudio(musica["url"], **FFMPEG_OTPS),
            after=lambda e: tocar_proxima(vc, guild_id, canal_texto)
        )
        return # sai sem avisar no chat pra nao spammar mensagens

    # Loop fila completa
    # quando uma musica termina, vai pro fim da fila em vvez de sumir
    if estado["loop_fila"] and estado["tocando"]:
        # adiciona a musica que acabou no fim da fila
        estado["fila"].append(estado["tocando"])

    # tocar proxima
    if estado["fila"]:   
        proxima = estado["fila"].pop(0) # remove a primeiro item da fila
        estado["tocando"] = proxima

        vc.play(
            discord.FFmpegPCMAudio(proxima["url"], **FFMPEG_OPTS),
            after=lambda e: tocar_proxima(vc, guild_id, canal_texto)
        )

        # envia mensagem no canal de texto
        # run_coroutine_threadsafe é necessário porque o 'after' roda num thread separadp
        # nao é possivel 'await' diretamente aqui
        asyncio.run_coroutine_threadsafe(
            canal_texto.send(f"Tocando agora: **{proxima['titulo']}**"),
            vc.loop
        )

    else:
        # fila vazia e sem looop - para tudo
        estado["tocando"] = None

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def buscar_musica(self, query):
        """
        Busca uma musica no Youtube usado yt_dlp.
        Retorna um dicionário com titulo e URL do stream, ou None se não encontrar.
        Separado em método próprio pra ser reutilizado em vários comandos.
        """
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if not info or "entries" not in info or not info["entries"]:
                return None
            video = info["entries"][0]
            return {}