import random
import logging
mainLog = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARN)

INF = ()

class Card(object):
    """
    Represents a class of card.

    To save computation, only one of each card should be constructed. Decks can
    contain many references to the same Card object.
    """
    def __init__(self, name, cost, treasure=0, vp=0, coins=0, cards=0,
                 actions=0, buys=0, potionCost=0, effect=(), isAttack=False,
                 isDefense=False, reaction=(), duration=()):
        self.name = name
        self.cost = cost
        self.potionCost = potionCost
        if isinstance(treasure, int):
            self.treasure = treasure
        else:
            self.treasure = property(treasure)
        if isinstance(vp, int):
            self.vp = vp
        else:
            self.vp = property(vp)
        self.coins = coins
        self.cards = cards
        self.actions = actions
        self.buys = buys
        self._isAttack = isAttack
        self._isDefense = isDefense
        if not isinstance(effect, (tuple, list)):
            self.effect = (effect,)
        else:
            self.effect = effect
        self.reaction = reaction
        self.duration = duration

    def isVictory(self):
        return self.vp > 0

    def isCurse(self):
        return self.vp < 0

    def isTreasure(self):
        return self.treasure > 0

    def isAction(self):
        return (self.coins or self.cards or self.actions or self.buys or
                self.effect)

    def isAttack(self):
        return self._isAttack

    def isDefense(self):
        return self._isDefense

    def perform_action(self, game):
        assert self.isAction()
        if self.cards:
            game = game.current_draw_cards(self.cards)
        if (self.coins or self.actions or self.buys):
            game = game.change_current_state(
              delta_coins=self.coins,
              delta_actions=self.actions,
              delta_buys=self.buys
            )
        for action in self.effect:
            game = action(game)
        return game

    def __str__(self): return self.name
    def __cmp__(self, other):
        if other is None: return -1
        return cmp((self.cost, self.name), 
                   (other.cost, other.name))
    def __hash__(self):
        return hash(self.name)
    def __repr__(self): return self.name

# define the cards that are in every game
curse    = Card('Curse', 0, vp=-1)
estate   = Card('Estate', 2, vp=1)
duchy    = Card('Duchy', 5, vp=3)
province = Card('Province', 8, vp=6)

copper = Card('Copper', 0, treasure=1)
silver = Card('Silver', 3, treasure=2)
gold   = Card('Gold', 6, treasure=3)

class PlayerState(object):
    """
    A PlayerState represents all the game state that is particular to a player,
    including the number of actions, buys, and +coins they have.
    """
    def __init__(self, player, hand, drawpile, discard, tableau, actions=0,
                 buys=0, coins=0):
        self.player = player
        self.actions = actions;   assert isinstance(self.actions, int)
        self.buys = buys;         assert isinstance(self.buys, int)
        self.coins = coins;       assert isinstance(self.coins, int)
        self.hand = hand;         assert isinstance(self.hand, tuple)
        self.drawpile = drawpile; assert isinstance(self.drawpile, tuple)
        self.discard = discard;   assert isinstance(self.discard, tuple)
        self.tableau = tableau;   assert isinstance(self.tableau, tuple)
        # TODO: duration cards
    
    @staticmethod
    def initial_state(player):
        # put it all in the discard pile so it auto-shuffles, then draw
        return PlayerState(player, hand=(), drawpile=(),
        discard=(copper,)*7 + (estate,)*3, tableau=()).next_turn()
    
    def change(self, delta_actions=0, delta_buys=0, delta_cards=0, delta_coins=0):
        """
        Change the number of actions, buys, cards, or coins available on this
        turn.
        """
        state= PlayerState(self.player, self.hand, self.drawpile, self.discard,
                           self.tableau, self.actions+delta_actions,
                           self.buys+delta_buys, self.coins+delta_coins)
        assert delta_cards >= 0
        if delta_cards > 0:
            return state.draw(delta_cards)
        else: return state
    
    def deck_size(self):
        return len(self.all_cards())
    __len__ = deck_size

    def all_cards(self):
        return self.hand + self.tableau + self.drawpile + self.discard

    def hand_value(self):
        """How many coins can the player spend?"""
        return self.coins + sum(card.treasure for card in self.hand)

    def hand_size(self):
        return len(self.hand)

    def is_defended(self):
        return any(x.isDefense() for x in self.hand)
    
    def get_reactions(self):
        """
        TODO: implement complex reactions like Secret Chamber
        """
        return []

    def draw(self, n=1):
        """
        Returns a new PlayerState in which n cards have been drawn (shuffling
        if necessary).
        """
        if len(self.drawpile) >= n:
            return PlayerState(
              self.player, self.hand+self.drawpile[:n], self.drawpile[n:],
              self.discard, self.tableau, self.actions, self.buys, self.coins
            )
        elif self.discard:
            got = self.drawpile
            newdraw = list(self.discard)
            random.shuffle(newdraw)

            state2 = PlayerState(
              self.player, self.hand+got, tuple(newdraw), (), self.tableau,
              self.actions, self.buys, self.coins
            )
            return state2.draw(n-len(got))
        else:
            return PlayerState(
              self.player, self.hand+self.drawpile, (), (), self.tableau,
              self.actions, self.buys, self.coins
            )

    def next_turn(self):
        """
        First, discard everything. Then, get 5 cards, 1 action, and 1 buy.
        """
        return PlayerState(
          self.player, (), self.drawpile, self.discard+self.hand+self.tableau,
          (), actions=1, buys=1, coins=0
        ).draw(5)

    def gain(self, card):
        "Gain a single card."
        return PlayerState(
          self.player, self.hand, self.drawpile, self.discard+(card,),
          self.tableau, self.actions, self.buys, self.coins
        )
    
    def gain_cards(self, cards):
        "Gain multiple cards."
        return PlayerState(
          self.player, self.hand, self.drawpile, self.discard+cards,
          self.tableau, self.actions, self.buys, self.coins
        )

    def play_card(self, card):
        """
        Play a card from the hand into the tableau.

        Decreasing the number of actions available is handled in
        play_action(card).
        """

        index = list(self.hand).index(card)
        newhand = self.hand[:index] + self.hand[index+1:]
        result = PlayerState(
          self.player, newhand, self.drawpile, self.discard,
          self.tableau+(card,), self.actions, self.buys, self.coins
        )
        assert len(self) == len(result)
        return result
    
    def play_action(self, card):
        """
        Play an action card, putting it in the tableau and decreasing the
        number of actions remaining.

        This does not actually put the Action into effect; the Action card
        does that when it is chosen in an ActDecision.
        """
        return self.play_card(card).change(delta_actions=-1)

    def discard_card(self, card):
        """
        Discard a single card from the hand.
        """
        index = list(self.hand).index(card)
        newhand = self.hand[:index] + self.hand[index+1:]
        return PlayerState(
          self.player, newhand, self.drawpile, self.discard+(card,),
          self.tableau, self.actions, self.buys, self.coins
        )

    def trash_card(self, card):
        """
        Remove a card from the game.
        """
        index = list(self.hand).index(card)
        newhand = self.hand[:index] + self.hand[index+1:]
        return PlayerState(
          self.player, newhand, self.drawpile, self.discard,
          self.tableau, self.actions, self.buys, self.coins
        )

    def actionable(self):
        """Are there actions left to take with this hand?"""
        return (self.actions > 0 
                and any(c.isAction() for c in self.hand))

    def buyable(self):
        """Can this hand still buy a card?"""
        return self.buys > 0
    
    def next_decision(self):
        """
        Return the next decision that must be made. This will be either
        an ActDecision or a BuyDecision; other kinds of decisions only happen
        as a result of ActDecisions.
        """
        if self.actionable():
            return ActDecision
        elif self.buyable():
            return BuyDecision
        else: return None

    def score(self):
        """How many points is this deck worth?"""
        return sum(card.vp for card in self.all_cards())

    def simulate(self):
        return self.simulation_state()

    def simulate_from_here(self):
        newdraw = list(self.drawpile)
        random.shuffle(newdraw)
        return PlayerState(self.player, self.hand, tuple(newdraw),
                           self.discard, self.tableau, self.actions,
                           self.buys, self.coins)

    def simulation_state(self, cards=()):
        """
        Get a state with a freshly-shuffled deck, a new turn, and certain cards
        on top of the deck. Generally useful for simulating the effect of
        gaining a new card.
        """
        state = PlayerState(self.player, (), cards, self.all_cards(), (),
                            1, 1, 0)
        return state.draw(5)

    def simulate_hands(self, n=100, cards=()):
        """
        Simulate n hands with certain cards in them, yielding the number of
        coins and buys they end with.
        """
        for i in xrange(n):
            # make sure there are cards to gain, even though we haven't
            # kept track of the real game state
            game = Game([self.simulation_state(cards)],
                        {province: 12, duchy: 12, estate: 12,
                         copper: 12, silver: 12, gold: 12},
                        simulated=True
            )
            coins, buys = game.simulate_turn()
            yield coins, buys

# How many duchies/provinces are there for n players?
VICTORY_CARDS = {
    1: 5,  # useful for simulation
    2: 8,
    3: 12,
    4: 12,
    5: 15,
    6: 18
}

class Game(object):
    def __init__(self, playerstates, card_counts, turn=0, simulated=False):
        self.playerstates = playerstates
        self.card_counts = card_counts
        self.turn = turn
        self.player_turn = turn % len(playerstates)
        self.round = turn // len(playerstates)
        self.simulated = simulated
        logid = 'Game'
        if self.simulated:
            logid = 'Simulation'
        self.log = logging.getLogger(logid)
        if self.simulated:
            self.log.setLevel(logging.WARN)
        else:
            self.log.setLevel(logging.INFO)

    def copy(self):
        "Make an exact copy of this game state."
        return Game(self.playerstates[:], self.card_counts, self.turn,
                    self.simulated)

    @staticmethod
    def setup(players, var_cards=(), simulated=False):
        "Set up the game."
        counts = {
            estate: VICTORY_CARDS[len(players)],
            duchy: VICTORY_CARDS[len(players)],
            province: VICTORY_CARDS[len(players)],
            copper: 60 - 7*len(players),
            silver: 40,
            gold: 30
        }
        for card in var_cards:
            counts[card] = 10

        playerstates = [PlayerState.initial_state(p) for p in players]
        random.shuffle(playerstates)
        return Game(playerstates, counts, turn=0, simulated=simulated)


    def state(self):
        """
        Get the game's state for the current player. Most methods that
        do anything interesting need to do this.
        """
        return self.playerstates[self.player_turn]
    
    def current_play_card(self, card):
        """
        Play a card in the current state without decrementing the action count.
        Could be useful for Throne Rooms and such.
        """
        return self.replace_current_state(self.state().play_card(card))

    def current_play_action(self, card):
        """
        Remember, this is the one that decrements the action count.
        """
        return self.replace_current_state(self.state().play_action(card))

    def current_draw_cards(self, n):
        """
        The current player draws n cards.
        """
        return self.replace_current_state(self.state().draw(n))

    def current_player(self):
        return self.state().player

    def num_players(self):
        return len(self.playerstates)

    def card_choices(self):
        """
        List all the cards that can currently be bought.
        """
        choices = [card for card, count in self.card_counts.items()
                   if count > 0]
        choices.sort()
        return choices

    def remove_card(self, card):
        """
        Remove a single card from the table.
        """
        new_counts = self.card_counts.copy()
        new_counts[card] -= 1
        assert new_counts[card] >= 0
        return Game(self.playerstates[:], new_counts, self.player_turn, self.simulated)

    def replace_states(self, newstates):
        """
        Do something with the current player's state and make a new overall
        game state from it.
        """
        newgame = self.copy()
        newgame.playerstates = newstates
        return newgame
    
    def replace_current_state(self, newstate):
        """
        Do something with the current player's state and make a new overall
        game state from it.
        """
        newgame = self.copy()
        newgame.playerstates[self.player_turn] = newstate
        return newgame
    
    def change_current_state(self, **changes):
        """
        Make a numerical change to the current player's state, such as adding
        a buy or using up an action. The changes are expressed as deltas from
        the current state.
        """
        return self.replace_current_state(self.state().change(**changes))

    def change_other_states(self, **changes):
        """
        Make a numerical change to the states of all non-current players, the
        same way as change_current_state.
        """
        newgame = self.copy()
        for i in xrange(self.num_players()):
            if i == self.player_turn: continue
            newgame.playerstates[i] = newgame.playerstates[i].change(**changes)
        return newgame

    def transform_other_states(self, func, attack=False):
        """
        Apply a function to all other states, with no decisions to be made.

        This does not work for attacks, because other players might have a
        counter that requires them to make a decision. Implement attacks using
        the attack_with_decision method instead.
        """
        newgame = self.copy()
        for i in xrange(self.num_players()):
            if i == self.player_turn: continue
            newgame.playerstates[i] = func(newgame.playerstates[i])
        return newgame
    
    def next_mini_turn(self):
        """
        Temporarily increase the turn counter, without doing any of the usual
        end-of-turn mechanics. 
        
        This is useful when players need to make decisions in the middle of
        another player's turn, creating what we call here a "mini-turn".
        """
        return Game(self.playerstates[:], self.card_counts, self.turn+1,
                    self.simulated)

    def everyone_else_makes_a_decision(self, decision_template, attack=False):
        newgame = self.next_mini_turn()
        while newgame.player_turn != self.player_turn:
            if attack:
                if newgame.state().is_defended():
                    newgame = newgame.next_mini_turn()
                    continue
                reactions = newgame.state().get_reactions()
                for reaction in reactions:
                    newgame = reaction(newgame)
            decision = decision_template(newgame)
            turn = newgame.player_turn
            game2 = newgame.current_player().make_decision(decision)
            assert game2.player_turn == turn
            newgame = game2.next_mini_turn()
        return newgame

    def attack_with_decision(self, decision):
        return self.everyone_else_makes_a_decision(decision, attack=True)

    def run_decisions(self):
        """
        Run through all the decisions the current player has to make, and
        return the resulting state.
        """
        state = self.state()
        decisiontype = state.next_decision()
        if decisiontype is None: return self
        decision = decisiontype(self)
        newgame = self.current_player().make_decision(decision)
        return newgame.run_decisions()
    
    def simulated_copy(self):
        """
        Get a copy of this game, but with the `simulated` flag set to True
        and no information that the current player should not have. This
        prevents accidentally cheating when looking at the implications of
        various actions.
        """
        return Game(
            [state.simulated_from_here() if state is self.state()
                                         else state.simulate()
             for state in self.playerstates],
            self.card_counts,
            self.turn,
            simulated=True
        )
        
    def simulate_turn(self):
        """
        Run through all the decisions the current player has to make, and
        return the number of coins and buys they end up with. Useful for
        the BigMoney strategy.
        """
        if not self.simulated: self = self.simulated_copy()
        state = self.state()
        decisiontype = state.next_decision()
        if decisiontype is None:
            assert False, "BuyDecision never happened this turn"
        if decisiontype is BuyDecision:
            return (state.hand_value(), state.buys)
        decision = decisiontype(self)
        newgame = self.current_player().make_decision(decision)
        return newgame.simulate_turn()

    def simulate_partial_turn(self):
        """
        Run through all the decisions the current player has to make, and
        return the state where the player buys stuff.
        """
        if not self.simulated: self = self.simulated_copy()
        state = self.state()
        decisiontype = state.next_decision()
        if decisiontype is None:
            assert False, "BuyDecision never happened this turn"
        if decisiontype is BuyDecision:
            return state
        decision = decisiontype(self)
        newgame = self.current_player().make_decision(decision)
        return newgame.simulate_partial_turn()

    def take_turn(self):
        """
        Play an entire turn, including drawing cards at the end. Return
        the game state where it is the next player's turn.
        """
        self.log.info("")
        self.log.info("Round %d / player %d: %s" % (
          (self.round + 1),
          (self.player_turn+1), self.current_player().name
        ))

        self.log.info("%d provinces left" % self.card_counts[province])
        
        # Run AI hooks that need to happen before the turn.
        self.current_player().before_turn(self)
        endturn = self.run_decisions()

        next_turn = (self.turn + 1)

        newgame = Game(endturn.playerstates[:], endturn.card_counts,
                       next_turn, self.simulated)
        # mutate the new game object since nobody cares yet
        newgame.playerstates[self.player_turn] =\
          newgame.playerstates[self.player_turn].next_turn()

        # Run AI hooks that need to happen after the turn.
        self.current_player().after_turn(newgame)
        return newgame

    def over(self):
        "Returns True if the game is over."
        if self.card_counts[province] == 0: return True
        zeros = 0
        for count in self.card_counts.values():
            if count == 0: zeros += 1
        if self.num_players() > 4: return (zeros >= 4)
        else: return (zeros >= 3)

    def run(self):
        """
        Play a game of Dominion. Return a dictionary mapping players to scores.
        """
        game = self
        while not game.over():
            game = game.take_turn()
        scores = [(state.player, state.score()) for state in game.playerstates]
        self.log.info("End of game.")
        self.log.info("Scores: %s" % scores)
        return scores

    def __repr__(self):
        return 'Game%s[%s]' % (str(self.playerstates), str(self.turn))

class Decision(object):
    def __init__(self, game):
        self.game = game
    def state(self):
        return self.game.state()
    def player(self):
        return self.game.current_player()

class MultiDecision(Decision):
    def __init__(self, game, min=0, max=INF):
        self.min=min
        self.max=max
        Decision.__init__(self, game)

class ActDecision(Decision):
    def choices(self):
        return [None] + [card for card in self.state().hand if card.isAction()]
    def choose(self, card):
        self.game.log.info("%s plays %s" % (self.player().name, card))
        if card is None:
            newgame = self.game.change_current_state(
              delta_actions=-self.state().actions
            )
            return newgame
        else:
            newgame = card.perform_action(self.game.current_play_action(card))
            return newgame
    def __str__(self):
        return "ActDecision (%d actions, %d buys, +%d coins)" %\
          (self.state().actions, self.state().buys, self.state().coins)

class BuyDecision(Decision):
    def coins(self):
        return self.state().hand_value()
    def buys(self):
        return self.state().buys
    def choices(self):
        assert self.coins() >= 0
        value = self.coins()
        return [None] + [card for card in self.game.card_choices() if card.cost <= value]
    def choose(self, card):
        self.game.log.info("%s buys %s" % (self.player().name, card))
        state = self.state()
        if card is None:
            newgame = self.game.change_current_state(
              delta_buys=-state.buys
            )
            return newgame
        else:
            newgame = self.game.remove_card(card).replace_current_state(
              state.gain(card).change(delta_buys=-1, delta_coins=-card.cost)
            )
            return newgame
    
    def __str__(self):
        return "BuyDecision (%d buys, %d coins)" %\
          (self.buys(), self.coins())

class TrashDecision(MultiDecision):
    def choices(self):
        return sorted(list(self.state().hand))

    def choose(self, choices):
        self.game.log.info("%s trashes %s" % (self.player().name, choices))
        state = self.state()
        for card in choices:
            state = state.trash_card(card)
        return self.game.replace_current_state(state)

    def __str__(self):
        return "TrashDecision(%s, %s, %s)" % (self.state().hand, self.min, self.max)

class DiscardDecision(MultiDecision):
    def choices(self):
        return sorted(list(self.state().hand))
    
    def choose(self, choices):
        self.game.log.info("%s discards %s" % (self.player().name, choices))
        state = self.state()
        for card in choices:
            state = state.discard_card(card)
        return self.game.replace_current_state(state)
    
    def __str__(self):
        return "DiscardDecision" + str(self.state().hand)

