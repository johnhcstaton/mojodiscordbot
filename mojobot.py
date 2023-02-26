# -*- coding: utf-8 -*-
"""
Created on Sat Sep 17 16:09:27 2022

@author: curly
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

query = YahooFantasySportsQuery(Path("./"), league_id="44246")

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
guildint = 745081422485651458
twinsid = 142
mojoBallsChannelNum = 953041430715191386
mojoIceChannelNum = 937511659189202974

client = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(client)

start_up_datetime = datetime.now()

def get_twins_last_game():
    # try statsapi, if it returns None, do it my way
    mlb_last_game = statsapi.last_game(twinsid)
    if mlb_last_game == None:
        response = requests.get('https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1',
                                params={"Content-Type": "application/json"})
        data = response.json()
        for date in data["dates"]:
            # print("--- Date:", date["date"])
            # and now through games
            for game in date["games"]:
                if game["teams"]["away"]["team"]["id"] == twinsid or game["teams"]["home"]["team"]["id"] == twinsid:
                    mlb_last_game = game["gamePk"]
                    break
    
    return mlb_last_game

mlb_last_game = get_twins_last_game()

def get_wild_last_game():
    response = requests.get('https://statsapi.web.nhl.com/api/v1/teams/30?expand=team.schedule.previous',
                            params={"Content-Type": "application/json"})
    data = response.json()
    return data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["gamePk"]

nhl_last_game = get_wild_last_game()

def get_twins_pretty_string(gameId):
    prettystring = "```" + statsapi.linescore(gameId) + "```"
    prettystring = prettystring + "```" + statsapi.game_scoring_plays(gameId) + "```"
    return prettystring

def get_wild_pretty_string(data):
    # print(data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["gamePk"])
    # gamePk = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["gamePk"]
    home_team = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["home"]["team"]["name"]
    away_team = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["away"]["team"]["name"]
    home_team_score = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["home"]["score"]
    away_team_score = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["away"]["score"]
    game_date = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["gameDate"]
    prettystring = "```" + "Last Wild Game (" + game_date + ")\n"
    prettystring = prettystring + home_team + " (H): " + str(home_team_score) + ", " + away_team + " (A): " + str(away_team_score) + "```"
    return prettystring

@tree.command(name = "twins", description = "Get the most recent Twins game results from Mojo", 
              guild=discord.Object(id=guildint)) 
async def twins_game(interaction):
    last_game = get_twins_last_game()
    if last_game == None:
        await interaction.response.send_message("MLB Stats API is still being dumb")
    else:
        await interaction.response.send_message(get_twins_pretty_string(last_game))
  
@tree.command(name = "wild", description = "Get the most recent Wild game results from Mojo", 
              guild=discord.Object(id=guildint)) 
async def wild_game(interaction):  
    response = requests.get('https://statsapi.web.nhl.com/api/v1/teams/30?expand=team.schedule.previous',
                            params={"Content-Type": "application/json"})
    data = response.json()
    await interaction.response.send_message(get_wild_pretty_string(data))

@tree.command(name = "league_standings", description = "Get the MIT league standings from Mojo", 
              guild=discord.Object(id=guildint)) 
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
     
@tree.command(name = "uptime", description = "See how long Mojo has been running", 
              guild=discord.Object(id=guildint)) 
async def uptime(interaction):
    await interaction.response.send_message(datetime.now() - start_up_datetime)
    
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    
    guild = discord.utils.get(client.guilds, name=GUILD)
    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

    # members = '\n - '.join([member.name for member in guild.members])
    # print(f'Guild Members:\n - {members}')
    
    # mojoTestChannel = client.get_channel(1020801404354449588)
    # await mojoTestChannel.send('MojoBot is Online')

    await tree.sync(guild=discord.Object(id=guildint))
    
    background_thread.start()

@tasks.loop(seconds=180.0)
async def background_thread():
    # twins score
    global mlb_last_game
    last_twins_game = get_twins_last_game()
    if last_twins_game != None and mlb_last_game != last_twins_game:
        mlb_last_game = last_twins_game
        mojoBallsChannel = client.get_channel(mojoBallsChannelNum)
        await mojoBallsChannel.send(get_twins_pretty_string(last_twins_game))
        
    # wild score
    global nhl_last_game
    last_wild_game = get_wild_last_game()
    if last_wild_game != None and nhl_last_game != last_wild_game:
        nhl_last_game = last_wild_game
        mojoIceChannel = client.get_channel(mojoIceChannelNum)
        response = requests.get('https://statsapi.web.nhl.com/api/v1/teams/30?expand=team.schedule.previous',
                                params={"Content-Type": "application/json"})
        data = response.json()
        await mojoIceChannel.send(get_wild_pretty_string(data))
        
@client.event
async def on_message(message):
    # print(f'message seen {message.content}')
    if message.author == client.user:
        return

    brooklyn_99_quotes = [
        'I\'m the human form of the 💯 emoji.',
        'Bingpot!',
        (
            'Cool. Cool cool cool cool cool cool cool, '
            'no doubt no doubt no doubt no doubt.'
        ),
    ]

    if message.content == '99!':
        response = random.choice(brooklyn_99_quotes)
        await message.channel.send(response)
        
    if message.content == ('zeke'):
        response = "Zeke Zeke Zeke"
        await message.channel.send(response)
        
    if message.content == 'Praise Mojo':
        response = "I bless you, my child."
        await message.channel.send(response)         
    
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
                    # print(str(home_score) + ", " + str(away_score))
                    if(len(players) <= 0):
                        players = used_players.copy()
                        used_players.clear()
                    # pick a random player
                    rand = random.randint(0, len(players)-1)
                    player = list(players)[rand]
                    # print(player)
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
    
