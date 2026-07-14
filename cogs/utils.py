import discord
import spotipy
import os
import random
import re
from discord.ext import commands
from spotipy.oauth2 import SpotifyClientCredentials

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def rolar_dado(self, qtd, lados):
        """Rola dados e retorna soma e detalhes formatados"""
        resultados = [random.randint(1, lados) for _ in range(qtd)]
        formatados = [f"**{d}**" if d == 1 or d == lados else str(d) for d in resultados]
        return sum(resultados), f"{qtd}d{lados}=[{', '.join(formatados)}]"

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        msg = message.content.strip()

        if msg.lower() == "distort yourself":
            await message.reply("https://tenor.com/view/carmen-project-moon-distort-lobotomy-corporation-gif-3698852749371056132")
            return    
            
        if msg.lower() == "tcnanotech":
            await message.reply("https://tenor.com/view/i%CC%87ron-man-i%CC%87nfinity-war-nano-suit-gif-18418443")
            return

        if msg.lower() == "tcclary":
            await message.reply("https://giphy.com/gifs/areon-areonsama-areonofficial-NbXNibaFRHuAfF9rtg")
            return
        
        if "farme aura neles" in msg.lower() and self.bot.user.mentioned_in(message):
            await message.reply("https://klipy.com/gifs/iron-man-mark-46")
            return

        if msg.lower().startswith("tcspotify"):
            query = msg[9:].strip().strip('"') # pegar o nome pós tc
            if not query:
                await message.reply("Escreva o nome de uma música. Ex: `tcspotify Drag Path`")
                return
                    
            sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
            ))
        
            resultados = sp.search(q=query, limit=1, type="track")
            tracks = resultados["tracks"]["items"]
        
            if not tracks:
                await message.reply("Música não encontrada.")
                return
        
            track = tracks[0]
            nome = track["name"]
            artista = track["artists"][0]["name"]
            link = track["external_urls"]["spotify"]
        
            await message.reply(f"**{nome}** - {artista}\n[Abrir no Spotify]({link})")
            return

        # comandos específicos que começam com tc + letra mas não são calculadora
        COMANDOS_TC = ["tcnanotech", "tcclary", "tciniciativa", "tcplay", "tcstop", 
               "tcpause", "tcresume", "tcleave", "tcqueue", "tcremove", 
               "tcskip", "tcmix", "tcloop", "tcspotify"]

        if any(msg.lower().startswith(cmd) for cmd in COMANDOS_TC):
            return

        if re.match(r"^tc[a-zA-Z]", msg.lower()):
            return
        
        # verifica se começa com "tc"
        if not msg.lower().startswith("tc"):
            return

        # remove o gatilho "tc"
        expressao = msg[2:].strip().replace(" ", "").lower()

        if not expressao:
            await message.reply("Escreve uma expressão depois do `tc`. Ex: `tc2+2`, `tc4d10*2`")
            return

        COR_AZUL = discord.Color.from_str("#5865F2")
        detalhes = []

        # substitui cada dado pela soma rolada
        def substituir_dado(match):
            qtd = int(match.group(1)) if match.group(1) else 1
            lados = int(match.group(2))

            if qtd > 100 or lados > 1000:
                return "0"

            soma, detalhe = self.rolar_dado(qtd, lados)
            detalhes.append(detalhe)
            return str(soma)

        # detecta NdM ou dM e substitui pela soma
        expressao_calculavel = re.sub(r"(\d*)d(\d+)", substituir_dado, expressao)

        # valida que só tem caracteres permitidos
        if not re.fullmatch(r"[\d+\-*/%.()^]+", expressao_calculavel):
            await message.reply("Expressão inválida.")
            return

        # substitui ^ por ** para exponencial
        expressao_calculavel = expressao_calculavel.replace("^", "**")

        # substitui % por /100 para porcentagem
        expressao_calculavel = re.sub(r"(\d+\.?\d*)%", r"(\1/100)", expressao_calculavel)

        try:
            resultado = eval(expressao_calculavel)

            # formata: inteiro se não tiver decimal
            if isinstance(resultado, float) and resultado.is_integer():
                resultado_str = str(int(resultado))
            else:
                resultado_str = f"{resultado:.4f}".rstrip("0").rstrip(".")

        except ZeroDivisionError:
            await message.reply("Divisão por zero.")
            return
        except Exception:
            await message.reply("Expressão inválida.")
            return

        embed = discord.Embed(
            description=f"`{msg}`",
            color=COR_AZUL
        )

        embed.set_author(
            name=f"Calculadora — {message.author.display_name}",
            icon_url=message.author.display_avatar.url
        )

        embed.add_field(name="Resultado", value=f"`{resultado_str}`", inline=False)

        # mostra detalhes dos dados se tiver
        if detalhes:
            embed.add_field(name="Dados", value="\n".join(detalhes), inline=False)

        await message.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Utils(bot))