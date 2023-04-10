# -*- coding: utf-8 -*-
"""
Created on Tue Mar 14 14:45:13 2023

@author: John HC Staton
"""
import statsapi
import requests
from datetime import datetime

TWINS_ID = 142
WILD_ID = 30
MLB_URL = 'https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1'
NHL_URL = 'https://statsapi.web.nhl.com/api/v1/teams/' + str(WILD_ID) + '?expand=team.schedule.previous'
NHL_STANDINGS_URL = 'https://statsapi.web.nhl.com/api/v1/standings'

class convenience:
    
    # Convenience function to get nice string output of the MLB standings
    def get_twins_standings():
        today = datetime.now()
        year = today.year
        month = '{:02d}'.format(today.month)
        day = '{:02d}'.format(today.day)
        return statsapi.standings(leagueId="103", division="all", include_wildcard=True, season=None, standingsTypes=None, date=month + "/" + day + "/" + str(year))
    
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
    
    # Convenience function to get nice string output of the NHL (Wild's division specifically) standings
    def get_wild_standings():
        response = requests.get(NHL_STANDINGS_URL, params={"Content-Type": "application/json"})
        data = response.json()
        return_string = ""
        division = data["records"][2]["division"]["name"]
        conference = data["records"][2]["conference"]["name"]
        return_string = return_string + division + " Division - " + conference + " Conference\n"
        rank = 1
        for team in data["records"][2]["teamRecords"]:
            team_name = team["team"]["name"]
            team_wins = str(team["leagueRecord"]["wins"])
            team_losses = str(team["leagueRecord"]["losses"])
            team_ot = str(team["leagueRecord"]["ot"])
            team_pts = str(team["points"])
            return_string = return_string + str(rank) + ") " + team_name + " ("
            return_string = return_string + team_wins + "-" + team_losses + "-"
            return_string = return_string + team_ot + " " + team_pts + "pts)\n"
            rank = rank + 1
        return return_string
        
    # Convenience function to get the ID number of the most recent Wild game
    def get_wild_last_game():
        response = requests.get(NHL_URL, params={"Content-Type": "application/json"})
        data = response.json()
        return data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["gamePk"]
    
    # Convenience function to get a nice string output of the results of the Twins game with gameId
    def get_twins_pretty_string(gameId):
        boxscore_data = statsapi.boxscore_data(gameId, timecode=None)
        away = boxscore_data["teamInfo"]["away"]["teamName"].replace(' ', '-').lower()
        home = boxscore_data["teamInfo"]["home"]["teamName"].replace(' ', '-').lower()
        
        away_runs = boxscore_data["away"]["teamStats"]["batting"]["runs"]
        home_runs = boxscore_data["home"]["teamStats"]["batting"]["runs"]
        
        prettystring = ""
        if (away == "twins" and away_runs > home_runs) or (home == "twins" and home_runs > away_runs) :
            prettystring = "<:twins:1084666898777636935> Twins win! <:twinsM:1084667299803447326>\n"
            
        # linescore
        linescore = statsapi.linescore(gameId)
        prettystring = prettystring + "```" + linescore + "```"
        
        # Trying it without showing the scoring plays, so as to take up less screenspace
        # prettystring = prettystring + "```" + statsapi.game_scoring_plays(gameId) + "```"
        
        # link to the official mlb wrapup for the game
        today = datetime.now()
        year = today.year
        month = '{:02d}'.format(today.month)
        day = '{:02d}'.format(today.day)
    
        wrap_url = "https://www.mlb.com/gameday/" + away + "-vs-" + home + "/" + str(year) + "/" + str(month) + "/" + str(day) + "/" + str(gameId) + "/final/wrap"
    
        prettystring = prettystring + "MLB Wrap Up: " + wrap_url
        
        return prettystring
    
    # TODO - Make nicer.  Right now it's just
    # Last Wild Game (2023-02-26T19:00:00Z)
    # Minnesota Wild (H): 3, Columbus Blue Jackets (A): 2
    # for example.  The MLB statsapi wrappers for linescore and game_scoring_plays makes a much nice
    # results string, and I'd like something like that for this.
    # Convenience function to get a nice string output of the results of the Wild game with json data
    def get_wild_pretty_string(gameId):
        response = requests.get(NHL_URL, params={"Content-Type": "application/json"})
        data = response.json()
        
        home_team = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["home"]["team"]["name"]
        away_team = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["away"]["team"]["name"]
        home_team_score = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["home"]["score"]
        away_team_score = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["teams"]["away"]["score"]
        
        prettystring = ""
        
        if (home_team == "Minnesota Wild" and home_team_score > away_team_score) or (away_team == "Minnesota Wild" and away_team_score > home_team_score) :
            prettystring = "<:wild:1084667743233646632> Wild win! <:wild:1084667743233646632>\n"
            
        game_date = data["teams"][0]["previousGameSchedule"]["dates"][0]["games"][0]["gameDate"]
        prettystring = prettystring + "```" + "Last Wild Game (" + game_date + ")\n"
        
        prettystring = prettystring + home_team + " (H): " + str(home_team_score) + ", " + away_team + " (A): " + str(away_team_score) + "```"
    
            
        gamecenter_url = "https://www.nhl.com/gamecenter/" + str(gameId)    
        prettystring = prettystring + "NHL Gamecenter: " + gamecenter_url
        return prettystring
    
