import discord
import asyncio
import feedparser
import os
import configparser
from transmission_rpc import Client
from discord.ext import commands

def configParserToDict(config_file_location):
    parser = configparser.ConfigParser()
    parser.read('DiscordTorrentBot.cfg')    
    config_dict = {}
    
    for element in parser.sections():
        config_dict[element] = {}
        for name, value in parser.items(element):
            config_dict[element][name] = value    
            
    return config_dict

client = discord.Client()
bot = commands.Bot(command_prefix='!', case_insensitive=True)


dir_path = os.path.dirname(os.path.realpath(__file__))

config = configParserToDict(dir_path + '/DiscordTorrentBot.cfg')
current_torrents = []
transmission_settings = config['TransmissionServer']
jackett_settings = config['JackettServer']
discord_settings = config['DiscordSettings']
general_settings = config['General']
TVpath = general_settings['tvlocation']
Animepath = general_settings['animelocation']
Moviepath =  general_settings['movieslocation']



emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣"]

jackett_APIkey = jackett_settings['apikey']
tv_source = jackett_settings['tvtorrentsource']
movie_source = jackett_settings['movietorrentsource']
discord_bot_api= discord_settings['apikey']
c = Client(host=transmission_settings['ip'], port=transmission_settings['port'], username=transmission_settings['username'], password=transmission_settings['password'])
 
    
    
@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')
        
@bot.command(name='downloadAnime', help='Downloads a Anime torrent and adds to Plex.')
async def downloadAnime(ctx, show, *args):
    if ctx.channel.name == "plex-torrents":
        for x in args:
            show += " " + x

        show = show.replace(" ", "+")
        show = "https://nyaa.si/?page=rss&q=" + str(show) + "&c=1_2&f=0"
        
        feed = feedparser.parse(show)
        msg= "Found the below torrents, select an option via reactions:"
        if(len(feed.entries) > 0):
            feedsorted = sorted(feed.entries, key = lambda x:int(x.nyaa_seeders))
            feedsorted.reverse()
            for i in range(min(5,len(feedsorted))):
                msg += "```" + str(i+1) +") " + str(feedsorted[i].title) + " | " + str(feedsorted[i].nyaa_size) + " | seeders : " + str(feedsorted[i].nyaa_seeders) + "```"
                           
            selection = await postMessageAndAwaitReaction(ctx, msg, min(5,len(feedsorted)))
            
            if selection != 0:
                add_torrent(feedsorted[selection-1].link, Animepath)
                await ctx.send("Torrent " + str(feedsorted[selection-1].title) + " added")
            else:
                await ctx.send("Selection timed out, try again loser boy")
        else:
            await ctx.send("Nothing found, try again or ask your lord and savior Jon")
    else:
        await ctx.send("You must use the plex-torrents chat")
        
@bot.command(name='downloadTV', help='Downloads a TV torrent and adds to Plex.')
async def downloadTV(ctx, show, *args):
    if ctx.channel.name == "plex-torrents":
        for x in args:
            show += " " + str(x)

        show = show.replace(" ", "+")
        show = "http://" + jackett_settings['ip'] + ":" + jackett_settings['port'] + "/api/v2.0/indexer/" + tv_source + "/results/torznab/api?apikey=" + jackett_APIkey + "&t=search&cat=&q=" + str(show)
        feed = feedparser.parse(show)
        msg= "Found the below torrents, select an option via reactions:"
        if(len(feed.entries) > 0):
            
            feedsorted = feed.entries
            for i in range(min(5,len(feedsorted))):
                msg += "```" + str(i+1) +") " + str(feedsorted[i].title) + " | " + sizeof_fmt(int(feedsorted[i].size)) + "```"
                           
            selection = await postMessageAndAwaitReaction(ctx, msg, min(5,len(feedsorted)))
            
            if selection != 0:
                add_torrent(feedsorted[selection-1].link, TVpath)
                await ctx.send("Torrent " + str(feedsorted[selection-1].title) + " added")
            else:
                await ctx.send("Selection timed out, try again loser boy")
        else:
            await ctx.send("Nothing found, try again or ask your lord and savior Jon")
    else:
        await ctx.send("You must use the plex-torrents chat")
        
@bot.command(name='downloadMovie', help='Downloads a Movie torrent and adds to Plex.')
async def downloadMovie(ctx, show, *args):
    if ctx.channel.name == "plex-torrents":
        for x in args:
            show += " " + str(x)
        #c.add_torrent(torrent_url, download_dir='/data/downloads/TV/')
        show = show.replace(" ", "+")
        show = "http://" + jackett_settings['ip'] + ":" + jackett_settings['port'] + "/api/v2.0/indexers/"+ movie_source +"/results/torznab/api?apikey=" + jackett_APIkey + "&t=search&cat=&q=" + str(show)
        
        feed = feedparser.parse(show)
        msg= "Found the below torrents, select an option via reactions:"
        if(len(feed.entries) > 0):
            feedsorted = feed.entries
            for i in range(min(5,len(feedsorted))):
                msg += "```" + str(i+1) +") " + str(feedsorted[i].title) + " | " + sizeof_fmt(int(feedsorted[i].size)) + "```"
                           
            selection = await postMessageAndAwaitReaction(ctx, msg, min(5,len(feedsorted)))
                
            if selection != 0:
                print(feedsorted)
                add_torrent(feedsorted[selection-1].link, Moviepath)
                await ctx.send("Torrent " + str(feedsorted[selection-1].title) + " added")
            else:
                await ctx.send("Selection timed out, try again loser boy")
        else:
            await ctx.send("Nothing found, try again or ask your lord and savior Jon")
    else:
        await ctx.send("You must use the plex-torrents chat")
                
@bot.command(name='eta', help='Shows ETA of current shows downloading.')
async def eta(ctx):
    msg = "Torrents remaining:"
    for x in current_torrents:
        tor = c.get_torrent(x)
        if(tor.status != "stopped") :
            msg+="```"+ tor.name + " : " + tor.format_eta() + "```"
        else:
            current_torrents.remove(x)
    await ctx.send(msg)
        
                
async def postMessageAndAwaitReaction(ctx, msg, numberofemojis):
    message = await ctx.send(msg)
    
    for i in range(numberofemojis):
        await message.add_reaction(emojis[i])
            
    selection=0
    for x in range(20):
        message = await ctx.fetch_message(message.id)
        x=1
        for reaction in message.reactions:            
            if reaction.count==2:
                selection=x
                break
            x = x+1
        if selection != 0:
            break
        await asyncio.sleep(1)    
    return selection
   
def add_torrent(torrent, path1):
    print(torrent)
    torrent = c.add_torrent(torrent, download_dir=str(path1))
    current_torrents.append(torrent.id)
    
    
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

    


bot.run(discord_bot_api)   