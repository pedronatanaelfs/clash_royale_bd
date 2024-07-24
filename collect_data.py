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

def get_clans():
    logging.debug("Fetching clans...")
    url = f'{BASE_URL}/clans?name=royale&minMembers=10&minScore=2000&limit=10'
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
            'cards': player_data['cards']
        }
        collection.update_one({'tag': player_data['tag']}, {'$set': player_record}, upsert=True)
        logging.debug(f"Saved data for player {player_data['tag']}.")

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

def save_battle_logs(battle_logs, player_tag):
    logging.debug(f"Saving battle logs for player {player_tag}...")
    collection = DB['battles']
    for log in battle_logs:
        battle_record = {
            'battleTime': log['battleTime'],
            'team': log['team'],
            'opponent': log['opponent'],
            'arena': log['arena'],
            'gameMode': log['gameMode'],
            'type': log['type'],
            'result': 'win' if log['team'][0]['crowns'] > log['opponent'][0]['crowns'] else 'lose',
            'teamCrowns': log['team'][0]['crowns'],
            'opponentCrowns': log['opponent'][0]['crowns'],
            'playerTag': player_tag
        }
        collection.update_one({'battleTime': log['battleTime'], 'playerTag': player_tag}, {'$set': battle_record}, upsert=True)
    logging.debug(f"Saved battle logs for player {player_tag}.")

if __name__ == '__main__':
    logging.debug("Starting data collection process...")
    
    clans = get_clans()
    player_tags = []

    for clan in clans:
        clan_tag = clan['tag']
        members = get_clan_members(clan_tag)
        for member in members:
            player_tags.append(member['tag'])
    
    logging.debug(f"Collected {len(player_tags)} player tags.")
    
    for player_tag in player_tags:
        player_data = get_player_data(player_tag)
        save_player_data(player_data)
        battle_logs = get_battle_logs(player_tag)
        save_battle_logs(battle_logs, player_tag)
    
    logging.debug("Data collection process completed.")
