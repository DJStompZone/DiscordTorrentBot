import discord
import asyncio
import feedparser
import os
import configparser
from pyarr import RadarrAPI, SonarrAPI
from discord_slash import SlashCommand
from discord.ext import commands


def configParserToDict(config_file_location):
    parser = configparser.ConfigParser()
    parser.read(config_file_location)
    config_dict = {}

    for element in parser.sections():
        config_dict[element] = {}
        for name, value in parser.items(element):
            config_dict[element][name] = value

    return config_dict


client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True)


dir_path = os.path.dirname(os.path.realpath(__file__))

config = configParserToDict(dir_path + '/discordarr.cfg')

parser = configparser.ConfigParser()
parser.read(dir_path + '/discordarr.cfg')
radarr_host_url = parser.get('radarr', 'radarrhosturl')
radarr_api_key = parser.get('radarr', 'radarrapikey')

sonarr_host_url = parser.get('sonarr', 'sonarrhosturl')
sonarr_api_key = parser.get('sonarr', 'sonarrapikey')

current_torrents = []
discord_settings = config['DiscordSettings']
general_settings = config['General']
TVpath = general_settings['tvlocation']
Animepath = general_settings['animelocation']
Moviepath = general_settings['movieslocation']

discord_bot_api = discord_settings['apikey']
bot_prefix = discord_settings['botprefix']
bot = commands.Bot(command_prefix=bot_prefix, case_insensitive=True)

radarr = RadarrAPI(radarr_host_url, radarr_api_key)
sonarr = SonarrAPI(sonarr_host_url, sonarr_api_key)

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')


@bot.command(name='downloadTV', help='Downloads a TV torrent and adds to Plex.')
async def downloadTV(ctx, show, *args):
    print(ctx.author)
    if ctx.channel.name == "plex-torrents":
        for x in args:
            show += " " + str(x)

        tvLookup = sonarr.lookup_series(show)

        for tv in tvLookup[0:3]:
            embed = discord.Embed(title=tv['title'],
                                  colour=discord.Colour(0x00AAFF),
                                  url=str(tv["remotePoster"]),
                                  description=tv["overview"])
            embed.set_thumbnail(url=str(tv["remotePoster"]))
            embed.set_author(name="TVShow")
            embed.set_footer(text=tv['tvdbId'])
            m = await ctx.send(embed=embed)
            emoji = '\N{THUMBS UP SIGN}'
            await m.add_reaction(emoji)

    else:
        await ctx.send("You must use the plex-torrents chat")


@bot.command(name='downloadMovie', help='Downloads a Movie torrent and adds to Plex.')
async def downloadMovie(ctx, show, *args):
    print(ctx.author)
    if ctx.channel.name == "plex-torrents":
        for x in args:
            show += " " + str(x)

        movieLookup = radarr.lookup_movie(show)

        for movie in movieLookup[0:3]:
            embed = discord.Embed(title=movie['folder'],
                                  colour=discord.Colour(0xFFAA00),
                                  url=str(movie["images"][0]["remoteUrl"]),
                                  description=movie["overview"])
            embed.set_thumbnail(url=str(movie["images"][0]["remoteUrl"]))
            embed.set_author(name="Movie")
            embed.set_footer(text=movie['tmdbId'])
            m = await ctx.send(embed=embed)
            emoji = '\N{THUMBS UP SIGN}'
            await m.add_reaction(emoji)

    else:
        await ctx.send("You must use the plex-torrents chat")


@bot.command(name='eta', help='Shows ETA of current shows downloading.')
async def eta(ctx):
    msg = "todo"
    await ctx.send(msg)


@bot.command(name='download', help='fuck you')
async def download(ctx, show, *args):
    content_type = str(show).lower()
    print(content_type)
    if content_type == "movie":
        await downloadMovie(ctx, args[0], args[1:])
    elif content_type == "tv" or content_type == "tvshow":
        if str(args[0]).lower() == "show":
            await downloadTV(ctx, args[1], args[2:])
        else:
            await downloadTV(ctx, args[0], args[1:])


@bot.event
async def on_reaction_add(reaction, user):
    if user.id != bot.user.id and reaction.message.author.id == bot.user.id:
        content_type = reaction.message.embeds[0].author.name

        if content_type == "Movie":
            movieID = int(reaction.message.embeds[0].footer.text)

            print(radarr.add_movie(movieID, 6, Moviepath))

            await bot.get_channel(reaction.message.channel.id).send(
                reaction.message.embeds[0].title + " has been added to the download list")

        elif content_type == "TVShow":
            tvID = int(reaction.message.embeds[0].footer.text)

            print(sonarr.add_series(tvID, 6, TVpath, search_for_missing_episodes=True))
            await bot.get_channel(reaction.message.channel.id).send(
                reaction.message.embeds[0].title + " has been added to the download list")


@slash.slash(name='DownloadMovie', description="hi loser")
async def slashDownloadMovie(ctx, show, *args):
    await downloadMovie(ctx, show, *args)

bot.run(discord_bot_api)
