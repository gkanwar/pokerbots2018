import sys
import random

card_map = {'J': 0, 'Q': 1, 'K': 2, 'A': 3}

def m(x): return x % 3
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


### Brain global state.
### Game state is represented by values of actions
### since the beginning.
LAMBDA = 0.5 # discount
ALPHA = 0.01 # learn rate
state_action_map = {
    (1,1,1): [
        ('BET', 1), ('BET', 2)],
    (1,1,1,1): [
        ('BET', 1), ('BET', 2)],
    (1,1,1,2): [
        ('BET', 2), ('FOLD', 1)],
    (1,1,1,1,1): [
        ('BET', 1), ('BET', 2)],
    (1,1,1,1,2): [
        ('BET', 2), ('FOLD', 1)],
    (1,1,1,2,1): [
        ('BET', 2), ('FOLD', 1)],
    (1,1,1,2,2): [
        ('BET', 2), ('FOLD', 1)],
    (1,1,1,1,1,1): [],
    (1,1,1,1,1,2): [
        ('BET', 2), ('FOLD', 1)],
    (1,1,1,1,2,1): [
        ('BET', 2), ('FOLD', 1)],
    (1,1,1,1,2,2): [
        ('BET', 2), ('FOLD', 1)],
    (1,1,1,2,1,2): [],
    (1,1,1,2,1,1): [],
    (1,1,1,2,2,2): [],
    (1,1,1,2,2,1): [],
    (1,1,1,1,1,2,1): [
        ('BET', 2), ('FOLD', 1)],
    (1,1,1,1,1,2,2): [
        ('BET', 2), ('FOLD', 1)],
    (1,1,1,1,2,1,2): [],
    (1,1,1,1,2,1,1): [],
    (1,1,1,1,2,2,2): [],
    (1,1,1,1,2,2,1): [],
    (1,1,1,1,1,2,1,1): [],
    (1,1,1,1,1,2,1,2): [],
    (1,1,1,1,1,2,2,1): [],
    (1,1,1,1,1,2,2,2): [],
}
def check_state_action_map(state):
    for act,val in state_action_map[state]:
        new_state = tuple(list(state) + [val])
        if not new_state in state_action_map:
            print "Missing state", new_state
            return False
        return check_state_action_map(new_state)
    return True
assert check_state_action_map((1,1,1))
print >>sys.stderr, "State action map is good!"

def update_state(acts, state):
    state = list(state)
    for i in xrange(len(acts)):
        act,val = acts[i]
        if act != "BLIND" and act != "PASS":
            state.append(val)
    return tuple(state)

## Init Q function to uniform
Q_function = {}
for state in state_action_map:
    acts = state_action_map[state]
    Q_function[state] = []
    for i,act in enumerate(acts):
        Q_function[state].append(0.0)

### Start brain
get_msg_named('init_round')
money,blinds,button,end_prob = get_init_round()
first_blind = m(button+1)
print "READY"
fl()

while True:
    msg = get_msg()
    if msg == 'end_round': break
    assert msg == 'init_hand'
    
    # Init hand
    hand,card = get_init_hand()
    state = tuple(blinds)
    choices = []
    assert state in state_action_map
    print "READY"
    fl()

    # First play
    get_msg_named('play')
    acts = get_play_actions()
    state = update_state(acts, state)
    assert state in Q_function
    assert len(Q_function[state]) > 0
    max_ind = max(range(len(Q_function[state])), key=lambda i: Q_function[state][i])
    choices.append((state, max_ind))
    act,val = state_action_map[state][max_ind]
    print act, val
    fl()
        
    msg = get_msg()
    if msg == "play":
        acts = get_play_actions()
        state = update_state(acts, state)
        max_ind = max(range(len(Q_function[state])), key=lambda i: Q_function[state][i])
        choices.append((state, max_ind))
        act,val = state_action_map[state][max_ind]
        print act, val
        fl()

        get_msg_named('end_hand')

    # End hand
    acts = get_play_actions()
    state = update_state(acts, state)
    my_delta = 0
    for i in xrange(len(money)):
        wagered_i = state[m(i-first_blind)::3][-1]
        money[i] -= wagered_i
        if i == 0: my_delta -= wagered_i
    get_showdown()
    pots = get_pots()
    for val,winner in pots:
        money[winner] += val
        if winner == 0: my_delta += val
    print "OK"
    fl()
    get_end_actions() # assume no rebuy for now
    print "Money:", ",".join(map(str, money))
    fl()

    # Update internal state
    first_blind = m(first_blind+1)
    discount = 1.0
    for state,ind in reversed(choices):
        Q_function[state][ind] += ALPHA*my_delta*discount
        discount *= LAMBDA

# End round
bs = get_bankrolls()
num_hands = get_num_hands()
print >>sys.stderr, "Final bankrolls:", ",".join(map(str, bs))
print >>sys.stderr, "Total hands played:", num_hands
# gotta be polite
print "Thank you dealer, have a nice day!"
