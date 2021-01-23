from constants import *

import sys
sys.path.insert(0, PREFIX + '/python-daemon')

from daemon import Daemon
from make_table import *
from make_tournament_page import *
from models import *
import time
import os
import os.path
import pickle
import subprocess
import traceback
import random

bots = []

def checkBotDirAndGetObj(ent):
  path = BOTSDIR + ent
  if not os.path.isdir(path): return None
  subents = os.listdir(path)
  if not 'author' in subents: return None
  if not 'bot' in subents: return None
  # TODO: Possibly run some checks on bot before adding to pool
  author_path = path + '/author'
  with open(author_path, 'r') as f:
    author = f.read(32)
  obj_path = BOTSDIR + ent + '/player.pkl'
  try:
    obj = Player.loadFromPkl(ent)
    if obj is None: obj = Player(ent, author)
    else: obj.author = author
  except:
    obj = Player(ent, author)
    obj.saveToPkl()
  assert obj.name == ent
  return obj


def loadBots():
  global bots
  ents = os.listdir(BOTSDIR)
  print >>sys.stderr, "Found bots: %s" % str(ents)
  bots = []
  for ent in ents:
    obj = checkBotDirAndGetObj(ent)
    assert obj is not None, "Failed to find bot %s" % ent
    bots.append(obj)
  print >>sys.stderr, "Updated bots: %s" % str(bots)
  sys.stderr.flush()

def runTournament(t):
  global bots
  if len(bots) < 3: # cannot start match
    print >>sys.stderr, "Cannot run tournament: too few bots"
    return
  # randomly establish an N_ROUNDS format with loaded bots
  print >>sys.stderr, "Creating tournamnent %d" % t
  tourn = Tournament(t, bots)
  print >>sys.stderr, "Running tournament %d" % t
  tourn.run()
  print >>sys.stderr, "Done with tournament %d." % t
  
  # Update bot ratings in place
  tourn.evalMultiplayerElo()
  tourn.saveToPkl()
  for p in tourn.players: p.saveToPkl()
  # Make tournament leaderboard page
  makeTournamentPage(tourn)
  # Update main page
  makeMainPage()

# def updateLeaderboard():
#   print >>sys.stderr, "Updating leaderboard with bots: %s" % bots
#   sys.stderr.flush()
#   with open(LEADERBOARD, 'w') as f:
#     f.write(makeTable(bots))

HOUR = 3600
def round_to_next_hour(t):
  t = t - t%HOUR
  t += HOUR
  return t

class PokerServer(Daemon):
  def run(self):
    with open(LOGFILE, 'w') as serv_logfd:
      sys.stderr = serv_logfd
      try:
        next_tournament = round_to_next_hour(time.time())
        # Run one tourney to begin
        loadBots()
        runTournament(123456)
        while True:
          loadBots()
          if time.time() > next_tournament:
            runTournament(next_tournament)
            next_tournament += HOUR
          # updateLeaderboard()
          time.sleep(60)
      except Exception as e:
        traceback.print_exc()
        sys.stderr.flush()
        raise


def usage(name):
    print >>sys.stderr, "Usage: %s (start|stop|restart)" % name


if __name__ == "__main__":
  if len(sys.argv) > 1:
    cmd = sys.argv[1]
    if cmd not in ("start", "stop", "restart"):
      usage(sys.argv[0])
    else:
      server = PokerServer(PIDFILE)
      if cmd == "start":
        server.start()
      elif cmd == "stop":
        server.stop()
      elif cmd == "restart":
        server.restart()
      else: assert False
  else:
    usage(sys.argv[0])
