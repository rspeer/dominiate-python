from game import curse, estate, duchy, province, copper, silver, gold
from game import Card, TrashDecision

# simple actions
village = Card('Village', 3, actions=2, cards=1)
woodcutter = Card('Woodcutter', 3, coins=2, buys=1)
smithy = Card('Smithy', 4, cards=3)
festival = Card('Festival', 5, coins=2, actions=2, buys=1)
market = Card('Market', 5, coins=1, cards=1, actions=1, buys=1)
laboratory = Card('Laboratory', 5, cards=2, actions=1)

def chapel_action(game):
    stopped = False
    trashed = 0
    while not stopped and trashed < 4:
        newgame = game.current_player().make_decision(
            TrashDecision(game)
        )
        stopped = (newgame is game)
        game = newgame
        trashed += 1
    return game

def cellar_action(game):
    stopped = False
    cards = game.state().hand_size()
    while not stopped:
        newgame = game.current_player().make_decision(
            DiscardDecision(game)
        )
        stopped = (newgame is game)
        game = newgame
    card_diff = cards - game.state().hand_size()
    return game.replace_current_state(game.state().draw(card_diff))

def warehouse_action(game):
    for i in xrange(3):
        game = game.current_player().make_decision(
            DiscardDecision(game, allow_none=False)
        )
    return game

chapel = Card('Chapel', 2, effect=chapel_action)
cellar = Card('Cellar', 2, effect=cellar_action)
warehouse = Card('Warehouse', 3, cards=3, actions=1, effect=warehouse_action)

variable_cards = [village, smithy, festival, market, laboratory, woodcutter,
chapel, cellar, warehouse]

