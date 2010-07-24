from collections import defaultdict
from game import BuyDecision, ActDecision, Game
from players import Player
from basic_ai import HillClimbBot
import cards as c

class DerivBot(HillClimbBot):
    """
    A bot that has some neat logic about the first and second derivatives
    of victory points. Pity it plays so badly, though.
    """
    def __init__(self, k):
        self.values = [{}, {}, {}]
        self.averages = [defaultdict(float), defaultdict(float),
          defaultdict(float)]
        self.current_values = {}
        self.k = k
        self.name = "DerivBot(%d)" % k
        self.samples = 0
        HillClimbBot.__init__(self, 1, 2)
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
                             game.card_counts, 0, simulated=True)
                state = game.simulate_partial_turn()
                hand = state.tableau + state.hand
                
                # How much is the hand worth without changing anything?
                actual_value = 0
                for coins, buys in state.simulate_hands(1, hand):
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
                        for coins, buys in state.simulate_hands(1, newhand):
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



