# -*- coding: utf-8 -*-
"""
Created on Sat Sep 17 16:09:27 2022

@author: John HC Staton
"""

import os
import random
import discord
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime
import statsapi
from pathlib import Path
from yfpy.query import YahooFantasySportsQuery
from discord.ext import tasks
import openai
from convenience import convenience

# load environment variables and setup global vars
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_INT = os.getenv('DISCORD_GUILD_INT')
MOJO_BASEBALL_CHANNEL_NUM = int(os.getenv('DISCORD_BASEBALL_CHANNEL'))
MOJO_ICE_CHANNEL_NUM = int(os.getenv('DISCORD_HOCKEY_CHANNEL'))
YAHOO_LEAGUE_ID = os.getenv('YAHOO_LEAGUE_ID')
openai.api_key = os.getenv('OPENAI_API_KEY')
BACKGROUND_LOOP_TIME = 180.0

query = YahooFantasySportsQuery(Path("./"), league_id=YAHOO_LEAGUE_ID)

client = discord.Client(intents=discord.Intents.all())
guild = discord.Object(id=GUILD_INT)
tree = app_commands.CommandTree(client)

start_up_datetime = datetime.now()

# Set up the model
model_engine = "text-davinci-003"

mlb_last_game = convenience.get_twins_last_game()
nhl_last_game = convenience.get_wild_last_game()

# ----------------------------------------------------------------------------
# Discord Slash Commands
# ----------------------------------------------------------------------------

# Discord slash command to "Talk to Mojo about anything (powered by ChatGPT)"
@tree.command(name = "chat", description = "Talk to Mojo about anything (powered by ChatGPT)", guild = guild)
async def mojo_chat(interaction, prompt: str):
    await interaction.response.defer()
    # Generate a chat gpt response
    completion = openai.Completion.create(
        engine=model_engine,
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5,
    )

    response = completion.choices[0].text
    
    prettystring = "```Responding to: \n\"" + prompt + "\"\n\n"
    prettystring = prettystring + "Mojo says: " + response + "```"
    await interaction.followup.send(prettystring)

# Discord slash command to "Get the most recent Twins game results from Mojo"
@tree.command(name = "twins", description = "Get the most recent Twins game results from Mojo", 
              guild = guild) 
async def twins_game(interaction):
    last_game = convenience.get_twins_last_game()
    if last_game == None:
        # This is here because MLB broke the statsapi.last_game call in the 2023 Spring Training
        await interaction.response.send_message("MLB Stats API is still being dumb")
    else:
        await interaction.response.send_message(convenience.get_twins_pretty_string(last_game))
  
# Discord slash command to "Get the most recent Twins standings from Mojo"
@tree.command(name = "twins_standings", description = "Get the most recent Twins standings from Mojo", 
              guild = guild) 
async def twins_standings(interaction):
    standings = convenience.get_twins_standings()
    prettystring = "```" + standings + "```"
    await interaction.response.send_message(prettystring)
    
# Discord slash command to "Get the most recent Wild standings from Mojo"
@tree.command(name = "wild_standings", description = "Get the most recent Wild standings from Mojo", 
              guild = guild) 
async def wild_standings(interaction):
    standings = convenience.get_wild_standings()
    prettystring = "```" + standings + "```"
    await interaction.response.send_message(prettystring)
    
# Discord slash command to "Get the most recent Wild game results from Mojo"
@tree.command(name = "wild", description = "Get the most recent Wild game results from Mojo", 
              guild = guild) 
async def wild_game(interaction):  
    last_game = convenience.get_wild_last_game()
    await interaction.response.send_message(convenience.get_wild_pretty_string(last_game))

# Discord slash command to "Get the MIT league standings from Mojo"
@tree.command(name = "league_standings", description = "Get the MIT league standings from Mojo", 
              guild = guild) 
async def league_standings(interaction):
    standings = query.get_league_standings()
    teams = standings.teams
    prettystring = "```"
    for team in teams:
        prettystring = prettystring + str(team["team"].rank) + " " + team["team"].name.decode('UTF-8') + " "
        prettystring = prettystring + "(" + str(team["team"].wins) + "-" + str(team["team"].losses) + "-" + str(team["team"].ties) + ")"
        prettystring = prettystring + "\n"
    prettystring = prettystring + "```"
    await interaction.response.send_message(prettystring)
     
# Discord slash command to "See how long Mojo has been running"
@tree.command(name = "uptime", description = "See how long Mojo has been running", 
              guild = guild) 
async def uptime(interaction):
    await interaction.response.send_message(datetime.now() - start_up_datetime)

# Discord slash command to "Return a "betting board" (aka "squares") for the given collection of players"
@tree.command(name = "board", 
              description = "Return a \"betting board\" (aka \"squares\") for the given collection of players", 
              guild = guild)
async def betting_board(interaction, names: str):
    players = names.replace(" ", "").split(',')
    if len(players) > 1:
        prettystring = "Generating Betting Board for " + str(players) + "\n"
        
        used_players = []

        assignments = dict()

        for player in players:
            assignments[player] = []

        for home_score in range(10):
            for away_score in range(10):
                if(len(players) <= 0):
                    players = used_players.copy()
                    used_players.clear()
                # pick a random player
                rand = random.randint(0, len(players)-1)
                player = list(players)[rand]
                # add the numbers to their assignments
                players_assignments = assignments[player]
                players_assignments.append(str(home_score) + " " + str(away_score))
                # remove from players and put in used_players
                used_players.append(player)
                players.remove(player)
                
        
        
        for player in assignments.keys():
            prettystring = prettystring + player + "->" + str(assignments[player]) + " - $" + str(len(assignments[player]))
            prettystring = prettystring + "\n"
            
        await interaction.response.send_message("```" + 
                                               prettystring + 
                                               "```")
    else:
        await interaction.response.send_message("Not enough names given!")
    
# ----------------------------------------------------------------------------
# Discord on_ready, background_thread, and on_message
# ----------------------------------------------------------------------------

# Discord on_ready (essentially on bot startup/connection to Discord)
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    
    guild = discord.utils.get(client.guilds, name=GUILD)
    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

    await tree.sync(guild=discord.Object(id=GUILD_INT))
    
    background_thread.start()

# Discord Approved (tm) background thread to check for Twins/Wild game results
@tasks.loop(seconds = BACKGROUND_LOOP_TIME)
async def background_thread():
    # twins score
    global mlb_last_game
    last_twins_game = convenience.get_twins_last_game()
    if last_twins_game != None and mlb_last_game != last_twins_game:
        # another check
        linescore = statsapi.linescore(last_twins_game)
        # have to check for Final because MLB updates last_game before the game
        # even starts AND updates game_scoring_plays during the game, so *only*
        # post the final score
        if "Final" in linescore:
            mlb_last_game = last_twins_game
            mojoBaseballChannel = client.get_channel(MOJO_BASEBALL_CHANNEL_NUM)
            await mojoBaseballChannel.send(convenience.get_twins_pretty_string(last_twins_game))
        
    # wild score
    global nhl_last_game
    last_wild_game = convenience.get_wild_last_game()
    if last_wild_game != None and nhl_last_game != last_wild_game:
        nhl_last_game = last_wild_game
        mojoIceChannel = client.get_channel(MOJO_ICE_CHANNEL_NUM)
        await mojoIceChannel.send(convenience.get_wild_pretty_string(nhl_last_game))

# Baby's first Discord bot responses to on_message, slash commands is the officially preferred method
@client.event
async def on_message(message):
    if message.author == client.user:
        return
        
    if 'Zeke' in message.content or 'zeke' in message.content:
        response = "Zeke Zeke Zeke"
        await message.channel.send(response)
        
    if ('Praise Mojo' in message.content or 'praise Mojo' in message.content or
        'praise mojo' in message.content or 'Praise mojo' in message.content):
        response = "I bless you, my child."
        await message.channel.send(response)

client.run(TOKEN)
    
