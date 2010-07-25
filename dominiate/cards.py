from game import curse, estate, duchy, province, copper, silver, gold
from game import Card, TrashDecision, DiscardDecision

# simple actions
village = Card('Village', 3, actions=2, cards=1)
woodcutter = Card('Woodcutter', 3, coins=2, buys=1)
smithy = Card('Smithy', 4, cards=3)
festival = Card('Festival', 5, coins=2, actions=2, buys=1)
market = Card('Market', 5, coins=1, cards=1, actions=1, buys=1)
laboratory = Card('Laboratory', 5, cards=2, actions=1)

def chapel_action(game):
    newgame = game.current_player().make_decision(
        TrashDecision(game, 0, 4)
    )
    return newgame

def cellar_action(game):
    newgame = game.current_player().make_decision(
        DiscardDecision(game)
    )
    card_diff = game.state().hand_size() - newgame.state().hand_size()
    return newgame.replace_current_state(newgame.state().draw(card_diff))

def warehouse_action(game):
    newgame = game.current_player().make_decision(
        DiscardDecision(game, 3, 3)
    )
    return newgame

def council_room_action(game):
    return game.change_other_states(delta_cards=1)

def militia_attack(game):
    return game.attack_with_decision(
        lambda g: DiscardDecision(g, 2, 2)
    )

chapel = Card('Chapel', 2, effect=chapel_action)
cellar = Card('Cellar', 2, actions=1, effect=cellar_action)
warehouse = Card('Warehouse', 3, cards=3, actions=1, effect=warehouse_action)
council_room = Card('Council Room', 5, cards=4, buys=1,
                    effect=council_room_action)
militia = Card('Militia', 4, coins=2, effect=militia_attack)
moat = Card('Moat', 2, cards=2, isDefense=True)

variable_cards = [village, cellar, smithy, festival, market, laboratory,
chapel, warehouse, council_room, militia, moat]

