import discord
import random
import re
from discord.ext import commands

# Dicionário que vai guardar os paineis ativos por server; chave: guild.id, valor: dicionario com dados do combate

paineis_ativos = {}

class ModalIniciativa(discord.ui.Modal, title="Initiative Roll"):
    """Modal que aparece quando o jogador clica em Entrar"""

    dado = discord.ui.TextInput(
        label="Initiative Dice",
        default="1d20",
        required=True
    )

    nome = discord.ui.TextInput(
        label="Character Name",
        placeholder="Ex: Alain Rezz",
        required=True
    )

    def __init__ (self, view_painel):
        super().__init__()
        self.view_painel= view_painel # Referência ao painal para atualizar depois


    async def on_submit(self, interaction: discord.Interaction):
        expressao = self.dado.value.strip().lower()
        nome_personagem = self.nome.value.strip()


        # Validar e rodar o dado
        padrao = re.fullmatch(r"(\d+)d(\d+)([+-]\d+)?", expressao)
        if not padrao:
            await interaction.response.send_message("Expressão de dado inválida", ephemeral=True)
            return

        qtd = int(padrao.group(1))
        lados = int(padrao.group(2))
        bonus = int(padrao.group(3)) if padrao.group(3) else 0

        if qtd > 10 or lados > 100:
            await interaction.response.send_message("Limite de valores", ephemeral=True)
            return

        resultados = [random.randint(1, lados) for _ in range(qtd)]
        total = sum(resultados) + bonus

        guild_id = interaction.guild.id

        #adiciona/atualiza o perso na lista do servidor

        if guild_id not in paineis_ativos:
            paineis_ativos[guild_id] = {"jogadores": [], "turno_atual": 0, "rodada": 1}

        jogadores = paineis_ativos[guild_id]["jogadores"]

        #se o jogador já entrou, atualiza
        jogadores.append({
            "user_id": interaction.user.id,
            "nome": nome_personagem,
            "iniciativa": total,
            "rolagem": resultados
        })

        # ordem de iniciativa decrescente
        paineis_ativos[guild_id]["jogadores"] = sorted(jogadores, key=lambda x: x["iniciativa"], reverse=True)

        await interaction.response.send_message(
            f"**{nome_personagem}** entrou com iniciativa **{total}** {resultados}",
        ephemeral=True
        )

        await self.view_painel.atualizar_painel()

class SelectRemover(discord.ui.Select):
    def __init__(self, jogadores, view_painel):
        self.view_painel = view_painel
        opcoes = [
            discord.SelectOption(label=j["nome"], value=str(i))
            for i, j, in enumerate(jogadores)
        ]
        super().__init__(placeholder="Select the player to be removed", options=opcoes)

    async def callback(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        index = int(self.values[0])
        dados = paineis_ativos.get(guild_id)
        if not dados:
            await interaction.response.send_message("Nenhum combate ativo", ephemeral=True)
            return
        removido = dados["jogadores"].pop(index)
        await interaction.response.send_message(f"**{removido['nome']}** removido.", ephemeral=True)
        await self.view_painel.atualizar_painel()

class ViewRemover(discord.ui.View):
    def __init__(self, jogadores, view_painel):
        super().__init__(timeout=30)
        self.add_item(SelectRemover(jogadores, view_painel))
class PainelIniciativa(discord.ui.View):
    """Painel principal ccm os botões"""

    def __init__(self, message=None, guild_id=None):
        super().__init__(timeout=None) 
        self.message = message
        self.guild_id = guild_id

    async def atualizar_painel(self):
        """edita a mensagem do painel com a lista atualizada"""
        if not self.message:
            return

        dados = paineis_ativos.get(self.guild_id, {"jogadores": [], "turno_atual": 0, "rodada": 1})
        embed = montar_embed(dados)
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="+ Entrar", style=discord.ButtonStyle.primary)
    async def entrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Abre o modal quando o jogador clica em Entrar"""
        await interaction.response.send_modal(ModalIniciativa(view_painel=self))

    @discord.ui.button(label="▶ Próximo", style=discord.ButtonStyle.success)
    async def proximo(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Avança para o próximo turno"""
        dados = paineis_ativos.get(self.guild_id)
        if not dados or not dados["jogadores"]:
            await interaction.response.send_message("Nenhum jogador na iniciativa", ephemeral=True)
            return

        dados["turno_atual"] = (dados["turno_atual"] + 1) % len(dados["jogadores"])

        # se voltou pro inicio, avança pra prox rodada
        if dados["turno_atual"] == 0:
            dados["rodada"] += 1

        await interaction.response.defer()
        await self.atualizar_painel()

    @discord.ui.button(label="✖ Remover", style=discord.ButtonStyle.secondary)
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        dados = paineis_ativos.get(self.guild_id)
        if not dados or not dados["jogadores"]:
            await interaction.response.send_message("Nenhum jogador na iniciativa.", ephemeral=True)
            return

        view_remover = ViewRemover(dados["jogadores"], self)
        await interaction.response.send_message("Selecione quem remover", view=view_remover, ephemeral=True)

    @discord.ui.button(label="↺ Resetar", style=discord.ButtonStyle.danger)
    async def resetar(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reseta o combate"""
        paineis_ativos[self.guild_id] = {"jogadores": [], "turno_atual": 0, "rodada": 1}
        await interaction.response.defer()
        await self.atualizar_painel()

def montar_embed(dados):
    """Monta o embed do painel com a lista de iniciativa"""
    jogadores = dados["jogadores"]
    turno_atual = dados["turno_atual"]
    rodada = dados["rodada"]

    embed = discord.Embed(
        title="Initiative Roll Helper",
        color=discord.Color.from_str("#D4AF37")
    )

    embed.add_field(name="Rodada", value=str(rodada), inline=True)

    if not jogadores:
        embed.description = "```...```"
        return embed

    linhas = []
    for i, j in enumerate(jogadores):
        prefixo = "▶ " if i == turno_atual else " "
        linhas.append(f"{prefixo}**{j['iniciativa']}** - {j['nome']}")

    embed.description = "\n".join(linhas)
    return embed


class Iniciativa(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content.strip().lower() != "tciniciativa":
            return

        guild_id = message.guild.id

        paineis_ativos[guild_id] = {"jogadores": [], "turno_atual": 0, "rodada": 1}

        dados = paineis_ativos[guild_id]
        embed = montar_embed(dados)

        view = PainelIniciativa(guild_id=guild_id)

        msg = await message.channel.send(embed=embed, view=view)
        view.message = msg

        await message.delete()

async def setup(bot):
    await bot.add_cog(Iniciativa(bot))