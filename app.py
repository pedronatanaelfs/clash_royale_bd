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
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "clash_royale"
CLIENT = pymongo.MongoClient(MONGO_URI)
DB = CLIENT[DB_NAME]


@app.route("/")
def index():
    # Obter nomes de cartas e datas válidas
    card_names = get_card_names()
    battle_dates = get_battle_dates()
    return render_template(
        "index.html", card_names=card_names, battle_dates=battle_dates
    )


@app.route("/victory_percentage", methods=["POST"])
def victory_percentage():
    card_name = request.form["card_name"]
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]
    results = victory_percentage_with_card(card_name, start_time, end_time)
    logging.debug(f"Results: {results}")
    return render_template("results.html", results=results)


def victory_percentage_with_card(card_name, start_time, end_time):
    logging.debug(f"Querying for card: {card_name}, from {start_time} to {end_time}")

    # Converter start_time e end_time para o formato ISO8601
    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    logging.debug(f"Converted start_time: {start_iso}, end_time: {end_iso}")

    pipeline = [
        # Filtra pelo periodo da batalha
        {"$match": {"battleTime": {"$gte": start_iso, "$lt": end_iso}}},
        # Cria campos booleanos informando em qual londo a carta esta presente
        {
            "$project": {
                "winnerHasCard": {"$in": [card_name, "$winner.deck.name"]},
                "loserHasCard": {"$in": [card_name, "$loser.deck.name"]},
            }
        },
        # Agrupa todos os documentos e soma as quantidades de vitoria e derrota
        {
            "$group": {
                "_id": 1,
                "totalWins": {"$sum": {"$cond": ["$winnerHasCard", 1, 0]}},
                "totalLosses": {"$sum": {"$cond": ["$loserHasCard", 1, 0]}},
            }
        },
        # Calcula as porcentagens de vitorias e derrotas.
        {
            "$project": {
                "winPercentage": {
                    "$multiply": [
                        {
                            "$divide": [
                                "$totalWins",
                                {"$add": ["$totalWins", "$totalLosses"]},
                            ]
                        },
                        100,
                    ]
                },
                "lossPercentage": {
                    "$multiply": [
                        {
                            "$divide": [
                                "$totalLosses",
                                {"$add": ["$totalWins", "$totalLosses"]},
                            ]
                        },
                        100,
                    ]
                },
            }
        },
    ]

    logging.debug(f"Pipeline: {pipeline}")
    results = list(DB["battles"].aggregate(pipeline))
    logging.debug(f"Pipeline results: {results}")
    return results


@app.route("/high_win_decks", methods=["POST"])
def high_win_decks():
    win_percentage = float(request.form["win_percentage"])
    start_time = request.form["start_time_deck"]
    end_time = request.form["end_time_deck"]
    results = decks_with_high_win_percentage(win_percentage, start_time, end_time)
    logging.debug(f"Results: {results}")
    return render_template("results.html", results=results)


def decks_with_high_win_percentage(min_win_percentage, start_time, end_time):
    logging.debug(
        f"Querying for decks with at least {min_win_percentage}% wins, from {start_time} to {end_time}"
    )

    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    pipeline = [
        {
            "$match": {
                "battleTime": {"$gte": start_iso, "$lt": end_iso},
            },
        },
        {"$project": {"winnerDeck": "$winner.deck.name", "isWin": {"$literal": 1}}},
        {"$group": {"_id": "$winnerDeck", "totalWins": {"$sum": "$isWin"}}},
        {
            "$lookup": {
                "from": "battles",
                "let": {"deck": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$gte": ["$battleTime", start_iso]},
                                    {"$lt": ["$battleTime", end_iso]},
                                    {
                                        "$or": [
                                            {"$eq": ["$winner.deck.name", "$$deck"]},
                                            {"$eq": ["$loser.deck.name", "$$deck"]},
                                        ]
                                    },
                                ]
                            }
                        }
                    },
                    {"$count": "totalGames"},
                ],
                "as": "gameStats",
            }
        },
        {
            "$project": {
                "totalWins": 1,
                "totalGames": {"$arrayElemAt": ["$gameStats.totalGames", 0]},
                "winPercentage": {
                    "$multiply": [
                        {
                            "$divide": [
                                "$totalWins",
                                {
                                    "$ifNull": [
                                        {"$arrayElemAt": ["$gameStats.totalGames", 0]},
                                        1,
                                    ]
                                },
                            ]
                        },
                        100,
                    ]
                },
            }
        },
        {"$match": {"winPercentage": {"$gt": min_win_percentage}}},
        {"$sort": {"winPercentage": -1}},
    ]

    results = list(DB["battles"].aggregate(pipeline))
    logging.debug(f"Pipeline results: {results}")
    return results


@app.route("/defeats_with_combo", methods=["POST"])
def defeats_with_combo():
    combo = request.form["combo"].split(",")
    start_time = request.form["start_time_combo"]
    end_time = request.form["end_time_combo"]
    results = losses_with_card_combo(combo, start_time, end_time)
    logging.debug(f"Results: {results}")
    return render_template("results.html", results=results)


def losses_with_card_combo(card_combo, start_time, end_time):
    logging.debug(
        f"Querying for defeats with card combo {card_combo}, from {start_time} to {end_time}"
    )

    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    pipeline = [
        # Filtra pelo periodo da batalha
        {"$match": {"battleTime": {"$gte": start_iso, "$lt": end_iso}}},
        # Cria um novo campo que informa se elementos do combo estão no deck do perdedor ou nao
        {
            "$project": {
                "hasCombo": {
                    "$allElementsTrue": {
                        "$map": {
                            "input": card_combo,
                            "as": "card",
                            "in": {"$in": ["$$card", "$loser.deck.name"]},
                        }
                    }
                },
            }
        },
        # Seleciona apenas os registros que possuem o combo no deck perdedor
        {"$match": {"hasCombo": True}},
        # Conta quantas derrotas ocorreram
        {"$count": "totalLosses"},
    ]

    results = list(DB["battles"].aggregate(pipeline))
    logging.debug(f"Pipeline results: {results}")
    return results


@app.route("/specific_victories", methods=["POST"])
def specific_victories():
    card_name = request.form["card_name_victory"]
    trophy_diff = float(request.form["trophy_diff"])
    start_time = request.form["start_time_victory"]
    end_time = request.form["end_time_victory"]
    results = specific_victory_conditions(card_name, trophy_diff, start_time, end_time)
    logging.debug(f"Results: {results}")
    return render_template("results.html", results=results)


def specific_victory_conditions(
    card_name, trophy_difference_percentage, start_time, end_time
):
    logging.debug(
        f"Querying for specific victories with card {card_name}, trophy diff {trophy_difference_percentage}%, from {start_time} to {end_time}"
    )

    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    pipeline = [
        {
            "$match": {
                "battleTime": {"$gte": start_iso, "$lt": end_iso},
                "team.cards.name": card_name,
                "opponentCrowns": {"$gte": 2},
                "team.trophies": {
                    "$lt": {
                        "$subtract": [
                            "$opponent.trophies",
                            {
                                "$multiply": [
                                    "$opponent.trophies",
                                    trophy_difference_percentage / 100,
                                ]
                            },
                        ]
                    }
                },
            }
        },
        {"$match": {"result": "win"}},
        {"$count": "victories"},
    ]

    results = list(DB["battles"].aggregate(pipeline))
    logging.debug(f"Pipeline results: {results}")
    return results


@app.route("/high_win_combos", methods=["POST"])
def high_win_combos():
    combo_size = int(request.form["combo_size"])
    win_percentage = float(request.form["win_percentage_combo"])
    start_time = request.form["start_time_combo"]
    end_time = request.form["end_time_combo"]
    results = card_combos_with_high_win_percentage(
        combo_size, win_percentage, start_time, end_time
    )
    logging.debug(f"Results: {results}")
    return render_template("results.html", results=results)


def card_combos_with_high_win_percentage(
    combo_size, min_win_percentage, start_time, end_time
):
    logging.debug(
        f"Querying for card combos of size {combo_size} with at least {min_win_percentage}% wins, from {start_time} to {end_time}"
    )

    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    pipeline = [
        # Filtra pelo periodo da batalha
        {
            "$match": {
                "battleTime": {"$gte": start_iso, "$lt": end_iso},
            },
        },
        # Separa os decks vencedores
        {
            "$project": {"winnerCards": "$winner.deck.name"},
        },
        # Cria um array de tamanho N referente ao combo de cartas
        {
            "$addFields": {
                "cardCombos": {" $slice": ["$winnerCards", 0, combo_size]},
            },
        },
        # Soma o total de jogos vitoriosos deste combo
        {
            "$group": {"_id": "$cardCombos", "totalWins": {"$sum": 1}},
        },
        # join na collection original para obter a qtd de batalhas totais
        {
            "$lookup": {
                "from": "battles",
                "pipeline": [
                    {
                        "$match": {
                            "battleTime": {"$gte": start_iso, "$lt": end_iso},
                        }
                    },
                    {"$count": "totalGames"},
                ],
                "as": "gameStats",
            }
        },
        # Calcula a taxa de ganho do combo em relacao ao total de batalhas
        {
            "$project": {
                "_id": "$_id",
                "winRate": {
                    "$multiply": [
                        {
                            "$divide": [
                                "$totalWins",
                                {
                                    "$ifNull": [
                                        {"$arrayElemAt": ["$gameStats.totalGames", 0]},
                                        1,
                                    ]
                                },
                            ]
                        },
                        100,
                    ]
                },
            }
        },
        # Filtra os resultados para incluir apenas aqueles com uma taxa de vitória superior a informada
        {"$match": {"winRate": {"$gt": min_win_percentage}}},
        # Organiza a resposta em ordem Descrescente
        {"$sort": {"winRate": -1}},
    ]

    results = list(DB["battles"].aggregate(pipeline))
    print(results)
    logging.debug(f"Pipeline results: {results}")
    return results


def get_card_names():
    try:
        card_names = DB["players"].distinct("deck.name")
        logging.debug(f"Card names: {card_names}")
        return card_names
    except Exception as err:
        logging.error(f"An error occurred while fetching card names: {err}")
        return []


def get_battle_dates():
    try:
        battle_dates = DB["battles"].distinct("battleTime")
        # Converter datas para strings no formato ISO sem a parte do tempo
        battle_dates = sorted(
            set(
                [
                    datetime.strptime(battle_date, "%Y%m%dT%H%M%S.%fZ")
                    .date()
                    .isoformat()
                    for battle_date in battle_dates
                ]
            )
        )
        logging.debug(f"Battle dates: {battle_dates}")
        return battle_dates
    except Exception as err:
        logging.error(f"An error occurred while fetching battle dates: {err}")
        return []


if __name__ == "__main__":
    app.run(debug=True)
