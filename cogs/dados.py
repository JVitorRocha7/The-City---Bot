from discord.ext import commands

async def setup(bot):
    pass

import discord
import random
import re           # biblioteca para expressões regulares (detectar padrões de texto)
from discord import app_commands
from discord.ext import commands

class Dados(commands.cog): # cog é um módulo que agrupa comandos relacionados
    def __init__(self, bot):
        self.bot = bot #guarda a referência do bot pra usar dentro da classe


    @commands.Cog.listener() #decorator que registra o metodo como um listener de evento
    async def on_message(self, message): #disparado toda vez que algué manda uma mensagem

        #ignora mensagens do próprio bot para não entrar em loop infinito
        if message.author.bot:
            return

       # regex que detecta o padrão NdM, NdM+x ou NdM-x
       # \d+ = um ou mais digitos
       # d   = a letra "d" literal
       # ([+-]\d+)? = bônus opcional (ex: +3 ou -2)
       # fullmatch = a mensagem tem que ser esse padrão, nada mais
       padrao = re.fullmatch(r"(\d+)d(d\d+)([+-]\d+)?", message.content.strip().lower())

       # se a mensagem nao for uma rolagem de dado, ignora
       if not padrao:
            return

       # extrai os grupos capturados pelo regex 
       qtd = int(padrao.group(1)) # quantia de dados
       lados = int(padrao.group(2)) # lados do dado
       bonus = int(padrao.group(3)) if padrao.group(3) else 0 #bônus, 0 se não tiver

       # limite para evitar spam ou travamento
       if qtd > 100 or lados >1000:
            await message.reply("Executor da Garra á caminho.")
            return

       # rola cada dado indivualmente e guarda os resultados numa lista
       resultados = [random.randint(1, lados) for _ in range(qtd)]

       # soma todos os resultados e adiciona o bônus
       total = sum(resultados) + bonus

       #formata a string do bÔnus
       bonus_str = f" + {bonus}" if bonus > 0 else (f" - {abs(bonus)}" if bonus < 0 else "")

       # montar a mensagem
       await message.reply(f"{resultados}{bonus_str} = **{total}**")

# função obrigatória que o discord.py chama ao carregar a cog
async def setup(bot):
    await bot.add_cog(Dados(bot))

    

    

    