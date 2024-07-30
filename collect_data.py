import requests
import pymongo
import os
import logging
from dotenv import load_dotenv
from datetime import datetime
from urllib.parse import quote

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações da API e MongoDB
API_KEY = os.getenv('API_KEY')
BASE_URL = 'https://api.clashroyale.com/v1'
HEADERS = {'Authorization': f'Bearer {API_KEY}'}
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = 'clash_royale'
CLIENT = pymongo.MongoClient(MONGO_URI)
DB = CLIENT[DB_NAME]

def get_clan(clan_name):
    logging.debug("Fetching clans...")
    url = f'{BASE_URL}/clans?name={clan_name}&minMembers=10&limit=10'
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        clans = response.json().get('items', [])
        logging.debug(f"Fetched {len(clans)} clans.")
        return clans
    else:
        logging.error(f"Failed to fetch clans: {response.status_code} - {response.text}")
        return []

def get_clan_members(clan_tag):
    logging.debug(f"Fetching members for clan {clan_tag}...")
    encoded_clan_tag = quote(clan_tag)
    url = f'{BASE_URL}/clans/{encoded_clan_tag}/members'
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        members = response.json().get('items', [])
        logging.debug(f"Fetched {len(members)} members for clan {clan_tag}.")
        return members
    else:
        logging.error(f"Failed to fetch members for clan {clan_tag}: {response.status_code} - {response.text}")
        return []

def get_player_data(player_tag):
    logging.debug(f"Fetching data for player {player_tag}...")
    encoded_player_tag = quote(player_tag)
    url = f'{BASE_URL}/players/{encoded_player_tag}'
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        player_data = response.json()
        logging.debug(f"Fetched data for player {player_tag}.")
        return player_data
    else:
        logging.error(f"Failed to fetch data for player {player_tag}: {response.status_code} - {response.text}")
        return {}

def save_player_data(player_data):
    if player_data:
        logging.debug(f"Saving data for player {player_data["tag"]}...")
        collection = DB['players']
        player = list(collection.find({"tag": player_data["tag"]})),
        saved = len(player[0]) != 0 
      
        if not saved:
            player_record = {
                'tag': player_data['tag'],
                'name': player_data['name'],
                'expLevel': player_data['expLevel'],
                'trophies': player_data['trophies'],
                'bestTrophies': player_data['bestTrophies'],
                'wins': player_data['wins'],
                'losses': player_data['losses'],
                'battleCount': player_data['battleCount'],
                'threeCrownWins': player_data['threeCrownWins'],
                'deck': player_data['currentDeck']
            }
            result = collection.update_one({'tag': player_data['tag']}, {'$set': player_record}, upsert=True)
            logging.debug(f"Saved data for player {player_data['tag']}.")
            logging.debug(f"Player id is {result.upserted_id}.")
            return result.upserted_id
        else:
            logging.debug(f"Player {player_data["tag"]} alrady exists.")
            return player[0][0]["_id"]

def get_battle_logs(player_tag):
    logging.debug(f"Fetching battle logs for player {player_tag}...")
    encoded_player_tag = quote(player_tag)
    url = f'{BASE_URL}/players/{encoded_player_tag}/battlelog'
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        battle_logs = response.json()
        logging.debug(f"Fetched {len(battle_logs)} battle logs for player {player_tag}.")
        return battle_logs
    else:
        logging.error(f"Failed to fetch battle logs for player {player_tag}: {response.status_code} - {response.text}")
        return []

def save_battle_logs(battle_logs, player_tag, player_id):
    logging.debug(f"Saving battle logs for player {player_tag}...")
    collection = DB['battles']
    playersCollection = DB["players"]
    
    for log in battle_logs:
        opponent_tag = log['opponent'][0]["tag"] if log['opponent'][0]["tag"] != None else ''
        opponent_mongo_data = list(playersCollection.find({"tag": opponent_tag})),
        saved = len(opponent_mongo_data[0]) != 0
        log['team'][0]["mongoId"] = player_id
        opponent_id = {}

        if not saved:
            opponent_data = get_player_data(opponent_tag)
            opponent_id = save_player_data(opponent_data)
            log['opponent'][0]["mongoId"] = opponent_id
        else:
            log['opponent'][0]["mongoId"] = opponent_mongo_data[0][0]["_id"]
            
        winner = {}
        loser = {}
        if log['team'][0]['crowns'] > log['opponent'][0]['crowns']: 
            winner = log['team'][0]
            loser = log['opponent'][0]
        else: 
            winner = log['opponent'][0]
            loser = log['team'][0]

        battle_record = {
            'battleTime': log['battleTime'],
            'winner': {
                "playerId": winner["mongoId"],
                "tag": winner['tag'],
                "name": winner['name'],
                "deck": winner['cards'],
                "crowns": winner['crowns'],
            },
            'loser': {
                "playerId": loser["mongoId"],
                "tag": loser['tag'],
                "name": loser['name'],
                "deck": loser['cards'],
                "crowns": loser['crowns'],
            },
        }
        collection.update_one({'battleTime': log['battleTime'], 'mainPlayerTag': player_tag}, {'$set': battle_record}, upsert=True)
    logging.debug(f"Saved battle logs for player {player_tag}.")

def dataRemover():
    
    players = DB['players']
    players.delete_many({})
    battles = DB['battles']
    battles.delete_many({})
    logging.debug("Data collection was removed.")


if __name__ == '__main__':
    logging.debug("Starting data collection process...")

    clans = [
        # 'WHAM! RO',
        # 'La Eza',
        # 'SAF GÜÇ',
        'おと姫',
        # 'Tigers BR',
        # 'Nova I',
        # 'INTZ',
        # 'Nova EG',
        # 'Chinese eSports',
        # 'Kings',
    ]

    for clanName in clans:
        logging.debug(f"----------- Clan {clanName} -----------------")
        clan = get_clan(clanName)
        player_tags = []
        for atributte in clan:
            clan_tag = atributte['tag']
            members = get_clan_members(clan_tag)
            for member in members:
                player_tags.append(member['tag'])
        
        logging.debug(f"Collected {len(player_tags)} player tags.")
        
        for player_tag in player_tags:
            player_data = get_player_data(player_tag)
            playerId = save_player_data(player_data)
            battle_logs = get_battle_logs(player_tag)
            save_battle_logs(battle_logs, player_tag, playerId)
    
    logging.debug("Data collection process completed.")
