from flask import Flask, render_template, request
import pymongo
import os
import logging
from dotenv import load_dotenv
from urllib.parse import quote
from datetime import datetime
from json2html import *

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
    html = json2html.convert(json=results)
    return render_template("results.html", results=html)


def victory_percentage_with_card(card_name, start_time, end_time):
    logging.debug(f"Querying for card: {card_name}, from {start_time} to {end_time}")

    # Converter start_time e end_time para o formato ISO8601
    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    logging.debug(f"Converted start_time: {start_iso}, end_time: {end_iso}")

    pipeline = [
        # Filtra pelo periodo da batalha
        {"$match": {"battleTime": {"$gte": start_iso, "$lt": end_iso}}},
        # Cria campos booleanos informando em qual lado a carta esta presente
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
                "_id": 0,
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
    html = json2html.convert(json=results)
    return render_template("results.html", results=html)


def decks_with_high_win_percentage(min_win_percentage, start_time, end_time):
    logging.debug(
        f"Querying for decks with at least {min_win_percentage}% wins, from {start_time} to {end_time}"
    )

    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    pipeline = [
        # Filtra pelo periodo da batalha e extrai apenas os decks completos
        {
            "$match": {
                "battleTime": {"$gte": start_iso, "$lt": end_iso},
                "winner.deck": {"$size": 8},
            },
        },
        # Extrai o deck do vencedor e marca cada entrada como uma vitoria
        {"$project": {"winnerDeck": "$winner.deck.name", "isWin": {"$literal": 1}}},
        # Agrupa os documentos pelo deck do vencedor e conta as vitórias para cada deck
        {"$group": {"_id": "$winnerDeck", "totalWins": {"$sum": "$isWin"}}},
        # Join na colecao original para contar quantas vezes cada deck
        # apareceu em uma partida dentro do intervalo, seja como vencedor ou perdedor.
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
        # Calcula a porcentagem total de vitórias para cada deck e
        # repassa o total de vitórias e de jogos.
        {
            "$project": {
                "_id": 0,
                "deck": "$_id",
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
        # Filtra os decks que tem uma taxa de vitoria superior ao limite informado
        {"$match": {"winPercentage": {"$gt": min_win_percentage}}},
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
    html = json2html.convert(json=results)
    return render_template("results.html", results=html)


def losses_with_card_combo(card_combo, start_time, end_time):
    logging.debug(
        f"Querying for defeats with card combo {card_combo}, from {start_time} to {end_time}"
    )

    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    pipeline = [
        # Filtra pelo periodo da batalha
        {"$match": {"battleTime": {"$gte": start_iso, "$lt": end_iso}}},
        # Cria um novo campo que informa se elementos do combo
        # estão no deck do perdedor ou nao
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
    # start_time = request.form["start_time_victory"]
    # end_time = request.form["end_time_victory"]
    results = specific_victory_conditions(card_name, trophy_diff)
    logging.debug(f"Results: {results}")
    html = json2html.convert(json=results)
    return render_template("results.html", results=html)


def specific_victory_conditions(card_name, trophy_difference_percentage):
    logging.debug(
        f"Querying for specific victories with card {card_name}, trophy diff {trophy_difference_percentage}%"
    )

    pipeline = [
        # Filtra batalhas on o perdedor derrubou, no minimo, 2 torres
        {"$match": {"loser.crowns": {"$gte": 2}}},
        # Busca dados de ambos vencedores e perdedores
        {
            "$lookup": {
                "from": "players",
                "let": {"winner_tag": "$winner.tag", "loser_tag": "$loser.tag"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$or": [
                                    {"$eq": ["$tag", "$$winner_tag"]},
                                    {"$eq": ["$tag", "$$loser_tag"]},
                                ]
                            }
                        }
                    }
                ],
                "as": "player_info",
            }
        },
        # Separa as informacoes do vencedor e do perdedor, que antes estavam combinados em player_info
        {
            "$addFields": {
                "winner_info": {
                    "$arrayElemAt": [
                        {
                            "$filter": {
                                "input": "$player_info",
                                "as": "info",
                                "cond": {"$eq": ["$$info.tag", "$winner.tag"]},
                            }
                        },
                        0,
                    ]
                },
                "loser_info": {
                    "$arrayElemAt": [
                        {
                            "$filter": {
                                "input": "$player_info",
                                "as": "info",
                                "cond": {"$eq": ["$$info.tag", "$loser.tag"]},
                            }
                        },
                        0,
                    ]
                },
            }
        },
        # Projeta os campos que verificam se o deck do vencedor contem a carta desejada
        # e se a diferença de trofeus satisfaz a condicao estabelecida.
        {
            "$project": {
                "trophyDifference": {
                    "$lt": [
                        {"$divide": ["$winner_info.trophies", "$loser_info.trophies"]},
                        {
                            "$subtract": [
                                1,
                                {"$divide": [trophy_difference_percentage, 100]},
                            ]
                        },
                    ]
                },
                "hasCardX": {"$in": [card_name, "$winner.deck.name"]},
            }
        },
        # Filtra as batalhas onde o vencedor tem uma porcentagem a menos de trofeus do que o perdedor
        # e utilizou a carta X.
        {"$match": {"trophyDifference": True, "hasCardX": True}},
        # Conta as vitorias que satisfazem os criterios
        {"$count": "victoriesWithCardX"},
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
    html = json2html.convert(json=results)
    return render_template("results.html", results=html)


def card_combos_with_high_win_percentage(
    combo_size, min_win_percentage, start_time, end_time
):
    logging.debug(
        f"Querying for card combos of size {combo_size} with at least {min_win_percentage}% wins, from {start_time} to {end_time}"
    )

    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    totalGames = DB["battles"].count_documents(
        {"battleTime": {"$gte": start_iso, "$lt": end_iso}}
    )

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
                "cardCombos": {"$slice": ["$winnerCards", combo_size]},
            },
        },
        # Soma o total de jogos vitoriosos deste combo
        {
            "$group": {"_id": "$cardCombos", "totalWins": {"$sum": 1}},
        },
        # Calcula a taxa de ganho do combo em relacao ao total de batalhas
        {
            "$project": {
                "_id": 0,
                "combo": "$_id",
                "winRate": {
                    "$multiply": [
                        {"$divide": ["$totalWins", {"$ifNull": [totalGames, 1]}]},
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
    logging.debug(f"Pipeline results: {results}")
    return results


@app.route("/card_win_after_update", methods=["POST"])
def card_win_after_update():

    card_name = request.form["card_name"]
    update_time = request.form["update_time"]
    results = card_win_rate_after_before_time(card_name, update_time)
    logging.debug(f"Results: {results}")
    html = json2html.convert(json=results)
    return render_template("results.html", results=html)


def card_win_rate_after_before_time(card_name, update_time):
    logging.debug(f"Querying for cards win dif after updates")

    update_iso = datetime.strptime(update_time, "%Y-%m-%d").strftime(
        "%Y%m%dT%H%M%S.000Z"
    )

    pipeline = [
        # Busca batalhas em que a carta especifica participou
        {
            "$match": {
                "$or": [{"winner.deck.name": card_name}, {"loser.deck.name": card_name}]
            }
        },
        # Projeta os campos que informa se a carta esta no lado vencedor.
        # cria tambem o campo mostrando se a batalha foi antes ou depois da data de update
        {
            "$project": {
                "cardInWinnerDeck": {"$in": [card_name, "$winner.deck.name"]},
                "isBeforeUpdate": {"$lt": ["$battleTime", update_iso]},
            }
        },
        # Divide os dados em dois grupos baseados no momento da batalha
        {
            "$facet": {
                # Soma as vitorias e conta os jogos totais antes do update
                "beforeUpdate": [
                    {"$match": {"isBeforeUpdate": True}},
                    {
                        "$group": {
                            "_id": None,
                            "totalWins": {
                                "$sum": {"$cond": ["$cardInWinnerDeck", 1, 0]}
                            },
                            "totalGames": {"$sum": 1},
                        }
                    },
                ],
                # Soma as vitorias e conta os jogos totais depois do update
                "afterUpdate": [
                    {"$match": {"isBeforeUpdate": False}},
                    {
                        "$group": {
                            "_id": None,
                            "totalWins": {
                                "$sum": {"$cond": ["$cardInWinnerDeck", 1, 0]}
                            },
                            "totalGames": {"$sum": 1},
                        }
                    },
                ],
            }
        },
        # Projeta os resultados de vitoria de cada periodo
        {
            "$project": {
                "beforeUpdate": {"$arrayElemAt": ["$beforeUpdate", 0]},
                "afterUpdate": {"$arrayElemAt": ["$afterUpdate", 0]},
            }
        },
        # Projeta o calculo das taxas de vitoria antes e depois do update
        {
            "$project": {
                "beforeWinRate": {
                    "$ifNull": [
                        {
                            "$multiply": [
                                {
                                    "$divide": [
                                        "$beforeUpdate.totalWins",
                                        "$beforeUpdate.totalGames",
                                    ]
                                },
                                100,
                            ]
                        },
                        0,
                    ]
                },
                "afterWinRate": {
                    "$ifNull": [
                        {
                            "$multiply": [
                                {
                                    "$divide": [
                                        "$afterUpdate.totalWins",
                                        "$afterUpdate.totalGames",
                                    ]
                                },
                                100,
                            ]
                        },
                        0,
                    ]
                },
            }
        },
    ]

    results = list(DB["battles"].aggregate(pipeline))
    print(results)
    logging.debug(f"Pipeline results: {results}")
    return results


@app.route("/cards_high_win_less_used", methods=["POST"])
def cards_high_win_less_used():

    win_percentage = float(request.form["win_percentage"])
    usage_percentage = float(request.form["usage_percentage"])
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]
    results = cards_win_rate_usage_rate(
        win_percentage, usage_percentage, start_time, end_time
    )
    logging.debug(f"Results: {results}")
    html = json2html.convert(json=results)
    return render_template("results.html", results=html)


def cards_win_rate_usage_rate(win_percentage, usage_percentage, start_time, end_time):

    logging.debug(f"Querying for cards win rate and usage rate")

    start_iso = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")
    end_iso = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y%m%dT%H%M%S.000Z")

    # obtem a quantidade total de batalhas
    totalBattles = DB["battles"].count_documents({})

    pipeline = [
        # Filtra as batalhas pelo periodo
        {
            "$match": {
                "battleTime": {"$gte": start_iso, "$lte": end_iso},
            },
        },
        # Projeta campo com todas as cartas e outro campos so com as cartas do vencedor
        {
            "$project": {
                "allCards": {
                    "$setUnion": ["$winner.deck.name", "$loser.deck.name"],
                },
                "winnerCards": "$winner.deck.name",
            },
        },
        # Destrincha o array allCards para tratar cada carta separadamente
        {
            "$unwind": "$allCards",
        },
        # Projeta a carta em questao e se ela faz parte do deck vencedor
        {
            "$project": {
                "_id": "$allCards",
                "winnerHasCard": {"$in": ["$allCards", "$winnerCards"]},
            },
        },
        # agrupa a resposta por carta em questao e seus totais de uso e vitoria
        {
            "$group": {
                "_id": "$_id",
                "totalWins": {"$sum": {"$cond": ["$winnerHasCard", 1, 0]}},
                "totalUses": {"$sum": 1},
            },
        },
        # Projeta a resposta final calculando as taxas de acordo com a carta em questao
        {
            "$project": {
                "_id": 0,
                "card": "$_id",
                "winRate": {
                    "$multiply": [{"$divide": ["$totalWins", "$totalUses"]}, 100],
                },
                "usageRate": {
                    "$multiply": [
                        {"$divide": ["$totalUses", totalBattles]},
                        100,
                    ],
                },
            },
        },
        # Filtra a resposta de acordo com os parametros
        {
            "$match": {
                "winRate": {"$gt": win_percentage},
                "usageRate": {"$lt": usage_percentage},
            }
        },
        # ordena a resposta de acodo com o winRate decrescente
        {
            "$sort": {"winRate": -1},
        },
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

        return [battle_dates[0], battle_dates[len(battle_dates) - 1]]
    except Exception as err:
        logging.error(f"An error occurred while fetching battle dates: {err}")
        return []


if __name__ == "__main__":
    app.run(debug=True)
