from subprocess import *
from random import *
from signal import *
from math import sqrt
import sys
import traceback

BLINDS = [1,1,1]
ENDPROB_AB = (1,1000)
ENDPROB = float(ENDPROB_AB[0]) / float(ENDPROB_AB[1])
CARD_NAMES = ['J', 'Q', 'K', 'A']
CARDS = [0,1,2,3]
NPLAYERS = 3
MAX_BET_ACTIONS = 10 # Just a safety check that we don't loop forever

MAX_BET = 2 # Kuhn Poker
MAX_RAISE = None # No max on raise, just absolute value of bet

# Log a subprocess stdin/stdout channel
class LoggedFDs():
    def __init__(self, stdin, stdout, pid, logfd):
        self.stdin = stdin
        self.stdout = stdout
        self.logfd = logfd
        self.pid = pid
    def __getattr__(self, attr):
        if attr == 'write':
            return self.write
        elif attr == 'readline':
            return self.readline
        elif attr == 'flush':
            return self.stdin.flush
        else:
            assert False
    def readline(self, *args, **kwargs):
        out = self.stdout.readline(*args, **kwargs)
        self.logfd.write("P%d -> S: %s" % (self.pid, out))
        return out
    def write(self, *args, **kwargs):
        self.logfd.write("S -> P%d: " % (self.pid))
        self.logfd.write(*args, **kwargs)
        return self.stdin.write(*args, **kwargs)

# Shortcut for n-second alarm
# Usage: with alarmCtxt(<n seconds>): <stuff>
class alarmCtxt():
    def __init__(self, n):
        self.n = n
    def __enter__(self):
        alarm(self.n)
    def __exit__(self, exc_type, exc_value, tb):
        alarm(0)
        # Print any traceback to stderr, then unset alarm
        if tb is not None:
            # traceback.print_tb(tb)
            return False # Kick up the exception
        return True # No exception

# Mod NPLAYERS shortcut
def m(i): return i % NPLAYERS

def button_from_first_blind(first_blind):
    return m(first_blind - 1)

# Walk backwards from the raiser and try to find a live player
# to give the option to.
def find_last_option(pi, statuses):
    for i in xrange(1, len(statuses)):
        act,val = statuses[m(pi-i)]
        if act in ('BET', 'BLIND'):
            return m(pi - i)
    return None

def with_prob(p):
    return random() < p

def comma_str(vals):
    return ",".join(map(str, vals))

def send_init_round(first_blind):
    button = button_from_first_blind(first_blind)
    for i,p in enumerate(ps):
        local_money = money[i:] + money[:i]
        p.stdin.write("init_round\n")
        p.stdin.write("Money: " + comma_str(local_money) + "\n")
        p.stdin.write("Blinds: " +  comma_str(BLINDS) + "\n")
        p.stdin.write("Button: " + str(m(button-i)) + "\n")
        p.stdin.write("EndProb: " + comma_str(ENDPROB_AB) + "\n")
        p.stdin.flush()
        resp = p.stdout.readline().strip()
        assert resp == "READY", "Expected READY but got %s" % resp

def send_init_hand(deal, hand):
    for i,p in enumerate(ps):
        p.stdin.write("init_hand\n")
        p.stdin.write("Hand: " + str(hand) + "\n")
        p.stdin.write("Cards: " + CARD_NAMES[deal[i]] + "\n")
        p.stdin.flush()
        resp = p.stdout.readline().strip()
        assert resp == "READY"

def send_actions(i, statuses):
    p = ps[i]
    for j in xrange(len(statuses)):
        p.stdin.write("Action: " + " ".join(map(str, statuses[m(i+j)])) + "\n")

def update_action(i, statuses):
    p = ps[i]
    p.stdin.write("play\n")
    send_actions(i, statuses)
    p.stdin.flush()
    act,val = p.stdout.readline().strip().split()
    # Fail-fast
    assert act in ("PASS", "BET", "FOLD"), \
        "Bad action from player %d: %s" % (i, act)
    val = int(val)
    statuses[i] = (act, val)

def send_showdown(i, showdown):
    showdown_local = showdown[i:] + showdown[:i]
    ps[i].stdin.write("Showdown: " + comma_str(showdown_local) + "\n")

def send_pots(i, pots):
    local_pots = []
    for val,winner in pots:
        local_pots.append((val, m(winner - i)))
    ps[i].stdin.write("Pots: " +" ".join(map(
        lambda x: comma_str(map(str, x)), local_pots)) + "\n")

def get_money(i):
    field,val = ps[i].stdout.readline().strip().split(": ")
    assert field == 'Money', "Expected field Money got %s" % (field)
    money_check = map(int, val.split(","))
    # Translate to global inds
    return money_check[-i:] + money_check[:-i]

def send_end_actions(i, end_acts):
    p = ps[i]
    for j in xrange(len(end_acts)):
        p.stdin.write("EndAction: " + end_acts[m(i+j)] + "\n")
        

def send_end_hand(last_played, statuses, showdown, pots, money):
    # Starting after last_played, send out missed actions
    # and showdown info
    end_acts = ["OK"]*len(statuses)
    for i in xrange(len(statuses)):
        pi = m(last_played + i + 1)
        p = ps[pi]
        p.stdin.write("end_hand\n")
        send_actions(pi, statuses)
        send_showdown(pi, showdown)
        send_pots(pi, pots)
        p.stdin.flush()
        resp = p.stdout.readline().strip()
        assert resp == "OK" # For now, could be REBUY later
        end_acts[pi] = resp
        # Update status to pass, since later players have seen this action
        statuses[pi] = ('PASS', statuses[pi][1])
    # Send out all end actions
    for pi in xrange(len(statuses)):
        send_end_actions(pi, end_acts)
        p = ps[pi]
        p.stdin.flush()
        money_check = get_money(pi)
        assert money_check == money, \
            "Money total off got %s vs %s" % (money_check, money)
        
def send_end_round(num_hands):
    for i,p in enumerate(ps):
        local_money = money[i:] + money[:i]
        p.stdin.write("end_round\n")
        p.stdin.write("Bankrolls: " + comma_str(local_money) + "\n")
        p.stdin.write("NumHands: " + str(num_hands) + "\n")
        p.stdin.flush()
        resp = p.stdout.readline().strip()
        assert resp == "Thank you dealer, have a nice day!"

def alarm_handler(signum, frame):
    raise Exception()

def usage(name):
    print "Usage: %s <bot0> <bot1> <bot2>"


### Main entry point
if __name__ == "__main__":
    if len(sys.argv) != 4:
        usage(sys.argv[0])
        sys.exit(1)
    
    # Handle alarm by just throwing so we have a stack trace
    signal(SIGALRM, alarm_handler)

    # Establish communications
    ps = [Popen(['%s' % sys.argv[i+1]],
              stdin=PIPE, stdout=PIPE, stderr=open('player%d.log' % i, 'w'))
          for i in xrange(NPLAYERS)]
    logfd = open('all_messages.log', 'w')
    for i,p in enumerate(ps):
        lfd = LoggedFDs(p.stdin, p.stdout, i, logfd)
        p.stdin = lfd
        p.stdout = lfd

    money = [0,0,0]
    first_blind = 0 # randomness comes from order of players in
    send_init_round(first_blind)
    cur_hand = 0
    while True:
        print "== Hand %d ==" % (cur_hand)
        print "First blind: %d" % first_blind
        deal = CARDS[:]
        shuffle(deal)
        deal = deal[:NPLAYERS]
        with alarmCtxt(1): send_init_hand(deal, cur_hand)
        statuses = [('BLIND', BLINDS[m(i+first_blind)]) for i in xrange(NPLAYERS)]
        for it in xrange(len(statuses)):
            pi = m(first_blind + it)
            act,val = statuses[pi]
            sys.stdout.write("Player %d: %s %d\t" % (pi, act.rjust(5), val))
        sys.stdout.write("\n")
        sys.stdout.flush()
        # Keep running track of last option, so we can exit the loop.
        # Last option starts with the last person to pay the blind (or ante here).
        # After a raise, last_option goes to whoever is still in the hand and
        # before the raiser.
        last_option = m(first_blind + len(BLINDS) - 1)
        pi = None
        price = BLINDS[-1] # Price to stay in hand
        for it in xrange(MAX_BET_ACTIONS):
            pi = m(first_blind + it)
            old_price = price
            old_act,old_val = statuses[pi]
            with alarmCtxt(1): update_action(pi, statuses)
            act,val = statuses[pi]
            sys.stdout.write("Player %d: %s %d\t" % (pi, act.rjust(5), val))
            if m(it+1) == 0: sys.stdout.write("\n")
            sys.stdout.flush()
            if old_act == 'FOLD' or old_act == 'PASS':
                assert act == 'PASS', \
                    "Action must be a PASS when no play is possible, got %s %d" % (act, val)
                assert val == old_val, \
                    "Value must remain the same when passing (%d changed to %d)" % (old_val, val)
            elif old_act == 'BET' or old_act == 'BLIND':
                if val != old_val: # Raise / call
                    assert act == 'BET', \
                        "Cannot raise without a BET action, %s %d" % (act, val)
                    assert val > old_val, \
                        "Cannot reduce value of bet from %d to %d!" % (old_val, val)
                    assert val <= MAX_BET, \
                        "Cannot bet %d which is more than MAX_BET %d." % (val, MAX_BET)
                    assert val >= price, \
                        "Cannot bet %d which is less than price %d." % (val, price)
                    assert MAX_RAISE is None or val - price <= MAX_RAISE, \
                        "Cannot raise by %d which is more than MAX_RAISE %d." \
                        % (val-price, MAX_RAISE)
                    price = max(price, val)
                else: # Check
                    assert act in ('BET', 'FOLD', 'PASS'), \
                        "Invalid action %s %d" % (act,val)
            else:
                assert False, "Bad old action %s" % (old_act)
            # Update last_option if raise. New last_option is either
            # an earlier live player or None indicating all dead.
            if old_price != price:
                last_option = find_last_option(pi, statuses)
            # Check end of round
            if pi == last_option or last_option is None:
                break
        else:
            assert False, "Failed to complete bet round within %d actions." % (MAX_BET_ACTIONS)
        # pi is the last played index
        assert pi is not None
        if m(it+1) != 0: print

        # Showdown
        showdown = ['-']*len(statuses)
        last_reveal = -1
        winner = None
        live = []
        main_pot = 0
        for i,stat in enumerate(statuses):
            act,val = stat
            if act == 'BET':
                live.append(i)
            # Transfer money into pots
            main_pot += val # TODO: Side pots?
            money[i] -= val
        if len(live) == 1:
            winner = live[0]
        else:
            assert len(live) > 1
            # TODO: Last aggressor behavior?
            for j in xrange(len(statuses)):
                pj = m(first_blind + j)
                if pj in live and deal[pj] > last_reveal:
                    last_reveal = deal[pj]
                    showdown[pj] = CARD_NAMES[deal[pj]]
                    winner = pj
        assert winner is not None

        pots = [(main_pot, winner)]
        for val,winner in pots:
            money[winner] += val

        # Debug output
        print "Showdown:", comma_str(showdown)
        print "Money:", comma_str(money)

        with alarmCtxt(1):
            send_end_hand(pi, statuses, showdown, [(main_pot, winner)], money)

        # Update all counters
        cur_hand += 1
        first_blind = m(first_blind + 1)

        # Check end condition
        if with_prob(ENDPROB):
            break

    with alarmCtxt(1): send_end_round(cur_hand)
    if logfd: logfd.close()

    # Log out final scores: money divided by sqrt(num_hands), since that's
    # the scale of a random walk of this length.
    print "Scores:", comma_str(map(lambda m : m / sqrt(cur_hand), money))
