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

class AIPlayer(Player):
    def make_decision(self, decision):
        if isinstance(decision, BuyDecision):
            choice = self.make_buy_decision(decision)
            if not decision.game.simulated:
                print self.name, "buys", choice
        elif isinstance(decision, ActDecision):
            choice = self.make_act_decision(decision)
            if not decision.game.simulated:
                print self.name, "plays", choice
        return decision.choose(choice)

class LameBot(AIPlayer):
    def __init__(self, cutoff1=3, cutoff2=6):
        self.cutoff1 = cutoff1  # when to buy duchy instead of gold
        self.cutoff2 = cutoff2  # when to buy duchy instead of silver
        self.name = 'LameBot(%d, %d)' % (self.cutoff1, self.cutoff2)
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
    def make_trash_decision(self, decision):
        choices = decision.choices()
        if c.copper in choices:
            return c.copper
        elif len(decision.deck()) < 20 and c.estate in choices:
            return c.estate
        else:
            return None

class SmithyBot(LameBot):
    def __init__(self, cutoff1=3, cutoff2=6, cards_per_smithy=8):
        LameBot.__init__(self, cutoff1, cutoff2)
        self.cards_per_smithy = 8
        self.name = 'SmithyBot(%d, %d, %d)' % (cutoff1, cutoff2,
        cards_per_smithy)
    
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


class HillClimbBot(LameBot):
    def __init__(self, cutoff1=2, cutoff2=3, simulation_steps=100):
        LameBot.__init__(self, cutoff1, cutoff2)
        self.simulation_steps = simulation_steps
        self.name = 'HillClimbBot(%d, %d, %d)' % (cutoff1, cutoff2,
        simulation_steps)

    def buy_priority(self, decision, card):

        game = decision.choose(card)
        state = game.state()
        total = 0
        if card is None: add = ()
        else: add = (card,)
        for coins, buys in state.simulate(self.simulation_steps, add):
            if coins > buys*8: coins = buys*8
            if (coins - (buys-1)*8) in (1, 7):  # there exists a useless coin
                coins -= 1
            total += coins

        # gold is better than it seems
        if card == c.gold: total += self.simulation_steps/2
        print card, ":", total
        return total
    
    def act_priority(self, decision, choice):
        if choice is None: return 0
        elif isinstance(choice, c.BasicActionCard):
            return (100*choice.actions + 10*(choice.pluscoins + choice.cards) +
                    choice.buys)
        else:
            raise ValueError("what kind of action is this?")
            return -1
    
    def make_act_decision(self, decision):
        choices = decision.choices()
        choices.sort(key=lambda x: self.act_priority(decision, x))
        return choices[-1]
    
    def make_buy_decision(self, decision):
        choices = decision.choices()
        provinces_left = decision.game.card_counts[c.province]
        
        if c.province in choices: return c.province
        if c.duchy in choices and provinces_left <= self.cutoff2:
            return c.duchy
        if c.estate in choices and provinces_left <= self.cutoff1:
            return c.estate
        return LameBot.make_buy_decision(self, decision)

class Contrafactus(HillClimbBot):
    def __init__(self, cutoff1, cutoff2, k):
        LameBot.__init__(self, cutoff1, cutoff2)
        self.name = "Contrafactus(%d, %d, %d)" % (cutoff1, cutoff2, k)
        self.cache = {}
        self.k = k
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
        #print "%12s: %+3.3f %+3.3f %+3.3f" % (newcard, computed, cached, result)
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
                if coins > buys*8: coins = buys*8
                if (coins - (buys-1)*8) in (1, 7):  # there exists a useless coin
                    coins -= 1
                total += coins
            print add, ":", total
            if total > best_total:
                best_total = total
        return best_total


class DerivBot(HillClimbBot):
    def __init__(self, k):
        self.values = [{}, {}, {}]
        self.averages = [defaultdict(float), defaultdict(float),
          defaultdict(float)]
        self.current_values = {}
        self.k = k
        self.name = "DerivBot(%d)" % k
        self.samples = 0
    def buy_value(self, coins, buys, order):
        value = 0
        for j in xrange(buys):
            if coins < 2: break        # no, coppers are not good
            for card, cardval in order:
                if card.cost <= coins:
                    coins -= card.cost
                    value += cardval
                    break
        return value
    def update_values(self, game):
        # 0th order and initialization
        for card in game.card_choices():
            self.values[0][card] = card.vp
            self.values[1][card] = 0
            self.values[2][card] = 0
        vp_order = sorted(self.values[0].items(), key=lambda x: -x[1])

        avg_hand_size = 0.0
        avg_provinces = 0.0
        for deriv in (1, 2):
            prev_order = sorted(self.values[deriv-1].items(), key=lambda x: -x[1])
            for iter in xrange(self.k):
                game = Game([game.state().simulation_state()],
                             game.card_counts, simulated=True)
                state = game.simulate_partial_turn()
                hand = state.tableau + state.hand
                
                # How much is the hand worth without changing anything?
                actual_value = 0
                for coins, buys in state.simulate(1, hand):
                    actual_value = self.buy_value(coins, buys, prev_order)
                if coins >= 8:
                    avg_provinces += 1.0 / self.k / 2

                n = len(hand)
                avg_hand_size += float(n) / self.k / 2
                for card in game.card_choices():
                    for i in range(len(hand)):
                        newhand = hand[:i] + (card,) + hand[i+1:]

                        # Only one simulation step will be necessary, most of the time.
                        # The only variance comes in if we draw extra cards.
                        for coins, buys in state.simulate(1, newhand):
                            value = self.buy_value(coins, buys, prev_order) - actual_value
                            self.values[deriv][card] += float(value) / self.k / n
                # TODO: take into account cards you gain/trash
        
        # turns_left = provinces_left / (provinces/turn)
        if avg_provinces == 0.0: avg_provinces = 0.1
        turns_left_in_game = (game.card_counts[c.province] /
          ((avg_provinces+0.5) * game.num_players()))
        print "Estimated turns left:", turns_left_in_game

        # reshuffles = (cards/turn) / (cards/deck) * turns_left
        reshuffles_left = (avg_hand_size / len(game.state().all_cards()) *
          turns_left_in_game)

        # compensate for cards in deck
        reshuffles_left -= \
          float(len(game.state().drawpile)) / game.state().deck_size()
        
        factors = [1.0, 0.0, 0.0]
        factors[1] = max(reshuffles_left, 0)
        factors[2] = max(reshuffles_left * (reshuffles_left-1)/2, 0)
        print "%12s  % 7.3f % 7.3f % 7.3f" % (('',) + tuple(factors))
        for card in game.card_choices():
            weighted_values = [0, 0, 0]
            for order in range(3):
                weighted_values[order] = (
                  self.values[order][card] * 0.6 +
                  self.averages[order][card] * 0.4
                )
                self.averages[order][card] = (
                  (self.averages[order][card] * self.samples) +
                  self.values[order][card]
                ) / (self.samples + 1.0)
            
            totalvalue = 0.0
            for value, factor in zip(weighted_values, factors):
                totalvalue += value*factor
            if card == c.province:
                # Provinces are better than this calculation would imply.
                # When you have a province, someone else doesn't have it.
                # So add another 12 for good measure.
                totalvalue += 12.0
            self.current_values[card] = totalvalue
            print "%12s: % 7.3f % 7.3f % 7.3f  % 7.3f % 7.3f % 7.3f % 7.3f" %\
              (card, self.values[0][card], self.values[1][card], 
               self.values[2][card], self.averages[0][card],
               self.averages[1][card], self.averages[2][card], totalvalue)
        self.samples += 1

    def buy_priority(self, decision, card):
        if card is None: return 0.0
        else: return self.current_values[card]
    
    def make_buy_decision(self, decision):
        print "BuyDecision (%d coins): hand is %s" % (
          decision.state().hand_value(), decision.state().hand
        )
        print "Deck is now:", sorted(decision.game.state().all_cards())
        choices = decision.choices()
        choices.sort(key=lambda x: self.buy_priority(decision, x))
        return choices[-1]

    def before_turn(self, game):
        self.update_values(game)
        
