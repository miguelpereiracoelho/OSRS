import discord
import os
import requests
import asyncio
from datetime import datetime

# --- CONFIG ---

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = 1485292178698928252  # Replace with your Discord channel ID
API1_URL = "https://templeosrs.com/api/collection-log/group_recent_items.php?group=2467"  # Replace with API 1 URL
API2_URL = "https://templeosrs.com/api/group_achievements.php?id=2467"  # Replace with API 2 URL

# --- SETUP ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

posted_ids = set()  # Keep track of items already posted

BOSS_IMAGE_OVERRIDES = {
    "Tombs of Amascut Expert": "https://oldschool.runescape.wiki/images/Tombs_of_Amascut_-_Expert_Mode_icon.png",
    "Tombs of Amascut Entry": "https://oldschool.runescape.wiki/images/Tombs_of_Amascut_-_Entry_Mode_icon.png",
    "Tombs of Amascut Normal": "https://oldschool.runescape.wiki/images/Tombs_of_Amascut_-_Normal_Mode_icon.png"
}

DEFAULT_CLOG_IMAGE = "https://oldschool.runescape.wiki/images/Coins_10000.png"

def get_clog_image(item_name):
    """
    Return the wiki image URL for a Collection Log item.
    Preserves parentheses exactly, replaces spaces with underscores.
    """
    if not item_name:
        return DEFAULT_CLOG_IMAGE

    # Replace spaces with underscores, keep everything else intact
    formatted_name = item_name.replace(" ", "_")
    
    # Construct URL
    url = f"https://oldschool.runescape.wiki/images/{formatted_name}.png"
    
    # Optional: check if URL exists
    # You could skip this to save HTTP requests if you trust the wiki
    import requests
    try:
        r = requests.head(url, timeout=5)
        if r.status_code == 200:
            return url
        else:
            url = f"https://oldschool.runescape.wiki/images/{formatted_name}_(1).png"
            r = requests.head(url, timeout=5)
            if r.status_code == 200:
                return url
    except:
        pass
    
    # Fallback if not found
    return DEFAULT_CLOG_IMAGE

# --- FUNCTION TO FETCH AND POST ---
async def fetch_and_post(channel):
    dataClog = []
    dataXP = []

    # --- API 1 ---
    try:
        res1 = requests.get(API1_URL).json()
        data1 = res1.get("data", [])
        for item in data1:
          
            dataClog.append({
                "id": f"api1-{item['id']}",
                "title": "New Collection Log",
                "name": item["name"],
                "player": item["player_name_with_capitalization"]
            })
    except Exception as e:
        print("Error fetching API 1:", e)

    # --- API 2 ---
    try:
        res2 = requests.get(API2_URL).json()
        data2 = res2.get("data", [])
        for item in data2:
            # direct image URL from API
            image = f"https://oldschool.runescape.wiki/images/{item['Skill']}_icon.png"

            dataXP.append({
                "id": f"api2-{item['Username']}-{item['Skill']}",
                "title": "Xp Milestone",
                "Skill": item['Skill'],
                "Milestone": item["Milestone"],
                "player": item["Username"],
                "image": image,
                "type": item["Type"],
                "Value": item["Xp"]
            })
    except Exception as e:
        print("Error fetching API 2:", e)

    # --- API 1 loop ---
    for item in dataClog:
        post_id = f"api1-{item['id']}"
        if post_id in posted_ids:
            continue
        posted_ids.add(post_id)

        #image = f"https://oldschool.runescape.wiki/images/{item['name'].replace(' ', '_').replace('(', '').replace(')', '').replace('+', '').replace('\'', '')}.png"
        image = get_clog_image(item["name"])
        embed = discord.Embed(
            title="New Collection Log",
            description=item["name"],
            color=discord.Color.blue()
        )
        embed.add_field(name="Player", value=item["player"], inline=True)
        embed.set_thumbnail(url=image)

        await channel.send(embed=embed)

    # --- API 2 loop ---
    for item in dataXP:
        post_id = f"api2-{item['player']}-{item['Skill']}"
        if post_id in posted_ids:
            continue
        posted_ids.add(post_id)
        if item['Skill'] == "Ehp": continue
        if item['Skill'] == "Overall": 
            image = "https://oldschool.runescape.wiki/images/Skills_icon.png" 
        else:
            image = f"https://oldschool.runescape.wiki/images/{item['Skill'].replace(' ', '_')}_icon.png"
        if item['Milestone'] == "XP" and item['type'] != "Pvm":
            item['Value'] = f"{int(item['Value'])//1000000}M"
        if item['type'] == "Pvm":
            item['Milestone'] = "Boss Kill"
            image = BOSS_IMAGE_OVERRIDES.get(
            item['Skill'],
            f"https://oldschool.runescape.wiki/images/{item['Skill'].replace(' ', '_')}.png"
        )

        embed = discord.Embed(
            title=f"{item['Milestone']} Milestone",
            description=f"{item['Skill']}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Player", value=item["player"], inline=True)
        embed.add_field(name=item["Milestone"], value=item["Value"], inline=True)
        embed.set_thumbnail(url=image)

        await channel.send(embed=embed)

# --- AUTO POST LOOP ---
async def auto_post():
    await client.wait_until_ready()

    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"ERROR: Channel ID {CHANNEL_ID} not found")
        return

    while not client.is_closed():
        await fetch_and_post(channel)
        await asyncio.sleep(60)  # check every 60 seconds

# --- RUN BOT ---
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(auto_post())

client.run(TOKEN)