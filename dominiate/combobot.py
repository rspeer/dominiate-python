# Thoughts on a combo bot:
# 
# It should probably run the BigMoney strategy by default; it will not work
# for minimalist (Chapel) or maximalist (Garden) strategies.
# 
# A ComboBot aims to get a certain set of cards. It pays an opportunity cost
# in the number of turns it could have been running BigMoney. How do we compare
# this? I think in the average value of cards it gains per turn, plus possibly
# a constant bonus for trashing useless cards.
#
# We're looking for strategies that gain more per turn than BigMoney would
# after being run for the same number of turns.

from basic_ai import BigMoney
from game import Game
import cards as c
import numpy as np

def deck_value(deck):
    return sum([card.cost for card in deck]) - len(deck)

def big_money_baseline():
    improvements = np.zeros((30,))
    counts = np.zeros((30,), dtype='int32')
    for iteration in xrange(10000):
        game = Game.setup([BigMoney(1, 2)])
        for turn in xrange(30):
            before_value = deck_value(game.state().all_cards())
            game = game.take_turn()
            after_value = deck_value(game.state().all_cards())
            delta = after_value - before_value
            improvements[turn] += delta
            counts[turn] += 1
            if game.over(): break
        avg = [imp/count for imp, count in zip(improvements, counts)]
        print avg
        print counts
    return avg

# precalculated; easier than loading a pickle or something
baseline = np.array(
   [1.8226, 1.8302, 2.4849, 2.5363, 3.2383, 3.6883, 3.9152, 4.4961,
    4.5271, 4.8773, 4.9464, 4.9591, 5.0117, 5.2145, 5.2473, 5.2609,
    5.1505, 5.1500, 5.2662, 5.4229]
)

class IdealistComboBot(BigMoney):
    def __init__(self, strategy, name=None):
        self.strategy = strategy
        self.strategy_on = True
        self.strategy_complete = False
        if name is None:
            self.name = 'IdealistComboBot(%s)' % (strategy)
        else:
            self.name = name
        BigMoney.__init__(self, 1, 2)
    
    def before_turn(self, game):
        current_cards = game.state().all_cards()
        priority = []
        needed = {}
        pending = False
        for card, round in self.strategy:
            if card not in needed: needed[card] = 0
            if round <= game.round:
                needed[card] += 1
            else:
                pending = True
        for card in needed:
            needed[card] -= current_cards.count(card)
            if needed[card] > 0: priority.append(card)

        priority.sort(key=lambda card: (needed[card], card.cost))
        self.strategy_priority = priority
        self.log.debug('Strategy: %s' % self.strategy_priority)
        self.strategy_on = bool(priority)
        self.strategy_complete = not (priority or pending)
    
    def buy_priority_order(self, decision):
        if self.strategy_complete:
            return BigMoney.buy_priority_order(self, decision)
        else:
            return [None, c.silver, c.gold, c.province] + self.strategy_priority

    def make_buy_decision(self, decision):
        choices = decision.choices()
        choices.sort(key=lambda x: self.buy_priority(decision, x))
        return choices[-1]
    
    def test(self):
        improvements = np.zeros((30,))
        counts = np.zeros((30,), dtype='int32')
        for iteration in xrange(100):
            game = Game.setup([self], c.variable_cards, simulated=False)
            turn_count = 0
            # Find a state where the strategy is done and the deck is
            # about to be shuffled
            while not (game.card_counts[c.province] <= 1 or
                       (game.current_player().strategy_complete and 
                        len(game.state().drawpile) < 5)):
                game = game.take_turn()
                turn_count += 1
                assert game.round == turn_count
            if turn_count <= 18:
                for trial in xrange(10):
                    # take one more turn to shuffle the deck
                    game1 = game.take_turn()
                    # test the next turn
                    before_value = deck_value(game1.state().all_cards())
                    game2 = game1.take_turn()
                    after_value = deck_value(game2.state().all_cards())
                    improvements[turn_count+1] +=\
                      (after_value - before_value - baseline[turn_count+1])
                    counts[turn_count+1] += 1
            avg = improvements/counts
            overall = np.sum(improvements)/np.sum(counts)
            self.log.info(str(overall))
            self.log.info('\n%s' % avg)
        self.log.info('Overall gain: %s' % overall)
        return overall

class ComboBot(IdealistComboBot):
    def buy_priority_order(self, decision):
        if self.strategy_complete:
            return BigMoney.buy_priority_order(self, decision)
        else:
            return [None, c.silver] + self.strategy_priority + [c.gold, c.province]


smithyComboBot = ComboBot([(c.smithy, 2), (c.smithy, 6)],
                   name='smithyComboBot')

chapelComboBot = ComboBot([(c.chapel, 0),
                           (c.laboratory, 0),
                           (c.laboratory, 0),
                           (c.laboratory, 0),
                           (c.market, 0),
                          ], name='chapelComboBot')
chapelComboBot2 = ComboBot([(c.chapel, 0), (c.smithy, 2), (c.smithy, 6),
                            (c.festival, 0), (c.festival, 4)],
                   name='chapelComboBot2')

if __name__ == '__main__':
    strategy = chapelComboBot
    strategy.setLogLevel(logging.INFO)
    strategy.test()

