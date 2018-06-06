import sys
import random

card_map = {'J': 0, 'Q': 1, 'K': 2, 'A': 3}
# really bad probs for betting -- the opposite of what we should
pbet = [1.0, 0.67, 0.33, 0.0]

def get_msg():
    return sys.stdin.readline().strip()
def get_msg_named(name):
    msg = get_msg()
    assert msg == name
def get_field():
    return get_msg().split(': ')
def get_field_named(name):
    field,val = get_field()
    assert field == name
    return val
def get_init_hand():
    hand = int(get_field_named('Hand'))
    card = card_map[get_field_named('Cards')]
    return hand,card
def get_action():
    act,val = get_field_named('Action').split()
    val = int(val)
    assert act in ("PASS", "BET", "FOLD", "BLIND")
    return act,val
def get_play_actions():
    acts = []
    for i in xrange(3):
        acts.append(get_action())
    return acts
def get_showdown():
    return get_field_named('Showdown').split(',')
def get_pots():
    out = []
    pots = get_field_named('Pots').split()
    for pot in pots:
        val,winner = map(int, pot.split(','))
        out.append((val,winner))
    return out
def get_init_round():
    money = map(int, get_field_named('Money').split(','))
    blinds = map(int, get_field_named('Blinds').split(','))
    button = int(get_field_named('Button'))
    end_prob = map(int, get_field_named('EndProb').split(','))
    return money,blinds,button,end_prob
def get_end_actions():
    return [get_field_named('EndAction') for i in xrange(3)]
def get_bankrolls():
    bs = get_field_named('Bankrolls').split(',')
    return map(int, bs)
def get_num_hands():
    return int(get_field_named('NumHands'))
    

def with_prob(p):
    return random.random() < p
def update_wagered(acts, wagered):
    for i in xrange(len(wagered)):
        act,val = acts[i]
        if act == "BET": wagered[i] = val
def get_call_amt(acts):
    amt = 0
    for act,val in acts:
        if act == "BET":
            amt = max(amt, val)
    return amt

def fl(): sys.stdout.flush()


### Start brain
get_msg_named('init_round')
money,blinds,button,end_prob = get_init_round()
print "READY"
fl()

while True:
    msg = get_msg()
    if msg == 'end_round': break
    assert msg == 'init_hand'
    
    # Init hand
    folded = False
    hand,card = get_init_hand()
    wagered = [0]*3
    for i in xrange(len(blinds)):
        pos = (i + button) % 3
        wagered[pos] = blinds[i]
    cur_bet = wagered[0]
    print "READY"
    fl()

    # First play
    get_msg_named('play')
    acts = get_play_actions()
    update_wagered(acts, wagered)
    call_amt = max(wagered)
    if with_prob(pbet[card]):
        cur_bet = 2
        print "BET", cur_bet
    elif cur_bet == call_amt: # always check
        print "BET", cur_bet
    else:
        folded = True
        print "FOLD", cur_bet
    fl()
        
    msg = get_msg()
    if msg == "play":
        acts = get_play_actions()
        update_wagered(acts, wagered)
        call_amt = max(wagered)
        if call_amt == cur_bet: # check
            print "BET", cur_bet
        elif not folded: # we were in a check/fold, so fold
            print "FOLD", cur_bet
        else: # already folded
            print "PASS", cur_bet
        fl()

        get_msg_named('end_hand')

    # End hand
    acts = get_play_actions()
    update_wagered(acts, wagered)
    for i in xrange(len(wagered)):
        money[i] -= wagered[i]
    get_showdown()
    pots = get_pots()
    for val,winner in pots:
        money[winner] += val
    print "OK"
    fl()
    get_end_actions() # assume no rebuy for now
    print "Money:", ",".join(map(str, money))
    fl()

# End round
bs = get_bankrolls()
num_hands = get_num_hands()
print >>sys.stderr, "Final bankrolls:", ",".join(map(str, bs))
print >>sys.stderr, "Total hands played:", num_hands
# gotta be polite
print "Thank you dealer, have a nice day!"
