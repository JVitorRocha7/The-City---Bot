import discord
import random
import re
from discord.ext import commands

COR_DOURADA = discord.Color.from_str("#D4AF37")


class BotaoExpandir(discord.ui.View):
    """View com o botão Expandir — aparece na mensagem simples da rolagem"""

    def __init__(self, embed_detalhes: discord.Embed):
        super().__init__(timeout=120)  # botão expira após 2 minutos
        # guarda o embed completo pra mostrar quando clicar
        self.embed_detalhes = embed_detalhes

    @discord.ui.button(label="Expandir", style=discord.ButtonStyle.secondary, emoji="🎲")
    async def expandir(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ao clicar, edita a mensagem mostrando os detalhes completos"""
        
        # desativa o botão pra não poder clicar duas vezes
        button.disabled = True
        button.label = "Expandido"
        
        # edita a mensagem original com o embed de detalhes
        await interaction.response.edit_message(embed=self.embed_detalhes, view=self)


class Dados(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def rolar_dados(self, qtd, lados):
        """Rola os dados e retorna a lista de resultados formatada e a soma"""
        resultados = [random.randint(1, lados) for _ in range(qtd)]
        # destaca 1 e valor máximo em negrito
        formatados = [f"**{d}**" if d == 1 or d == lados else str(d) for d in resultados]
        return resultados, f"[{', '.join(formatados)}]"

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        msg = message.content.strip().lower()

        # --- REPETIÇÃO (ex: 3#2d6) ---
        if "#" in msg:
            partes = msg.split("#", 1)
            if not partes[0].isdigit():
                return

            vezes = int(partes[0])
            expressao_dado = partes[1].strip()

            if expressao_dado.startswith('d'):
                expressao_dado = "1" + expressao_dado

            if vezes > 10:
                await message.reply("Limite atingido")
                return

            linhas_resposta = []
            padrao_dados = r"(\d+)d(\d+)"

            for i in range(1, vezes + 1):
                match = re.fullmatch(padrao_dados, expressao_dado)
                if match:
                    qtd = int(match.group(1))
                    lados = int(match.group(2))

                    if qtd > 100 or lados > 100:
                        await message.reply("https://i.ytimg.com/vi/OuHQQdVbhKc/maxresdefault.jpg")
                        return

                    _, dados_str = self.rolar_dados(qtd, lados)
                    linhas_resposta.append(f"` {i} `┠ {dados_str}")

            if linhas_resposta:
                embed = discord.Embed(
                    title="Rolagem",
                    description=f"Resultados para **{msg}**",
                    color=COR_DOURADA
                )
                embed.add_field(name="Resultados", value="\n".join(linhas_resposta), inline=False)
                embed.set_footer(text=f"Solicitado por {message.author.display_name}", icon_url=message.author.display_avatar.url)
                await message.reply(embed=embed)
            return

        # --- ROLAGEM NORMAL ---
        msg_limpa = msg.replace(" ", "")

        if not re.fullmatch(r"[\dd+\-]+", msg_limpa) or "d" not in msg_limpa:
            return

        msg_limpa = re.sub(r"(?<!\d)d", "1d", msg_limpa)

        padrao_rolagem = r"(\d+)d(\d+)"
        rolagens = re.findall(padrao_rolagem, msg_limpa)

        for qtd, lados in rolagens:
            if int(qtd) > 100 or int(lados) > 1000:
                await message.reply("https://i.ytimg.com/vi/OuHQQdVbhKc/maxresdefault.jpg")
                return

        lista_detalhes = []
        expressao_matematica = msg_limpa

        for qtd_str, lados_str in rolagens:
            qtd, lados = int(qtd_str), int(lados_str)
            resultados, dados_str = self.rolar_dados(qtd, lados)
            soma_dados = sum(resultados)
            lista_detalhes.append(f"**{qtd}d{lados}**: {dados_str}")
            expressao_matematica = expressao_matematica.replace(f"{qtd}d{lados}", f"({soma_dados})", 1)

        try:
            total_final = eval(expressao_matematica)
        except Exception:
            return

        modificadores = re.findall(r"(?<!d)([+-]\d+)(?!\d*d)", msg_limpa)
        if modificadores:
            lista_detalhes.append(f"**Modificadores**: `{', '.join(modificadores)}`")

        # --- EMBED SIMPLES (mostrado primeiro) ---
        # só mostra o total e a expressão, igual ao Mini Kraken
        embed_simples = discord.Embed(
            description=f"**{total_final}** ← `{msg}`",
            color=COR_DOURADA
        )
        embed_simples.set_author(
            name=f"Rolagem de {message.author.display_name}",
            icon_url=message.author.display_avatar.url
        )

        # --- EMBED DETALHADO (mostrado ao expandir) ---
        # contém todos os detalhes da rolagem
        embed_detalhes = discord.Embed(
            description=f"`{msg}`",
            color=COR_DOURADA
        )
        embed_detalhes.set_author(
            name=f"Rolagem de {message.author.display_name}",
            icon_url=message.author.display_avatar.url
        )
        embed_detalhes.add_field(name="Detalhes da Expressão", value="\n".join(lista_detalhes), inline=False)
        embed_detalhes.add_field(name="Total", value=f"`{total_final}`", inline=False)

        # manda o embed simples com o botão Expandir
        # passa o embed_detalhes pro botão pra ele saber o que mostrar ao clicar
        await message.reply(embed=embed_simples, view=BotaoExpandir(embed_detalhes))


async def setup(bot):
    await bot.add_cog(Dados(bot))