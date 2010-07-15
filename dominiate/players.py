from collections import defaultdict
from game import BuyDecision, ActDecision, Game
import cards as c

class Player(object):
    def __init__(self, *args):
        raise NotImplementedError("Player is an abstract class")
    def make_decision(self, decision, state):
        raise NotImplementedError("Player is an abstract class")
    def __str__(self):
        return self.name
    def __repr__(self):
        return "<Player: %s>" % self.name
    def before_turn(self, game):
        pass
    def after_turn(self, game):
        pass

class HumanPlayer(Player):
    def __init__(self, name):
        self.name = name
    def make_decision(self, decision):
        state = decision.game.state()
        print state.hand
        print "Deck: %d cards" % state.deck_size()
        print "VP: %d" % state.score()
        print decision
        for index, choice in enumerate(decision.choices()):
            print "\t[%d] %s" % (index, choice)
        choice = raw_input('Your choice: ')
        try:
            chosen = decision.choices()[int(choice)]
        except (ValueError, IndexError):
            # Try again
            print "That's not a choice."
            return make_decision(self, decision)
        newgame = decision.choose(chosen)
        return newgame

