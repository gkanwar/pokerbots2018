from math import log

PREFIX = '/pokerbots/'
PIDFILE = PREFIX + '/poker_serv.pid'
LOGFILE = PREFIX + '/poker_serv.log'
BOTSDIR = PREFIX + '/allbots/'
TOURNSDIR = PREFIX + '/tournaments/'
LEADERBOARD = PREFIX + '/leaderboard.html'
CODEDIR = PREFIX + '/pokerbots2018/src/'
GAMESERVER = CODEDIR + '/gameserver.py'

# Elo System
START_ELO = 1000
ELO_POWER = log(10)/400
ELO_K = 32

# Tournament format
N_ROUNDS = 10
TABLE_SIZE = 3
