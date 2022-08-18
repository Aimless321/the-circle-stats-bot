# bot.py
import os
import json
import discord
from discord.ext import commands
import datetime
import stats
import math

configFile = 'config.json'
runtimeFile = 'runtime.json'
actualGuild = None

intents = discord.Intents.default()
bot = commands.Bot(intents=intents, command_prefix='stats')


def log(message):
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + message)
def getRuntimeConfiguration():
    if os.path.exists(runtimeFile):
        f = open(runtimeFile)
        runtime = json.load(f)
    else:
        runtime = {}
    return runtime
def updateRuntimeConfiguration(runtime):
    jsonStr = json.dumps(runtime, indent=4)
    with open(runtimeFile, "w") as outfile:
        outfile.write(jsonStr)
def getConfiguration():
    if os.path.exists(configFile):
        f = open(configFile)
        config = json.load(f)
    else:
        config = { 'discord-token': '', 'guild-id': 1, 'hll-servers': [ { 'name': 'server 1', 'base-rcon-url': 'https://rcon.aimless.eu', 'live-stats-channel-id': 2, 'post-game-stats-channel-id': 3, 'color': '#6793e0'}]}
        jsonStr = json.dumps(config, indent=4)
        with open(configFile, "w") as outfile:
            outfile.write(jsonStr)
        print('Please update the config.json and restart the bot')
        exit()
    return config

config = getConfiguration()
runtime = getRuntimeConfiguration()

@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == config['guild-id']:
            actualGuild = guild
            break
    
    log(
        f'{bot.user} is connected to the following guild: \n' 
        f'{guild.name} (id: {guild.id})'
    )


import asyncio
import traceback
import threading
timerDelay = 60
lastResultJson = None

async def my_background_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await updateStats()
        await asyncio.sleep(timerDelay)

async def updateStats():
    for server in config['hll-servers']:
        try:
            liveStats = stats.getLiveStats(server)
            await postLiveStats(server, liveStats)
            lastGameId = runtime.get(server['name']).get('last_game_id')
            gameStats = stats.getGames(server, lastGameId)
            if gameStats:
                log('Found new games')
                log('Last game Id: ' + str(gameStats[-1]['id']))
                runtime.get(server['name'])['last_game_id'] = gameStats[-1]['id']
                for gameStat in gameStats:
                    await postGameStats(server, gameStat)
            updateRuntimeConfiguration(runtime)

        except:
            traceback.print_exc()

async def postGameStats(server, stats):
    if stats != None:
        channel = bot.get_channel(server['post-game-stats-channel-id'])
        if channel != None:
            embeds = []
            color = discord.Color.from_str(server['color'])
            title=stats['server_name'] + ' - Game {}'.format(stats['id'])
            e=discord.Embed(title=title, description='', color = color)
            if stats.get('map-image-url') != None:
                e.set_thumbnail(url = stats['map-image-url'])

            e.add_field(name="Map", value="{}".format(stats['map-human-name']))
            startEpoch = math.floor(stats['start'].timestamp())
            endEpoch = math.floor(stats['end'].timestamp())
            e.add_field(name="Start time", value="<t:{}>".format(startEpoch))
            e.add_field(name="End time", value="<t:{}>".format(endEpoch))
            embeds.append(e)
            liveStats = stats.get('top10s')

            if liveStats.get('top10-kills'):
                e2=discord.Embed( color = color)

                e2.add_field(name="Kills", value="{}".format(formatTop10(liveStats['top10-kills'])), inline=True)
                e2.add_field(name="Kill/Deaths", value="{}".format(formatTop10(liveStats['top10-kdr'])), inline=True)
                e2.add_field(name='\u200B', value='\u200B', inline=True)

                embeds.append(e2)
                e3=discord.Embed(color = color)

                e3.add_field(name="Kills Per Minute", value="{}".format(formatTop10(liveStats['top10-kpm'])), inline=True)
                e3.add_field(name="Deaths", value="{}".format(formatTop10(liveStats['top10-deaths'])), inline=True)
                embeds.append(e3)
                e4=discord.Embed( color = color)

                e4.add_field(name="Kill Streak", value="{}".format(formatTop10(liveStats['top10-killstreak'])), inline=True)
                e4.add_field(name="Death Streak", value="{}".format(formatTop10(liveStats['top10-deathstreak'])), inline=True)
                embeds.append(e4)
            sent_message = await channel.send(embeds=embeds)

            if stats['table']:
                filename = server['name'] + "-" + str(stats['id']) + ".txt"
                with open(filename, "w", encoding="utf-8") as outfile:
                    outfile.write(stats['table'])
                file = discord.File( filename)
                sent_message = await sent_message.reply(file=file)
                os.remove(filename)


async def postLiveStats(server, liveStats):
    if liveStats != None:
        channel = bot.get_channel(server['live-stats-channel-id'])
        if channel != None:
            message = None
            public_info = liveStats['public_info']
            embeds = []
            color = discord.Color.from_str(server['color'])
            e=discord.Embed(title=public_info['name'], description='', color = color)
            if public_info.get('map-image-url') != None:
                e.set_thumbnail(url = public_info['map-image-url'])

            e.add_field(name="Map", value="{}".format(public_info['map-human-name']))
            e.add_field(name="Players", value="{}".format(public_info['nb_players']))
            startEpoch = math.floor(public_info['start'].timestamp())
            e.add_field(name="Start time", value="<t:{}>".format(startEpoch))

            e.add_field(name="Next map", value="{}".format(public_info['next-map']))
            embeds.append(e)

            if liveStats['top10-kills']:
                e2=discord.Embed( color = color)

                e2.add_field(name="Kills", value="{}".format(formatTop10(liveStats['top10-kills'])), inline=True)
                e2.add_field(name="Kill/Deaths", value="{}".format(formatTop10(liveStats['top10-kdr'])), inline=True)
                e2.add_field(name='\u200B', value='\u200B', inline=True)

                embeds.append(e2)
                e3=discord.Embed(color = color)

                e3.add_field(name="Kills Per Minute", value="{}".format(formatTop10(liveStats['top10-kpm'])), inline=True)
                e3.add_field(name="Deaths", value="{}".format(formatTop10(liveStats['top10-deaths'])), inline=True)
                embeds.append(e3)
                e4=discord.Embed( color = color)

                e4.add_field(name="Kill Streak", value="{}".format(formatTop10(liveStats['top10-killstreak'])), inline=True)
                e4.add_field(name="Death Streak", value="{}".format(formatTop10(liveStats['top10-deathstreak'])), inline=True)
                embeds.append(e4)

            if (runtime.get(server['name']) != None and runtime.get(server['name']).get('live_stats_message_id') != None):
                try:
                    oldMessageId = runtime.get(server['name']).get('live_stats_message_id')
                    message = await channel.fetch_message(oldMessageId)
                except:
                    log('Could not find the old live stats message. Creating a new one.')
            if message != None:
                await message.edit(embeds=embeds)
            else:
                sent_message = await channel.send(embeds=embeds)
                runtime[server['name']] = {'live_stats_message_id': sent_message.id }

def formatTop10(playerList):
    top10List = []
    for count, value in enumerate(playerList):
        top10List.append("{}. {}: {}".format(count+1, value['player'], value['value']))
    return "```" + ("\n".join(top10List)) + "```"   


async def main():
    async with bot:
        bot.loop.create_task(my_background_task())
        await bot.start(config['discord-token'])

asyncio.run(main())