from collections import defaultdict
from game import MultiDecision, Game, INF
import cards as c

class Player(object):
    def __init__(self, *args):
        raise NotImplementedError("Player is an abstract class")
    def make_decision(self, decision, state):
        raise NotImplementedError
    def make_multi_decision(self, decision, state):
        raise NotImplementedError
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
        if isinstance(decision, MultiDecision):
            chosen = self.make_multi_decision(decision)
        else:
            chosen = self.make_single_decision(decision)
        return decision.choose(chosen)

    def make_single_decision(self, decision):
        for index, choice in enumerate(decision.choices()):
            print "\t[%d] %s" % (index, choice)
        choice = raw_input('Your choice: ')
        try:
            return decision.choices()[int(choice)]
        except (ValueError, IndexError):
            # Try again
            print "That's not a choice."
            return self.make_single_decision(decision)

    def make_multi_decision(self, decision):
        for index, choice in enumerate(decision.choices()):
            print "\t[%d] %s" % (index, choice)
        if decision.min != 0:
            print "Choose at least %d options." % decision.min
        if decision.max != INF:
            print "Choose at most %d options." % decision.max
        choices = raw_input('Your choices (separated by commas): ')
        try:
            chosen = [decision.choices()[int(choice.strip())]
                      for choice in choices.split(',')]
            return chosen
        except (ValueError, IndexError):
            # Try again
            print "That's not a valid list of choices."
            return self.make_multi_decision(decision)
        if len(chosen) < decision.min:
            print "You didn't choose enough things."
            return self.make_multi_decision(decision)
        if len(chosen) > decision.max:
            print "You chose too many things."
            return self.make_multi_decision(decision)
        for ch in chosen:
            if chosen.count(ch) > 1:
                print "You can't choose the same thing twice."
                return self.make_multi_decision(decision)


