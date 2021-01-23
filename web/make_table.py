import time

def tableHeader():
  return '<table class="leaderboard">\n'
def tableFooter():
  return '</table>\n'
def pageFooter():
  return '<p>Last updated: %s.</p>\n' % time.asctime()
def tableTableHeading():
  return """<tr>
<th> Bot Name </th>
<th> Author </th>
<th> Score </th>
</tr>"""
def tournTableHeading():
  return """<tr>
<th> Bot Name </th>
<th> Author </th>
<th> Elo (Update) </th>
</tr>"""
def tableTableRow(p, score):
  return """<tr>
<td>%s</td>
<td>%s</td>
<td>%f</td>
</tr>""" % (p.name, p.author, score)
def tournTableRow(p, old_elo, new_elo):
  return """<tr>
<td>%s</td>
<td>%s</td>
<td>%d (%+d)</td>
</tr>""" % (p.name, p.author, new_elo, (new_elo-old_elo))

def makeTableTable(table):
  out = ""
  out += tableHeader()
  out += tableTableHeading()
  for i in xrange(len(table.ordered_players)):
    p = table.ordered_players[i]
    score = table.scores[i]
    out += tableTableRow(p, score)
  out += tableFooter()
  return out

def makeTournTable(tourn):
  out = ""
  out += tableHeader()
  out += tournTableHeading()
  inds = sorted(range(len(tourn.players)),
                reverse=True, key=lambda i: tourn.players[i].elo)
  for i in inds:
    p = tourn.players[i]
    old_elo = tourn.old_elos[i]
    new_elo = tourn.new_elos[i]
    out += tournTableRow(p, old_elo, new_elo)
  out += tableFooter()
  return out
