from schafkopfrl.players.player import Player
from schafkopfrl.rules import Rules
import random


class RuleBasedPlayer(Player):

  def __init__(self):
    super().__init__()

  def act(self, state):
    allowed_actions, gamestate, player_cards = state["allowed_actions"], state["game_state"], state["current_player_cards"]

    if gamestate.game_stage == Rules.BIDDING:
      return self.call_game_type(player_cards, allowed_actions)
    elif gamestate.game_stage == Rules.CONTRA or gamestate.game_stage == Rules.RETOUR:
      return self.contra_retour(player_cards, allowed_actions)
    else:
      return self.select_card(gamestate, player_cards, allowed_actions)

  def call_game_type(self, player_cards, allowed_games):
    '''
    Calls a game according to the following rules:
    - if in some solo more then 7 trumps then play the solo
    - if at least 2 unter and for all colors in hand the ace is also in hand then play wenz
    - if 4 or more trumps then play a sauspiel on the color with the fewest other cards of that color
    - otherwise weiter

    :param game_state: the current game state
    :type game_state: game_state
    :return: the game to play
    :rtype: list
    '''


    # solo heuristic
    for solo in [[0, 2], [1, 2], [2, 2], [3, 2]]:
      trump_count = 0
      for card in self.rules.get_sorted_trumps(solo):
        if card in player_cards:
          trump_count+= 1
      if trump_count >= 7:
        return solo, 1

    # wenz heurisitc
    wenz_count = len([card for card in [[0, 3], [1, 3], [2, 3], [3, 3]] if card in player_cards])
    spazen_count = 0
    if wenz_count >= 2:
      for color in range(4):
        if [color, 7] in player_cards:
          continue
        for number in range(7):
          if number == 3:
            continue
          if [color, number] in player_cards:
            spazen_count += 1
      if spazen_count < 2:
        return [None, 1], 1

    # sauspiel heuristic
    trumps = [card for card in self.rules.get_sorted_trumps([0,0]) if card in player_cards]
    if len(trumps) >= 4:
      non_trump_cards = [card for card in player_cards if card not in trumps]
      allowed_saupiele = [game for game in allowed_games if game in [[0, 0], [2, 0], [3, 0]]]

      best_color = -1
      best_color_count = 10
      if len(allowed_saupiele) > 0:
        for [color, _] in allowed_saupiele:
          color_count = len([[color,_] for [color,_] in  non_trump_cards])
          if color_count < best_color_count:
            best_color = color
        return [best_color, 0], 1

    return [None, None], 1

  def contra_retour(self, player_cards, allowed_double):
    trumps = [card for card in self.rules.get_sorted_trumps([0, 0]) if card in player_cards]
    if len(trumps) >= 6 and (True in allowed_double):
      return True, 1
    else:
      return False, 1

  def select_card(self, game_state, player_cards, allowed_cards):

    selected_card = random.choice(allowed_cards)

    #precompute some interesting features
    if game_state.game_stage == Rules.TRICK and len(player_cards) == 8:
      if game_state.game_player == game_state.current_player or (game_state.game_type in [[0, 0], [2, 0], [3, 0]] and [game_state.game_type[0],7] in player_cards):
        self.spieler_or_mitspieler = True
      else:
        self.spieler_or_mitspieler = False

    played_cards_in_trick = game_state.played_cards % 4
    trump_cards = [trump for trump in self.rules.get_sorted_trumps(game_state.game_type) if trump in allowed_cards]
    color_aces = [ace for ace in allowed_cards if ace in [[0, 7], [1, 7], [2, 7], [3, 7]]]
    #played colors does not include current trick
    played_colors = {c for [c, n] in [trick[0] for trick in game_state.course_of_game if trick[3] != [None, None]] if n not in [3, 4]}
    first_card_in_trick = game_state.course_of_game[game_state.trick_number][0]


    if game_state.game_type in [[0, 0], [2, 0], [3, 0]]: #Sauspiel
      if [1, 7] in color_aces:
        color_aces.remove([1, 7])
      if [game_state.game_type[0], 7]  in color_aces: #Suchsau
        color_aces.remove([game_state.game_type[0], 7])
      if played_cards_in_trick == 0:
        if self.spieler_or_mitspieler:
          # play highest or lowest trump if possible
          if len(trump_cards) > 0:
            idx = random.choice([0, -1])
            selected_card = trump_cards[idx]
          #otherwise play an ace
          elif len(color_aces) > 0:
            selected_card = random.choice(color_aces)
        else:
          # play Suchcolor if not already searched
          such_color_cards = [card for card in allowed_cards if card[0] == game_state.game_type[0] and card[1] not in [3, 4]]
          if game_state.game_type[0] not in played_colors and len(such_color_cards)>0:
            if len(such_color_cards)>3 and [game_state.game_type[0], 6] in such_color_cards:
              selected_card = [game_state.game_type[0], 6]
            else:
              selected_card = random.choice(such_color_cards)
          # play an ace if possible
          elif len(color_aces) > 0:
            selected_card = random.choice(color_aces)
          # otherwise play color
          else:
            color_cards = [card for card in allowed_cards if card not in trump_cards]
            if len(color_cards) > 0:
              selected_card = random.choice(color_cards)
      else: #not first trick player
        # color played and player is free then play trump
        if first_card_in_trick not in self.rules.get_sorted_trumps(game_state.game_type):
          if len(trump_cards) > 0:
            if first_card_in_trick[0] not in played_colors:
              if [1,7] in trump_cards:
                selected_card = [1,7]
              elif [1,6] in trump_cards:
                selected_card = [1, 6]
              else:
                selected_card = trump_cards[0]
            else:
              selected_card = trump_cards[-1]
        #play ace if you have it and color has not already been played
        elif first_card_in_trick[0] not in played_colors and [first_card_in_trick[0], 7] in allowed_cards:
          selected_card = [first_card_in_trick[0], 7]


    elif game_state.game_type in [[0, 2], [1, 2], [2, 2], [3, 2]]: #Solo
      if [game_state.game_type[0], 7] in color_aces:
        color_aces.remove([game_state.game_type[0], 7])

      if self.spieler_or_mitspieler:
        if played_cards_in_trick == 0:
          if len(trump_cards) > 0:
            selected_card = trump_cards[-1]
          elif len(color_aces) > 0:
            selected_card = random.choice(color_aces)
        else: # not first trick player
          # color played and player is free then play trump
          if first_card_in_trick not in self.rules.get_sorted_trumps(game_state.game_type):
            if len(trump_cards) > 0:
              if first_card_in_trick[0] not in played_colors:
                if [game_state.game_type[0],7] in trump_cards:
                  selected_card = [game_state.game_type[0],7]
                elif [game_state.game_type[0],6] in trump_cards:
                  selected_card = [game_state.game_type[0], 6]
                else:
                  selected_card = trump_cards[0]
              else:
                selected_card = trump_cards[-1]
          elif [first_card_in_trick[0], 7] in allowed_cards:
            selected_card = [first_card_in_trick[0], 7]
      else: #not solo player
        pass

    else: # Wenz
      unter = [card for card in [[3, 3], [2, 3], [1, 3], [0, 3]] if card in allowed_cards]
      sorted_color_cards = [[0, 7], [0, 6], [0, 5], [0, 4], [0, 2], [0, 1], [0, 0], # eichel
                      [1, 7], [1, 6], [1, 5], [1, 4], [1, 2], [1, 1], [1, 0],  # gras
                      [2, 7], [2, 6], [2, 5], [2, 4], [2, 2], [2, 1], [2, 0],  # herz
                      [3, 7], [3, 6], [3, 5], [3, 4], [3, 2], [3, 1], [3, 0]]  # schelle
      sorted_cards = [card for card in sorted_color_cards if card in allowed_cards]
      if self.spieler_or_mitspieler:
        if played_cards_in_trick == 0:
          if len(unter) > 0:
            selected_card = unter[0]
          else:
            selected_card = sorted_cards[0]
        else:
          if len(unter) > 0:
            selected_card = unter[-1]
          else: #TODO: this could be improved by selecting a low card if you cannot take the trick
            selected_card = sorted_cards[-1]
      else:
        pass

    return selected_card, 1


