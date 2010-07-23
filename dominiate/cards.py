from game import curse, estate, duchy, province, copper, silver, gold
from game import Card, TrashDecision

def chapel_action(game):
    stopped = False
    while not stopped:
        newgame = game.current_player().make_decision(
            TrashDecision(game)
        )
        stopped = (newgame is game)
        game = newgame
    return game

village = Card('Village', 3, actions=2, cards=1)
woodcutter = Card('Woodcutter', 3, coins=2, buys=1)
smithy = Card('Smithy', 4, cards=3)
festival = Card('Festival', 5, coins=2, actions=2, buys=1)
market = Card('Market', 5, coins=1, cards=1, actions=1, buys=1)
laboratory = Card('Laboratory', 5, cards=2, actions=1)
chapel = Card('Chapel', 2, effect=chapel_action)

variable_cards = [village, smithy, festival, market, laboratory, woodcutter, chapel]

