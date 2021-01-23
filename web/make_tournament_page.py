import sys
import time
import os
from constants import *
from make_table import *
from models import *

def playerDataJS(players, money, round_id, table_id):
  out = "function load_%d_%d() {" % (round_id, table_id)
  series = [[] for i in xrange(len(players))]
  for m in money:
    for i in xrange(len(players)):
      series[i].append(m[i])
  varNames = []
  for i,s in enumerate(series):
    varNames.append("player%d" % i)
    out += "var %s = {\n" % varNames[-1]
    out += "  x: %s,\n" % str(range(1,len(s)+1))
    out += "  y: %s,\n" % str(s)
    out += "  name: '%s'\n" % players[i].name
    out += "};\n"
  out += "return [%s];\n" % ",".join(varNames)
  out += "}\n"
  return out

def getTableLinks(t, table):
  out = ""
  out += '<h4>Table %d:</h4>\n<div class="table-links"><ul>\n' % (table.table_id)
  out += '<li><a href="?t=%d&rid=%d&tid=%d&req=stdout">stdout</a></li>\n' \
      % (t, table.round_id, table.table_id)
  out += '<li><a href="/tournaments/%d/round%d/table%d/all_messages.log.gz" download>all_messages.log.gz</a></li>\n' \
      % (t, table.round_id, table.table_id)
  for i,p in enumerate(table.ps):
    out += '<li><a href="?t=%d&rid=%d&tid=%d&req=player%d">[%d] %s stderr</a></li>\n' \
        % (t, table.round_id, table.table_id, i, i, p.name)
  out += '</ul></div>\n'
  out += '<div class="money-plot" data-src="load_%d_%d()"></div>\n' \
      % (table.round_id, table.table_id)
  out += '<script type="text/javascript">\n' \
      + playerDataJS(table.ps, table.hands, table.round_id, table.table_id) \
      + '</script>\n'
  return out

def makeTournamentPage(tourn):
  dirname = tourn.getDirName()
  if not os.path.isdir(dirname): return
  filename = dirname + '/leaderboard.html'
  with open(filename, 'w') as f:
    f.write("<h3>Tournament: %s</h3>\n" % time.ctime(tourn.t))
    f.write(makeTournTable(tourn))
    for i,r in enumerate(tourn.rounds):
      f.write("<hr>\n")
      f.write("<h3>Round %d / %d\n" % (i+1, len(tourn.rounds)))
      for table in r.tables:
        f.write(getTableLinks(tourn.t, table))
    f.write(pageFooter())
  os.chmod(filename, 0644)

def makeMainPage():
  if not os.path.isdir(TOURNSDIR): return
  ts = sorted(map(int, os.listdir(TOURNSDIR)), reverse=True) # should only be int-named dirs!
  print >>sys.stderr, "Making main page with ts:", ts
  latest = ts[0]
  with open(LEADERBOARD, 'w') as f:
    f.write("<h3>Latest (%s):</h3>\n" % time.ctime(latest))
    f.write(makeTournTable(Tournament.loadFromPkl(latest)))
    f.write("<h3>All Tournaments:</h3>\n")
    for t in ts:
      f.write("<a href='?t=%d'>%s</a><br/>\n" % (t, time.ctime(t)))
    f.write(pageFooter())
  os.chmod(LEADERBOARD, 0644)

if __name__ == "__main__":
  t = int(sys.argv[1])
  makeTournamentPage(Tournament.loadFromPkl(t))
