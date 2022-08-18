import re
import requests
import time
import json
import urllib.parse
import datetime
import math
from prettytable import PrettyTable
 

LIVE_STATS_API = '/api/get_live_game_stats'
PUBLIC_INFO = '/api/public_info'
SCOREBOARD_MAPS = '/api/get_scoreboard_maps'
SCOREBOARD = '/api/get_map_scoreboard?map_id={}'
MAP_TO_PICTURE = {
  'carentan': "carentan.webp",
  'foy': "foy.webp",
  'hill400': "hill400.webp",
  'hurtgenforest': "hurtgen.webp",
  'omahabeach': "omaha.webp",
  'purpleheartlane': "phl.webp",
  'stmariedumont': "smdm.webp",
  'stmereeglise': "sme.webp",
  'utahbeach': "utah.webp",
  'kursk': "kursk.webp",
  'stalingrad': "stalingrad.webp",
}
class DateTimeEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, datetime.datetime):
            return (str(z))
        else:
            return super().default(z)
def getLiveStats(server):
    publicInfo = getPublicInfo(server)
    url = server['base-rcon-url'] + LIVE_STATS_API
    req = requests.get(url)
    content = req.text
    data = json.loads(content)
    if data:
        result = data.get('result')
        if result:
            stats = result.get('stats')
            liveStats = getTop10s(stats)
            liveStats['table'] = createTable(stats)
            liveStats['public_info'] = publicInfo
            #with open(server['name'] + "-live-stats.json", "w") as outfile:
            #    jsonStr = json.dumps(liveStats, indent=4, cls=DateTimeEncoder)
            #    outfile.write(jsonStr)
            return liveStats
    return None

def getTop10s(stats):
    liveStats = {}
    liveStats['top10-kills'] = getTop10(stats, get_kills)
    liveStats['top10-kdr'] = getTop10(stats, get_kdr)
    liveStats['top10-kpm'] = getTop10(stats, get_kpm)
    liveStats['top10-deaths'] = getTop10(stats, get_deaths)
    liveStats['top10-killstreak'] = getTop10(stats, get_killstreak)
    liveStats['top10-deathstreak'] = getTop10(stats, get_deathstreak)
    return liveStats

def createTable(players):
    sortedPlayers = list(players)
    sortedPlayers.sort(key=get_kills, reverse=True)

    myTable = PrettyTable([
            "Name", 
            "Kills",
            "Deaths",
            "K/D",
            "Max kill streak",
            "Kill(s) / minute",
            "Death(s) / minute",
            "Max death streak",
            "Max TK streak",
            "Death by TK",
            "Death by TK Streak",
            "(aprox.) Longest life min.",
            "(aprox.) Shortest life secs.",
            "Nemesis",
            "Victim",
            "Weapons"])
    for player in sortedPlayers:
        nemesisLine = None
        if player['death_by']:
            nemesis = list(player['death_by'])[0]
            nemesisLine = nemesis + ': ' + str(player['death_by'][nemesis])
        victimLine = None
        if player['most_killed']:
            victim = list(player['most_killed'])[0]
            victimLine = victim + ': ' + str(player['most_killed'][victim])
        weapons = []
        if player['weapons']:
            for key, value in player['weapons'].items():
                weapons.append(key + ': ' + str(value))
        myTable.add_row(
            [ 
            player['player'], 
            player['kills'], 
            player['deaths'], 
            player['kill_death_ratio'], 
            player['kills_streak'], 
            player['kills_per_minute'], 
            player['deaths_per_minute'], 
            player['deaths_without_kill_streak'], 
            player['teamkills_streak'], 
            player['deaths_by_tk'], 
            player['deaths_by_tk_streak'], 
            player['longest_life_secs'], 
            player['shortest_life_secs'], 
            nemesisLine, 
            victimLine,
            " ".join(weapons)
            ]
        )
    return str(myTable)

def getPublicInfo(server):
    url = server['base-rcon-url'] + PUBLIC_INFO
    req = requests.get(url)
    content = req.text
    public_info = json.loads(content)
    #with open("public-info.json", "w") as outfile:
    #    jsonStr = json.dumps(public_info, indent=4)
    #    outfile.write(jsonStr)
    result = public_info.get('result')
    current_map = result.get('current_map')
    timestamp = datetime.datetime.fromtimestamp(current_map.get('start'))
    now = datetime.datetime.now()
    time_diff = now - timestamp
    tsecs = time_diff.total_seconds()
    tmins = math.floor(tsecs/60)
    publicInfo = {}
    publicInfo['name'] = result.get('name')
    publicInfo['start'] = timestamp
    publicInfo['minutes_elapsed'] = tmins
    publicInfo['player_count'] = result.get('player_count')
    publicInfo['nb_players'] = result.get('nb_players')
    publicInfo['map-human-name'] = current_map.get('human_name')
    publicInfo['next-map'] = result.get('next_map')
    publicInfo['just_name'] = current_map.get('just_name')
    mapImage = MAP_TO_PICTURE.get(current_map.get('just_name'))
    if mapImage != None:
        publicInfo['map-image-url'] = "https://raw.githubusercontent.com/MarechJ/hll_rcon_tool/master/rcongui/public/maps/" + mapImage
    else:
        publicInfo['map-image-url'] = None
    return publicInfo

def getGames(server, lastGameId):
    url = server['base-rcon-url'] + SCOREBOARD_MAPS
    req = requests.get(url)
    content = req.text
    scoreboardMaps = json.loads(content)
    #with open("scoreboardMaps.json", "w") as outfile:
    #    jsonStr = json.dumps(scoreboardMaps, indent=4)
    #    outfile.write(jsonStr)
    if scoreboardMaps and scoreboardMaps.get('result') and scoreboardMaps.get('result').get('maps'):
        maps = scoreboardMaps.get('result').get('maps')
        if lastGameId:
            maps = list(filter(lambda map: map.get('id') > lastGameId, maps))
        maps.sort(key=getId, reverse=False)
        if maps:
            servername = getServerName(server)
        allStats = list(map(lambda game: getGameStats(server, game, servername), maps))
        #with open(server['name'] + "-all-stats.json", "w") as outfile:
        #    jsonStr = json.dumps(allStats, indent=4, cls=DateTimeEncoder)
        #    outfile.write(jsonStr)
        return allStats
    return None

def getServerName(server):
    url = server['base-rcon-url'] + PUBLIC_INFO
    req = requests.get(url)
    content = req.text
    public_info = json.loads(content)
    if public_info and public_info.get('result'):
        return public_info.get('result').get('name')
    return None

def getId(element):
    return element['id']

def getGameStats(server, game, servername):
    url = server['base-rcon-url'] + SCOREBOARD.format(game.get('id'))
    print('Looking for a game: ' + url)
    req = requests.get(url)
    content = req.text
    stats = json.loads(content)
    #with open("scoreboard.json", "w") as outfile:
    #    jsonStr = json.dumps(stats, indent=4)
    #    outfile.write(jsonStr)
    if stats and stats.get('result'):
        result = stats.get('result')
        gameStats = {}
        gameStats['server_name'] = servername
        gameStats['id'] = result.get('id')
        gameStats['start'] = datetime.datetime.fromisoformat(game.get('start'))
        gameStats['end'] = datetime.datetime.fromisoformat(game.get('end'))

        gameStats['map-human-name'] = game.get('long_name')
        gameStats['just_name'] = game.get('just_name')
        mapImage = MAP_TO_PICTURE.get(game.get('just_name'))
        if mapImage != None:
            gameStats['map-image-url'] = "https://raw.githubusercontent.com/MarechJ/hll_rcon_tool/master/rcongui/public/maps/" + mapImage
        else:
            gameStats['map-image-url'] = None

        gameStats['top10s'] = getTop10s(result.get('player_stats'))
        gameStats['players_stats'] = result.get('player_stats')
        gameStats['table'] = createTable(result.get('player_stats'))
        return gameStats
    return None


def getTop10(stats, sortMethod):
    if stats != None:
        coreStats = list(map(lambda player: {'player': player['player'], 'value' : sortMethod(player)}, stats))
        coreStats.sort(key=get_value, reverse=True)
        top10 = coreStats[:10]
        return top10
    return None

def get_value(element):
    return element['value']
def get_kills(element):
    return element['kills']
def get_kdr(element):
    return element['kill_death_ratio']
def get_kpm(element):
    return element['kills_per_minute']
def get_deaths(element):
    return element['deaths']
def get_killstreak(element):
    return element['kills_streak']
def get_deathstreak(element):
    return element['deaths_without_kill_streak']
