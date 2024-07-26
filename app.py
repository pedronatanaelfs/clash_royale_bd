from flask import Flask, render_template, request
import pymongo
import os
import logging
from dotenv import load_dotenv
from urllib.parse import quote
from datetime import datetime

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configurações do MongoDB
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = 'clash_royale'
CLIENT = pymongo.MongoClient(MONGO_URI)
DB = CLIENT[DB_NAME]

@app.route('/')
def index():
    # Obter nomes de cartas e datas válidas
    card_names = get_card_names()
    battle_dates = get_battle_dates()
    return render_template('index.html', card_names=card_names, battle_dates=battle_dates)

@app.route('/victory_percentage', methods=['POST'])
def victory_percentage():
    card_name = request.form['card_name']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    results = victory_percentage_with_card(card_name, start_time, end_time)
    logging.debug(f"Results: {results}")
    return render_template('results.html', results=results)

def victory_percentage_with_card(card_name, start_time, end_time):
    logging.debug(f"Querying for card: {card_name}, from {start_time} to {end_time}")
    
    # Converter start_time e end_time para o formato ISO8601
    start_iso = datetime.strptime(start_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    end_iso = datetime.strptime(end_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    
    logging.debug(f"Converted start_time: {start_iso}, end_time: {end_iso}")
    
    pipeline = [
        {"$match": {
            "battleTime": {"$gte": start_iso, "$lt": end_iso},
            "team.cards.name": card_name
        }},
        {"$group": {
            "_id": "battleGroup",
            "totalMatches": {"$sum": 1},
            "totalWinsWithCardX": 
                { "$sum": { "$cond": [{ "$eq": [ "$result", "win"]}, 1, 0 ]}},
            "totalWinsLossesCardX": 
                {"$sum": {"$cond": [{ "$eq": [ "$result", "lose" ]}, 1, 0 ]}}
        }},
        {"$project": {
            "_id": 0,
            "winPercentage": {
                "$multiply": [
                    {"$divide": [ "$totalWinsWithCardX", "$totalMatches"]},
                    100]
            },
            "losePercentage": {
                "$multiply": [
                    {"$divide": ["$totalWinsLossesCardX", "$totalMatches"]},
                    100 ]
            }
        }}
    ]
    
    logging.debug(f"Pipeline: {pipeline}")
    
    results = list(DB['battles'].aggregate(pipeline))
    logging.debug(f"Pipeline results: {results}")
    return results

@app.route('/high_win_decks', methods=['POST'])
def high_win_decks():
    win_percentage = float(request.form['win_percentage'])
    start_time = request.form['start_time_deck']
    end_time = request.form['end_time_deck']
    results = decks_with_high_win_percentage(win_percentage, start_time, end_time)
    logging.debug(f"Results: {results}")
    return render_template('results.html', results=results)

def decks_with_high_win_percentage(min_win_percentage, start_time, end_time):
    logging.debug(f"Querying for decks with at least {min_win_percentage}% wins, from {start_time} to {end_time}")
    
    start_iso = datetime.strptime(start_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    end_iso = datetime.strptime(end_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    
    pipeline = [
        {"$match": {
            "battleTime": {"$gte": start_iso, "$lt": end_iso}
        }},
        {"$group": {
            "_id": "$team.cards",
            "totalBattles": {"$sum": 1},
            "wins": {"$sum": {"$cond": [{"$eq": ["$result", "win"]}, 1, 0]}}
        }},
        {"$project": {
            "deck": "$_id",
            "winPercentage": {"$multiply": [{"$divide": ["$wins", "$totalBattles"]}, 100]},
            "totalBattles": 1,
            "wins": 1,
            "_id": 0
        }},
        {"$match": {"winPercentage": {"$gte": min_win_percentage}}}
    ]
    
    results = list(DB['battles'].aggregate(pipeline))
    logging.debug(f"Pipeline results: {results}")
    return results

@app.route('/defeats_with_combo', methods=['POST'])
def defeats_with_combo():
    combo = request.form['combo'].split(',')
    start_time = request.form['start_time_combo']
    end_time = request.form['end_time_combo']
    results = losses_with_card_combo(combo, start_time, end_time)
    logging.debug(f"Results: {results}")
    return render_template('results.html', results=results)

def losses_with_card_combo(card_combo, start_time, end_time):
    logging.debug(f"Querying for defeats with card combo {card_combo}, from {start_time} to {end_time}")
    
    start_iso = datetime.strptime(start_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    end_iso = datetime.strptime(end_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    
    pipeline = [
        {"$match": {
            "battleTime": {"$gte": start_iso, "$lt": end_iso},
            "team.cards.name": {"$all": card_combo}
        }},
        {"$group": {
            "_id": "$result",
            "count": {"$sum": 1}
        }},
        {"$match": {"_id": "lose"}},
        {"$project": {
            "_id": 0,
            "result": "$_id",
            "count": 1
        }}
    ]
    
    results = list(DB['battles'].aggregate(pipeline))
    logging.debug(f"Pipeline results: {results}")
    return results

@app.route('/specific_victories', methods=['POST'])
def specific_victories():
    card_name = request.form['card_name_victory']
    trophy_diff = float(request.form['trophy_diff'])
    start_time = request.form['start_time_victory']
    end_time = request.form['end_time_victory']
    results = specific_victory_conditions(card_name, trophy_diff, start_time, end_time)
    logging.debug(f"Results: {results}")
    return render_template('results.html', results=results)

def specific_victory_conditions(card_name, trophy_difference_percentage, start_time, end_time):
    logging.debug(f"Querying for specific victories with card {card_name}, trophy diff {trophy_difference_percentage}%, from {start_time} to {end_time}")
    
    start_iso = datetime.strptime(start_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    end_iso = datetime.strptime(end_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    
    pipeline = [
        {"$match": {
            "battleTime": {"$gte": start_iso, "$lt": end_iso},
            "team.cards.name": card_name,
            "opponentCrowns": {"$gte": 2},
            "team.trophies": {"$lt": {"$subtract": ["$opponent.trophies", {"$multiply": ["$opponent.trophies", trophy_difference_percentage / 100]}]}}
        }},
        {"$match": {"result": "win"}},
        {"$count": "victories"}
    ]
    
    results = list(DB['battles'].aggregate(pipeline))
    logging.debug(f"Pipeline results: {results}")
    return results

@app.route('/high_win_combos', methods=['POST'])
def high_win_combos():
    combo_size = int(request.form['combo_size'])
    win_percentage = float(request.form['win_percentage_combo'])
    start_time = request.form['start_time_combo']
    end_time = request.form['end_time_combo']
    results = card_combos_with_high_win_percentage(combo_size, win_percentage, start_time, end_time)
    logging.debug(f"Results: {results}")
    return render_template('results.html', results=results)

def card_combos_with_high_win_percentage(combo_size, min_win_percentage, start_time, end_time):
    logging.debug(f"Querying for card combos of size {combo_size} with at least {min_win_percentage}% wins, from {start_time} to {end_time}")
    
    start_iso = datetime.strptime(start_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    end_iso = datetime.strptime(end_time, '%Y-%m-%d').strftime('%Y%m%dT%H%M%S.000Z')
    
    pipeline = [
        {"$match": {
            "battleTime": {"$gte": start_iso, "$lt": end_iso}
        }},
        {"$unwind": "$team.cards"},
        {"$group": {
            "_id": {"$slice": ["$team.cards.name", combo_size]},
            "totalBattles": {"$sum": 1},
            "wins": {"$sum": {"$cond": [{"$eq": ["$result", "win"]}, 1, 0]}}
        }},
        {"$project": {
            "combo": "$_id",
            "winPercentage": {"$multiply": [{"$divide": ["$wins", "$totalBattles"]}, 100]},
            "totalBattles": 1,
            "wins": 1,
            "_id": 0
        }},
        {"$match": {"winPercentage": {"$gte": min_win_percentage}}}
    ]
    
    results = list(DB['battles'].aggregate(pipeline))
    logging.debug(f"Pipeline results: {results}")
    return results

def get_card_names():
    try:
        card_names = DB['battles'].distinct("team.cards.name")
        logging.debug(f"Card names: {card_names}")
        return card_names
    except Exception as err:
        logging.error(f"An error occurred while fetching card names: {err}")
        return []

def get_battle_dates():
    try:
        battle_dates = DB['battles'].distinct("battleTime")
        # Converter datas para strings no formato ISO sem a parte do tempo
        battle_dates = sorted(set([datetime.strptime(battle_date, '%Y%m%dT%H%M%S.%fZ').date().isoformat() for battle_date in battle_dates]))
        logging.debug(f"Battle dates: {battle_dates}")
        return battle_dates
    except Exception as err:
        logging.error(f"An error occurred while fetching battle dates: {err}")
        return []

if __name__ == '__main__':
    app.run(debug=True)
