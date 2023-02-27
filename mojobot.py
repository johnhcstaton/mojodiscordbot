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
import requests
from pathlib import Path
from yfpy.query import YahooFantasySportsQuery
from discord.ext import tasks

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_INT = os.getenv('DISCORD_GUILD_INT')
MOJO_BASEBALL_CHANNEL_NUM = os.getenv('DISCORD_BASEBALL_CHANNEL')
MOJO_ICE_CHANNEL_NUM = os.getenv('DISCORD_HOCKEY_CHANNEL')
YAHOO_LEAGUE_ID = os.getenv('YAHOO_LEAGUE_ID')
MLB_URL = 'https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1'
TWINS_ID = 142
WILD_ID = 30
NHL_URL = 'https://statsapi.web.nhl.com/api/v1/teams/' + str(WILD_ID) + '?expand=team.schedule.previous'
BACKGROUND_LOOP_TIME = 180.0

query = YahooFantasySportsQuery(Path("./"), league_id=YAHOO_LEAGUE_ID)

client = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(client)

start_up_datetime = datetime.now()

# Convenience function to get the ID number of the most recent Twins game
def get_twins_last_game():
    # try statsapi, if it returns None, do it my way
    mlb_last_game = statsapi.last_game(TWINS_ID)
    if mlb_last_game == None:
        response = requests.get(MLB_URL, params={"Content-Type": "application/json"})
        data = response.json()
        for date in data["dates"]:
            # and now through games
            for game in date["games"]:
                if game["teams"]["away"]["team"]["id"] == TWINS_ID or game["teams"]["home"]["team"]["id"] == TWINS_ID:
                    mlb_last_game = game["gamePk"]
                    break
    
    return mlb_last_game

mlb_last_game = get_twins_last_game()

# Convenience function to get the ID number of the most recent Wild game
def get_wild_last_game():
    response = requests.get(NHL_URL, params={"Content-Type": "application/json"})
    data = response.json()
    return data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["gamePk"]

nhl_last_game = get_wild_last_game()

# Convenience function to get a nice string output of the results of the Twins game with gameId
def get_twins_pretty_string(gameId):
    prettystring = "```" + statsapi.linescore(gameId) + "```"
    prettystring = prettystring + "```" + statsapi.game_scoring_plays(gameId) + "```"
    return prettystring

# Convenience function to get a nice string output of the results of the Wild game with json data
def get_wild_pretty_string(data):
    home_team = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["home"]["team"]["name"]
    away_team = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["away"]["team"]["name"]
    home_team_score = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["home"]["score"]
    away_team_score = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["away"]["score"]
    game_date = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["gameDate"]
    prettystring = "```" + "Last Wild Game (" + game_date + ")\n"
    prettystring = prettystring + home_team + " (H): " + str(home_team_score) + ", " + away_team + " (A): " + str(away_team_score) + "```"
    return prettystring

# Discord slash command to "Get the most recent Twins game results from Mojo"
@tree.command(name = "twins", description = "Get the most recent Twins game results from Mojo", 
              guild=discord.Object(id=GUILD_INT)) 
async def twins_game(interaction):
    last_game = get_twins_last_game()
    if last_game == None:
        # This is here because MLB broke the statsapi.last_game call in the 2023 Spring Training
        await interaction.response.send_message("MLB Stats API is still being dumb")
    else:
        await interaction.response.send_message(get_twins_pretty_string(last_game))
  
# Discord slash command to "Get the most recent Wild game results from Mojo"
@tree.command(name = "wild", description = "Get the most recent Wild game results from Mojo", 
              guild=discord.Object(id=GUILD_INT)) 
async def wild_game(interaction):  
    response = requests.get(NHL_URL, params={"Content-Type": "application/json"})
    data = response.json()
    await interaction.response.send_message(get_wild_pretty_string(data))

# Discord slash command to "Get the MIT league standings from Mojo"
@tree.command(name = "league_standings", description = "Get the MIT league standings from Mojo", 
              guild=discord.Object(id=GUILD_INT)) 
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
              guild=discord.Object(id=GUILD_INT)) 
async def uptime(interaction):
    await interaction.response.send_message(datetime.now() - start_up_datetime)

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
@tasks.loop(seconds=BACKGROUND_LOOP_TIME)
async def background_thread():
    # twins score
    global mlb_last_game
    last_twins_game = get_twins_last_game()
    if last_twins_game != None and mlb_last_game != last_twins_game:
        mlb_last_game = last_twins_game
        mojoBaseballChannel = client.get_channel(MOJO_BASEBALL_CHANNEL_NUM)
        await mojoBaseballChannel.send(get_twins_pretty_string(last_twins_game))
        
    # wild score
    global nhl_last_game
    last_wild_game = get_wild_last_game()
    if last_wild_game != None and nhl_last_game != last_wild_game:
        nhl_last_game = last_wild_game
        mojoIceChannel = client.get_channel(MOJO_ICE_CHANNEL_NUM)
        response = requests.get(NHL_URL, params={"Content-Type": "application/json"})
        data = response.json()
        await mojoIceChannel.send(get_wild_pretty_string(data))

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
    
    # TODO - Make into a proper slash command
    # Return a "betting board" (aka "squares") for the given collection of players
    if message.content.startswith('-mojobettingboard'):
        names_substring = message.content.replace('-mojobettingboard', '')
        players = names_substring.split(',')
        if len(players) > 1:
            await message.channel.send("Generating Betting Board for " + str(players))
            
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
                    
            
            prettystring = ""
            for player in assignments.keys():
                prettystring = prettystring + player + "->" + str(assignments[player]) + " - $" + str(len(assignments[player]))
                prettystring = prettystring + "\n"
                
            await message.channel.send("```" + 
                                       prettystring + 
                                       "```")
        else:
            await message.channel.send("Not enough names given!")

client.run(TOKEN)
    