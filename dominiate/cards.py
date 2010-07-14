from game import curse, estate, duchy, province, copper, silver, gold
from game import ActionCard

def basic_action(coins=0, cards=0, actions=0, buys=0):
    def theaction(game):
        if cards:
            game = game.current_draw_cards(cards)
        if (coins or actions or buys):
            game = game.change_current_state(
              delta_coins=coins,
              delta_actions=actions,
              delta_buys=buys
            )
        return game
    return theaction

def chapel_action():
    def theaction(game):
        raise NotImplementedError
    return theaction

class BasicActionCard(ActionCard):
    def __init__(self, name, cost, coins=0, cards=0, actions=0, buys=0):
        ActionCard.__init__(self, name, cost,
                           [basic_action(coins, cards, actions, buys)])
        self.cards = cards
        self.actions = actions
        self.pluscoins = coins
        self.buys = buys

village  = BasicActionCard('Village', 3, actions=2, cards=1)
woodcutter = BasicActionCard('Woodcutter', 3, coins=2, buys=1)
smithy   = BasicActionCard('Smithy', 4, cards=3)
festival = BasicActionCard('Festival', 5, coins=2, actions=2, buys=1)
market   = BasicActionCard('Market', 5, coins=1, cards=1, actions=1, buys=1)
laboratory = BasicActionCard('Laboratory', 5, actions=1, cards=2)

chapel = ActionCard('Chapel', 2, [chapel_action()])

variable_cards = [village, smithy, festival, market, laboratory, woodcutter]

