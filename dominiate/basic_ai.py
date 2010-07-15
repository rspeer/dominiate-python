from collections import defaultdict
from game import BuyDecision, ActDecision, TrashDecision, Game, TreasureCard
from players import Player
import cards as c
import logging, sys

class AIPlayer(Player):
    def __init__(self):
        self.log = logging.getLogger(self.name)
    def setLogLevel(self, level):
        self.log.setLevel(level)
    def make_decision(self, decision):
        self.log.debug("Decision: %s" % decision)
        if isinstance(decision, BuyDecision):
            choice = self.make_buy_decision(decision)
            if not decision.game.simulated:
                self.log.info("I buy %s" % (choice))
        elif isinstance(decision, ActDecision):
            choice = self.make_act_decision(decision)
            if not decision.game.simulated:
                self.log.info("I play %s" % choice)
        elif isinstance(decision, TrashDecision):
            choice = self.make_trash_decision(decision)
            if not decision.game.simulated:
                self.log.info("I trash %s" % choice)
        else:
            raise NotImplementedError
        return decision.choose(choice)

class BigMoney(AIPlayer):
    def __init__(self, cutoff1=3, cutoff2=6):
        self.cutoff1 = cutoff1  # when to buy duchy instead of gold
        self.cutoff2 = cutoff2  # when to buy duchy instead of silver
        #FIXME: names are implemented all wrong
        if not hasattr(self, 'name'):
            self.name = 'BigMoney(%d, %d)' % (self.cutoff1, self.cutoff2)
        AIPlayer.__init__(self)
    
    def buy_priority_order(self, decision):
        provinces_left = decision.game.card_counts[c.province]
        if provinces_left <= self.cutoff1:
            return [None, c.estate, c.silver, c.duchy, c.province]
        elif provinces_left <= self.cutoff2:
            return [None, c.silver, c.duchy, c.gold, c.province]
        else:
            return [None, c.silver, c.gold, c.province]
    
    def buy_priority(self, decision, card):
        try:
            return self.buy_priority_order(decision).index(card)
        except ValueError:
            return -1
    
    def make_buy_decision(self, decision):
        choices = decision.choices()
        choices.sort(key=lambda x: self.buy_priority(decision, x))
        return choices[-1]
    
    def act_priority(self, decision, choice):
        if choice is None: return 0
        return (100*choice.actions + 10*(choice.pluscoins + choice.cards) +
                    choice.buys) + 1
    
    def make_act_decision(self, decision):
        choices = decision.choices()
        choices.sort(key=lambda x: self.act_priority(decision, x))
        return choices[-1]
    
    def make_trash_decision(self, decision):
        choices = decision.choices()
        deck = decision.state().all_cards()
        money = sum([card.coins for card in deck if isinstance(card, TreasureCard)])
        if c.copper in choices and money > 3:
            return c.copper
        elif decision.game.round < 10 and c.estate in choices:
            # TODO: judge how many turns are left in the game and whether
            # an estate is worth it
            return c.estate
        else:
            return None

class SmithyBot(BigMoney):
    def __init__(self, cutoff1=3, cutoff2=6, cards_per_smithy=8):
        self.cards_per_smithy = 8
        self.name = 'SmithyBot(%d, %d, %d)' % (cutoff1, cutoff2,
        cards_per_smithy)
        BigMoney.__init__(self, cutoff1, cutoff2)
    
    def num_smithies(self, state):
        return list(state.all_cards()).count(c.smithy)

    def buy_priority_order(self, decision):
        state = decision.state()
        provinces_left = decision.game.card_counts[c.province]
        if provinces_left <= self.cutoff1:
            order = [None, c.estate, c.silver, c.duchy, c.province]
        elif provinces_left <= self.cutoff2:
            order = [None, c.silver, c.smithy, c.duchy, c.gold, c.province]
        else:
            order = [None, c.silver, c.smithy, c.gold, c.province]
        if ((self.num_smithies(state) + 1) * self.cards_per_smithy
           > state.deck_size()) and (c.smithy in order):
            order.remove(c.smithy)
        return order

    def make_act_decision(self, decision):
        return c.smithy

class HillClimbBot(BigMoney):
    def __init__(self, cutoff1=2, cutoff2=3, simulation_steps=100):
        self.simulation_steps = simulation_steps
        self.name = 'HillClimbBot(%d, %d, %d)' % (cutoff1, cutoff2,
        simulation_steps)
        BigMoney.__init__(self, cutoff1, cutoff2)

    def buy_priority(self, decision, card):
        state = decision.state()
        total = 0
        if card is None: add = ()
        else: add = (card,)
        for coins, buys in state.simulate(self.simulation_steps, add):
            total += buying_value(coins, buys)

        # gold is better than it seems
        if card == c.gold: total += self.simulation_steps/2
        print card, ":", total
        return total
    
    def make_buy_decision(self, decision):
        choices = decision.choices()
        provinces_left = decision.game.card_counts[c.province]
        
        if c.province in choices: return c.province
        if c.duchy in choices and provinces_left <= self.cutoff2:
            return c.duchy
        if c.estate in choices and provinces_left <= self.cutoff1:
            return c.estate
        return BigMoney.make_buy_decision(self, decision)

class Contrafactus(HillClimbBot):
    def __init__(self, cutoff1, cutoff2, k):
        self.name = "Contrafactus(%d, %d, %d)" % (cutoff1, cutoff2, k)
        self.cache = {}
        self.k = k
        BigMoney.__init__(self, cutoff1, cutoff2)
    def buy_priority(self, decision, newcard):
        """
        We're going to calculate the average benefit we would get by replacing
        a card from this hand with the card we intend to buy, answering the
        question "How much better would this hand be with card x in it?"
        """
        # First of all, for the null buy, the answer is zero.
        if newcard is None: return 0
        
        total = 0
        for iter in xrange(self.k):
            game = Game([decision.state().simulation_state()],
                         {c.province: 12}, simulated=True)
            state = game.simulate_partial_turn()
            hand = state.tableau + state.hand
            
            # How much is the hand worth without changing anything?
            actual_value = 0
            for coins, buys in state.simulate(1, hand):
                actual_value = buying_value(coins, buys)

            n = len(hand)
            for i in range(len(hand)):
                newhand = hand[:i] + (newcard,) + hand[i+1:]

                # Only one simulation step will be necessary, most of the time.
                # The only variance comes in if we draw extra cards.
                for coins, buys in state.simulate(1, newhand):
                    value = buying_value(coins, buys) - actual_value
                    total += float(value) / self.k / n
        computed = total
        cached = self.cache.get(newcard, 1.0)
        self.cache[newcard] = cached*0.95 + computed*0.05
        result = computed*0.8 + cached*0.2
        print "%12s: %+3.3f %+3.3f %+3.3f" % (newcard, computed, cached, result)
        return result

def buying_value(coins, buys):
    if coins > buys*8: coins = buys*8
    if (coins - (buys-1)*8) in (1, 7):  # there exists a useless coin
        coins -= 1
    return coins

class PairBot(HillClimbBot):
    def buy_priority(self, decision, card):
        provinces_left = decision.game.card_counts[c.province]
        if card == c.copper: return -1
        if card == c.province: return 100*self.simulation_steps
        if card == c.gold: return 75*self.simulation_steps
        if card == c.duchy and provinces_left <= self.cutoff2:
            return 90*self.simulation_steps
        if card == c.estate and provinces_left <= self.cutoff1:
            return 80*self.simulation_steps
        
        best_total = 0
        for card2 in decision.choices():
            if card is None:
                if card2 is not None: continue
            else:
                if not isinstance(card2, c.ActionCard): continue
            if card is None: add = ()
            else: add = (card, card2)

            game = decision.choose(card)
            state = game.state()
            total = 0

            for coins, buys in state.simulate(self.simulation_steps, add):
                total += buying_value(coins, buys)
            print add, ":", total
            if total > best_total:
                best_total = total
        return best_total

