"""
Classic cart-pole system implemented by Rich Sutton et al.
Copied from https://webdocs.cs.ualberta.ca/~sutton/book/code/pole.c
"""

import gym
from gym import spaces
import numpy as np
from gym import error


def random_policy(state):
    possible_moves = HexEnv.get_possible_moves(state)
    a = np.random.randint(len(possible_moves))
    return HexEnv.coordinate_to_action(state.shape[1], possible_moves[a])


class HexEnv(gym.Env):
    """
    Hex environment. Play against a fixed opponent.
    """
    BLACK = 0
    WHITE = 1
    metadata = {"render.modes": ["ansi"]}

    def __init__(self, player_color, opponent, observation_type, illegal_move_mode, board_size):
        """
        Args:
            player_color: Stone color for the agent. Either 'black' or 'white'
            opponent: An opponent policy
            observation_type: State encoding
            illegal_move_mode: What to do when the agent makes an illegal move. Choices: 'raise' or 'lose'
            board_size: size of the Hex board
        """
        assert isinstance(board_size, int) and board_size >= 1, 'Invalid board size: {}'.format(board_size)
        self.board_size = board_size

        colormap = {
            'black': HexEnv.BLACK,
            'white': HexEnv.WHITE,
        }
        try:
            self.player_color = colormap[player_color]
        except KeyError:
            raise error.Error("player_color must be 'black' or 'white', not {}".format(player_color))

        self.opponent = opponent or 'random'
        self.opponent_policy = None

        assert observation_type in ['numpy3c']
        self.observation_type = observation_type

        assert illegal_move_mode in ['lose', 'raise']
        self.illegal_move_mode = illegal_move_mode

        # One action for each board position, pass, and resign
        self.action_space = spaces.Discrete(self.board_size ** 2 + 2)

        if self.observation_type != 'numpy3c':
            raise error.Error('Unsupported observation type: {}'.format(self.observation_type))

        self.reset()

    def _reset(self):
        self.state = np.zeros((3, self.board_size, self.board_size))
        self.state[2, :, :] = 1.0
        self.to_play = HexEnv.BLACK
        self.done = False

        # Let the opponent play if it's not the agent's turn
        if self.player_color != self.to_play:
            a = self.opponent_policy(self.state)
            HexEnv.make_move(self.state, a, HexEnv.BLACK)
            self.to_play = HexEnv.WHITE
        return self.state

    def _step(self, action):
        assert self.to_play == self.player_color
        # If already terminal, then don't do anything
        if self.done:
            return self.state, 0., True, {'state': self.state}

        if not HexEnv.valid_move(self.state, action):
            if self.illegal_move_mode == 'raise':
                raise
            elif self.illegal_move_mode == 'lose':
                # Automatic loss on illegal move
                self.done = True
                return self.state, -1., True, {'state': self.state}
            else:
                raise error.Error('Unsupported illegal move action: {}'.format(self.illegal_move_mode))

        HexEnv.make_move(self.state, action, self.player_color)

        # Opponent play
        a = self.opponent_policy(self.state)
        HexEnv.make_move(self.state, a, 1 - self.player_color)

        reward = HexEnv.game_finished(self.state)
        if self.player_color == HexEnv.WHITE:
            reward = - reward
        self.done = reward == 0
        return self.state, reward, self.done, {'state': self.state}

    def _reset_opponent(self):
        if self.opponent == 'random':
            self.opponent_policy = random_policy
        else:
            raise error.Error('Unrecognized opponent policy {}'.format(self.opponent))

    def _render(self, mode='asi', close=False):
        board = self.state
        print(" " * 6, end="")
        for j in range(board.shape[1]):
            print(" ", j + 1, " ", end="")
            print("|", end="")
        print("")
        print(" " * 5, end="")
        print("-" * (board.shape[1] * (board.shape[1] + 1) + 1), end="")
        print("")
        for i in range(board.shape[1]):
            print(" " * (1 + i * 3), i + 1, " ", end="")
            print("|", end="")
            for j in range(board.shape[1]):
                if board[2, i, j] == 1:
                    print("  O  ", end="")
                elif board[0, i, j] == 1:
                    print("  B  ", end="")
                else:
                    print("  W  ", end="")
                print("|", end="")
            print("")
            print(" " * (i * 3 + 1), end="")
            print("-" * (board.shape[1] * (board.shape[1] + 2)), end="")
            print("")

    @staticmethod
    def valid_move(board, action):
        coords = HexEnv.action_to_coordinate(board, action)
        if board[2, coords[0], coords[1]] == 1:
            return True
        else:
            return False

    @staticmethod
    def make_move(board, action, player):
        coords = HexEnv.action_to_coordinate(board, action)
        board[2, coords[0], coords[1]] = 0
        board[player, coords[0], coords[1]] = 1

    @staticmethod
    def coordinate_to_action(board, coords):
        return coords[0] * board.shape[-1] + coords[1]

    @staticmethod
    def action_to_coordinate(board, action):
        return action // board.shape[-1], action % board.shape[-1]

    @staticmethod
    def get_possible_actions(board):
        free_x, free_y = np.where(board[2, :, :] == 1)
        return [HexEnv.coordinate_to_action(board, [x, y]) for x, y in zip(free_x, free_y)]

    @staticmethod
    def game_finished(board):
        # Returns 1 if player 1 wins, -1 if player 2 wins and 0 otherwise
        d = board.shape[1]

        inpath = set()
        newset = set()
        for i in range(d):
            if board[0, 0, i] == 1:
                newset.add(i)

        while len(newset) > 0:
            for i in range(len(newset)):
                v = newset.pop()
                inpath.add(v)
                cx = v // d
                cy = v % d
                # Left
                if cy > 0 and board[0, cx, cy - 1] == 1:
                    v = cx * d + cy - 1
                    if v not in inpath:
                        newset.add(v)
                # Right
                if cy + 1 < d and board[0, cx, cy + 1] == 1:
                    v = cx * d + cy + 1
                    if v not in inpath:
                        newset.add(v)
                # Up
                if cx > 0 and board[0, cx - 1, cy] == 1:
                    v = (cx - 1) * d + cy
                    if v not in inpath:
                        newset.add(v)
                # Down
                if cx + 1 < d and board[0, cx + 1, cy] == 1:
                    if cx + 1 == d - 1:
                        return 1
                    v = (cx + 1) * d + cy
                    if v not in inpath:
                        newset.add(v)
                # Up Right
                if cx > 0 and cy + 1 < d and board[0, cx - 1, cy + 1] == 1:
                    v = (cx - 1) * d + cy + 1
                    if v not in inpath:
                        newset.add(v)
                # Down Left
                if cx + 1 < d and cy > 0 and board[0, cx + 1, cy - 1] == 1:
                    if cx + 1 == d - 1:
                        return 1
                    v = (cx + 1) * d + cy - 1
                    if v not in inpath:
                        newset.add(v)

        inpath.clear()
        newset.clear()
        for i in range(d):
            if board[1, i, 0] == 1:
                newset.add(i)

        while len(newset) > 0:
            for i in range(len(newset)):
                v = newset.pop()
                inpath.add(v)
                cy = v // d
                cx = v % d
                # Left
                if cy > 0 and board[1, cx, cy - 1] == 1:
                    v = (cy - 1) * d + cx
                    if v not in inpath:
                        newset.add(v)
                # Right
                if cy + 1 < d and board[1, cx, cy + 1] == 1:
                    if cy + 1 == d - 1:
                        return -1
                    v = (cy + 1) * d + cx
                    if v not in inpath:
                        newset.add(v)
                # Up
                if cx > 0 and board[1, cx - 1, cy] == 1:
                    v = cy * d + cx - 1
                    if v not in inpath:
                        newset.add(v)
                # Down
                if cx + 1 < d and board[1, cx + 1, cy] == 1:
                    v = cy * d + cx + 1
                    if v not in inpath:
                        newset.add(v)
                # Up Right
                if cx > 0 and cy + 1 < d and board[1, cx - 1, cy + 1] == 1:
                    if cy + 1 == d - 1:
                        return -1
                    v = (cy + 1) * d + cx - 1
                    if v not in inpath:
                        newset.add(v)
                # Left Down
                if cx + 1 < d and cy > 0 and board[1, cx + 1, cy - 1] == 1:
                    v = (cy - 1) * d + cx + 1
                    if v not in inpath:
                        newset.add(v)
        return 0