from constants import *
from math import exp
import os
import os.path
import pickle
from random import shuffle
import subprocess
import sys

# Very simple multiple Elo system: the ordered list of players
# with best first results in a set of (n choose 2) pairings of
# win-loss records, which are just updated with simple 2-player Elo.
def multiplayerElo(ordered_players):
  print >>sys.stderr, "Multiplayer elo on order %s" \
      % str([p.elo for p in ordered_players])
  # Do updates in batch
  updates = [0]*len(ordered_players)
  for i in xrange(len(ordered_players)):
    for j in xrange(i+1, len(ordered_players)):
      # p1 = winner, p2 = loser
      p1 = ordered_players[i]
      p2 = ordered_players[j]
      q1 = exp(p1.elo * ELO_POWER)
      q2 = exp(p2.elo * ELO_POWER)
      print >>sys.stderr, "Pairing %d %d: %f %f" % (p1.elo, p2.elo, q1, q2)
      # expected win value for p1, p2
      # sum to 1 and reflect the zero-rating transfer expectation
      e1 = q1 / (q1 + q2)
      e2 = q2 / (q1 + q2)
      transfer = int(ELO_K*(1-e1))
      print >>sys.stderr, "... transfer %d" % transfer
      updates[i] += transfer
      updates[j] -= transfer
  print >>sys.stderr, "Updates =", updates
  for i,up in enumerate(updates):
    ordered_players[i].elo += up

class Player():
  def __init__(self, name, author):
    self.name = name
    self.author = author
    self.elo = START_ELO

  def getBotExe(self):
    return BOTSDIR + self.name + '/bot'

  def saveToPkl(self):
    pklname = BOTSDIR + '/%s/player.pkl' % self.name
    with open(pklname, 'w') as f:
      pickle.dump(self, f)

  def __str__(self):
    return "%s (by %s) [Elo=%d]" % (self.name, self.author, self.elo)
  __repr__ = __str__

  @staticmethod
  def loadFromPkl(name):
    pklname = BOTSDIR + '/%s/player.pkl' % name
    if not os.path.isfile(pklname): return None
    try:
      with open(pklname, 'r') as f:
        player = pickle.load(f)
        assert isinstance(player, Player)
        return player
    except:
      print >>sys.stderr, "Failed to load %s" % pklname
      return None

def argsort(seq, **kwargs):
  return sorted(range(len(seq)), key=seq.__getitem__, **kwargs)

def maybeMkdir(dirname):
  if not os.path.isdir(dirname):
    os.mkdir(dirname)
  os.chmod(dirname, 0775)

def parseGameserverStdout(stdout_filename):
  hands = []
  moneyTag = 'Money: '
  scoresTag = 'Scores: '
  with open(stdout_filename, 'r') as stdout_fd:
    for line in stdout_fd:
      if line[:len(moneyTag)] == moneyTag:
        money = map(int, line[len(moneyTag):].split(','))
        hands.append(money)
      if line[:len(scoresTag)] == scoresTag:
        scores = map(float, line[len(scoresTag):].split(','))
        return hands,scores

class Table():
  def __init__(self, ps, parent_dir, round_id, table_id):
    assert(len(ps) == TABLE_SIZE), "Table only got %d players" % len(ps)
    for p in ps: assert(isinstance(p, Player))
    self.ps = ps
    self.old_elos = [0]*len(ps)
    self.ordered_players = [None]*len(ps)
    self.scores = [0.0]*TABLE_SIZE
    self.hands = [] # list of money after each hand
    self.parent_dir = parent_dir
    self.round_id = round_id # 1-indexed
    self.table_id = table_id # 1-indexed
    
  def rankPlayers(self):
    inds = argsort(self.scores, reverse=True)
    self.ordered_players = [self.ps[i] for i in inds]
    self.scores = [self.scores[i] for i in inds]

  def evalMultiplayerElo(self):
    self.old_elos = [p.elo for p in self.ordered_players]
    multiplayerElo(self.ordered_players)
    self.new_elos = [p.elo for p in self.ordered_players]

  def getDirName(self):
    return self.parent_dir + '/round%d/table%d/' % (self.round_id, self.table_id)

  def run(self):
    dirname = self.getDirName()
    print >>sys.stderr, "Running table in dir %s" % dirname
    maybeMkdir(dirname)
    print >>sys.stderr, "Created table dir %s" % dirname
    stdout_filename = dirname + '/gameserver.stdout'
    stderr_filename = dirname + '/gameserver.stderr'
    stdout_fd = open(stdout_filename, 'w')
    stderr_fd = open(stderr_filename, 'w')
    cmd = ['python', GAMESERVER]
    for p in self.ps:
      cmd.append(p.getBotExe())
    print >>sys.stderr, "Running tournament with cmd %s" % cmd
    print >>sys.stderr, "Logging tournament to %s" % stdout_filename
    p = subprocess.Popen(cmd, cwd=dirname, stdout=stdout_fd, stderr=stderr_fd)
    p.wait()
    stdout_fd.close()
    stderr_fd.close()
    # Gzip the all_messages.log file to keep things tight
    os.system('gzip -f %s/all_messages.log' % dirname)
    self.hands,self.scores = parseGameserverStdout(stdout_filename)
    print >>sys.stderr, "Retrieved scores %s" % str(self.scores)
    sys.stderr.flush()
    self.rankPlayers()
    print >>sys.stderr, "Rankings: %s" % str(self.ordered_players)

class Round():
  def __init__(self, tables, byes):
    self.tables = tables
    self.byes = byes

  def evalMultiplayerElo(self):
    for t in self.tables:
      t.evalMultiplayerElo()

  def run(self):
    print >>sys.stderr, "Running round..."
    for t in self.tables:
      print >>sys.stderr, "Running table %d" % (t.table_id)
      t.run()

class Tournament():
  @staticmethod
  def makeRounds(players, parent_dir):
    n_tables = len(players) // TABLE_SIZE
    n_bye = len(players) % TABLE_SIZE
    print >>sys.stderr, "makeRounds with %d players = %d tables, %d byes" \
        % (len(players), n_tables, n_bye)
    rounds = []
    for i in xrange(N_ROUNDS):
      round_order = players[:]
      shuffle(round_order)
      tables = [Table(round_order[j-TABLE_SIZE:j], parent_dir, i+1, j // TABLE_SIZE)
                for j in range(TABLE_SIZE, len(round_order)+1, TABLE_SIZE)]
      rounds.append(Round(tables, round_order[-n_bye:]))
    print >>sys.stderr, "Made rounds:", rounds
    return rounds

  def __init__(self, t, players):
    self.t = t
    # Original player order
    self.players = players
    self.old_elos = [p.elo for p in players]
    self.new_elos = [0]*len(players)
    # List of rounds, FORNOW randomly assign players to tables
    self.rounds = Tournament.makeRounds(players, self.getDirName())
    # Ensure directory structure exists
    maybeMkdir(self.getDirName())
    for i in xrange(len(self.rounds)):
      maybeMkdir(self.getDirName() + '/round%d/' % (i+1))

  def evalMultiplayerElo(self):
    for r in self.rounds:
      r.evalMultiplayerElo()
    self.new_elos = [p.elo for p in self.players]

  def run(self):
    for r in self.rounds:
      r.run()

  def getDirName(self):
    return TOURNSDIR + '/%d/' % self.t

  def saveToPkl(self):
    pklname = TOURNSDIR + '/%d/tournament.pkl' % self.t
    with open(pklname, 'w') as f:
      pickle.dump(self, f)

  @staticmethod
  def loadFromPkl(t):
    pklname = TOURNSDIR + '/%d/tournament.pkl' % t 
    if not os.path.isfile(pklname): return None
    try:
      with open(pklname, 'r') as f:
        tourn = pickle.load(f)
        assert isinstance(tourn, Tournament)
        return tourn
    except:
      print >>sys.stderr, "Failed to load %s" % pklname
      return None
