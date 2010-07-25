from game import Game, BuyDecision, ActDecision, TrashDecision, DiscardDecision, MultiDecision, INF
import cards as c
import logging

class Player(object):
    def __init__(self, *args):
        raise NotImplementedError("Player is an abstract class")
    def make_decision(self, decision, state):
        assert state.player is self
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
        if decision.game.simulated:
            # Don't ask the player to tell the AI what they'll do!
            return self.substitute_ai().make_decision(decision)
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
    
    def substitute_ai(self):
        return BigMoney()


class AIPlayer(Player):
    def __init__(self):
        self.log = logging.getLogger(self.name)
    def setLogLevel(self, level):
        self.log.setLevel(level)
    def make_decision(self, decision):
        self.log.debug("Decision: %s" % decision)
        if isinstance(decision, BuyDecision):
            choice = self.make_buy_decision(decision)
        elif isinstance(decision, ActDecision):
            choice = self.make_act_decision(decision)
        elif isinstance(decision, DiscardDecision):
            choice = self.make_discard_decision(decision)
        elif isinstance(decision, TrashDecision):
            choice = self.make_trash_decision(decision)
        else:
            raise NotImplementedError
        return decision.choose(choice)

class BigMoney(AIPlayer):
    """
    This AI strategy provides reasonable defaults for many AIs. On its own,
    it aims to buy money, and then buy victory (the "Big Money" strategy).
    """
    def __init__(self, cutoff1=3, cutoff2=6):
        self.cutoff1 = cutoff1  # when to buy duchy instead of gold
        self.cutoff2 = cutoff2  # when to buy duchy instead of silver
        #FIXME: names are implemented all wrong
        if not hasattr(self, 'name'):
            self.name = 'BigMoney(%d, %d)' % (self.cutoff1, self.cutoff2)
        AIPlayer.__init__(self)
    
    def buy_priority_order(self, decision):
        """
        Provide a buy_priority by ordering the cards from least to most
        important.
        """
        provinces_left = decision.game.card_counts[c.province]
        if provinces_left <= self.cutoff1:
            return [None, c.estate, c.silver, c.duchy, c.province]
        elif provinces_left <= self.cutoff2:
            return [None, c.silver, c.duchy, c.gold, c.province]
        else:
            return [None, c.silver, c.gold, c.province]
    
    def buy_priority(self, decision, card):
        """
        Assign a numerical priority to each card that can be bought.
        """
        try:
            return self.buy_priority_order(decision).index(card)
        except ValueError:
            return -1
    
    def make_buy_decision(self, decision):
        """
        Choose a card to buy.

        By default, this chooses the card with the highest positive
        buy_priority.
        """
        choices = decision.choices()
        choices.sort(key=lambda x: self.buy_priority(decision, x))
        return choices[-1]
    
    def act_priority(self, decision, choice):
        """
        Assign a numerical priority to each action. Higher priority actions
        will be chosen first.
        """
        if choice is None: return 0
        return (100*choice.actions + 10*(choice.coins + choice.cards) +
                    choice.buys) + 1
    
    def make_act_decision(self, decision):
        """
        Choose an Action to play.

        By default, this chooses the action with the highest positive
        act_priority.
        """
        choices = decision.choices()
        choices.sort(key=lambda x: self.act_priority(decision, x))
        return choices[-1]
    
    def make_trash_decision_incremental(self, decision, choices, allow_none=True):
        "Choose a single card to trash."
        deck = decision.state().all_cards()
        money = sum([card.treasure + card.coins for card in deck])
        if c.curse in choices:
            return c.curse
        elif c.copper in choices and money > 3:
            return c.copper
        elif decision.game.round < 10 and c.estate in choices:
            # TODO: judge how many turns are left in the game and whether
            # an estate is worth it
            return c.estate
        elif allow_none:
            return None
        else:
            # oh shit, we don't know what to trash
            # get rid of whatever looks like it's worth the least
            choices.sort(key=lambda x: (x.vp, x.cost))
            return choices[0]

    def make_trash_decision(self, decision):
        """
        The default way to decide which cards to trash is to repeatedly
        choose one card to trash until None is chosen.

        TrashDecision is a MultiDecision, so return a list.
        """
        latest = False
        chosen = []
        choices = decision.choices()
        while choices and latest is not None and len(chosen) < decision.max:
            latest = self.make_trash_decision_incremental(
                decision, choices,
                allow_none = (len(chosen) >= decision.min)
            )
            if latest is not None:
                choices.remove(latest)
                chosen.append(latest)
        return chosen

    def make_discard_decision_incremental(self, decision, choices, allow_none=True):
        actions_sorted = [ca for ca in choices if ca.isAction()]
        actions_sorted.sort(key=lambda a: a.actions)
        plus_actions = sum([ca.actions for ca in actions_sorted])
        wasted_actions = len(actions_sorted) - plus_actions - decision.state().actions
        victory_cards = [ca for ca in choices if ca.isVictory() and
                         not ca.isAction() and not ca.isTreasure()]
        if wasted_actions > 0:
            return actions_sorted[0]
        elif len(victory_cards):
            return victory_cards[0]
        elif c.copper in choices:
            return c.copper
        elif allow_none:
            return None
        else:
            priority_order = sorted(choices,
              key=lambda ca: (ca.actions, ca.cards, ca.coins, ca.treasure))
            return priority_order[0]

    def make_discard_decision(self, decision):
        # TODO: make this good.
        # This probably involves finding all distinct sets of cards to discard,
        # of size decision.min to decision.max, and figuring out how well the
        # rest of your hand plays out (including things like the Cellar bonus).

        # Start with 
        #   game = decision.game().simulated_copy() ...
        # to avoid cheating.

        latest = False
        chosen = []
        choices = decision.choices()
        while choices and latest is not None and len(chosen) < decision.max:
            latest = self.make_discard_decision_incremental(
                decision, choices,
                allow_none = (len(chosen) >= decision.min)
            )
            if latest is not None:
                choices.remove(latest)
                chosen.append(latest)
        return chosen

