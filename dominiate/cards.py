from game import curse, estate, duchy, province, copper, silver, gold
from game import ActionCard, TrashDecision

def chapel_action():
    def theaction(game):
        stopped = False
        while not stopped:
            newgame = game.current_player().make_decision(
                TrashDecision(game)
            )
            stopped = (newgame is game)
            game = newgame
        return game
    return theaction

village  = ActionCard('Village', 3, [], actions=2, cards=1)
woodcutter = ActionCard('Woodcutter', 3, [], coins=2, buys=1)
smithy   = ActionCard('Smithy', 4, [], cards=3)
festival = ActionCard('Festival', 5, [], coins=2, actions=2, buys=1)
market   = ActionCard('Market', 5, [], coins=1, cards=1, actions=1, buys=1)
laboratory = ActionCard('Laboratory', 5, [], actions=1, cards=2)

chapel = ActionCard('Chapel', 2, [chapel_action()])

variable_cards = [village, smithy, festival, market, laboratory, woodcutter, chapel]

