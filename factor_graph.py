
'''From SumProd.pdf'''
import sys
import inspect

'''
The example in SumProd.pdf has exactly the same shape 
as the cancer example:

(Note arrows are from x1->x3, x2->x3, x3->x4 and x3->x5)

      x1      x2
       \      /
        \    /
         \  /
          x3
         /  \
        /    \
       /      \
      x4      x5


The equivalent Factor Graph is:


     fA        fB
     |          |
     x1---fC---x2
           |
     fD---x3---fE
     |          |
     x4         x5


fA(x1) = p(x1)
fB(x2) = p(x2)
fC(x1,x2,x3) = p(x3|x1,x2)
fD(x3,x4) = p(x4|x3)
fE(x3,x5) = p(x5|x3)

Lets simulate this, from SumProd.pdf:

Step1:
Start at all the leaf nodes ie fA, fB, x4, x5

mfA -> x1 = fA(x1)  ie this is passing along a function and a parameter
mfB -> x2 = fB(x2) 
mx4 -> fD = 1       when starting from a variable node we always send a 1 (Not sure for the constrained version)
mx5 -> fE = 1

So at this point we have recorded the message *at* the recipient

Step 2:
mx1 -> fC = fA(x1)  This is the same message that fA passed to x1 in step 1
mx2 -> fC = fB(x2)  This is the same message that fB passed to x2 in step 1
mfD -> x3 = sum(fD(x3,x4) * mx4 -> fD (Note that the sum should *exclude* x3 and that the mx4->fd messages is 1
mfE -> x3 = sum(fE(x3,x5) * mx5 -> fE

???? Parts I dont understand is *when* is anything actually evaluated?
It seems that messages are either a 1 (if it originiated at a leaf variable) or they are a sum of functions
with unbound variables or do the factor nodes substitute the value they got into the equation?????

Only thing to do is try it!

Converting the cancer example to a factor graph..

'''
class Node(object):
    
     def is_leaf(self):
        if not (self.parents and self.children):
            return True
        return False

     def send_to(self, recipient, message):
        print('%s--->%s'%(self.name,recipient.name),message)
        recipient.received_messages[self.name] = message
    
     def message_report(self):
         '''
         List out all messages Node
         currently has received.
         '''
         print('------------------')
         print('Messages at Node %s'% self.name)
         print('------------------')
         for k, v in self.received_messages.items():
             print('%s<--Argspec:%s'%(v.source.name,v.argspec))
             v.list_factors()
         print('--')

class VariableNode(Node):
    
    def __init__(self, name, parents=[], children=[]):
        self.name = name
        self.parents = parents
        self.children = children
        self.received_messages = {}
        self.sent_messages = {}
        #self.current_value = 1
    
    def marginal(self , val):
        '''
        the marginal function is the product of all
        incoming messages which should be 
        functions of this node variable
        '''
        product = 1
        for _, message in self.received_messages.items():
            product *= message.func(val)
        return product

    def __repr__(self):
        return '<VariableNode: %s>' % self.name    

class FactorNode(Node):

    def __init__(self, name,func, parents=[], children=[]):
        self.func = func
        self.name = name
        self.parents = parents
        self.children = children
        self.received_messages = {}
        self.sent_messages = {}
        #self.bindings = dict()

    def __repr__(self):
        return '<FactorNode %s %s(%s)>' % \
            (self.name,
             self.func.__name__,
             get_args(self.func))
            
class Message(object):

    def list_factors(self):
        print ('---------------------------')
        print ('Factors in message %s -> %s' % (self.source.name, self.destination.name))
        print ('---------------------------')
        for factor in self.factors:
            print (factor) 

class FactorMessage(Message):
    
    def __init__(self , source , destination , not_sum):
        self.source = source
        self.destination = destination
        self.factors = not_sum.factors
        self.not_sum = not_sum
        self.argspec = [destination.name]
    def __repr__(self):
        return '<F-Message %s -> %s: ~(%s) %s factors (%s)>' % \
            (self.source.name, self.destination.name,
             self.not_sum.exclude_var,
             len(self.factors), self.argspec)

class VariableMessage(Message):
    
    def __init__(self , source ,destination , factors):
        self.source = source
        self.destination = destination
        self.factors = factors
        self.argspec = [source.name]
        
    def __repr__(self):
         return '<V-Message from %s -> %s: %s factors (%s)>' % \
            (self.source.name, self.destination.name, 
             len(self.factors), self.argspec)

class NotSum(object):
    
    def __init__(self, exclude_var, factors):
        self.exclude_var = exclude_var
        self.factors = factors
        self.argspec = [exclude_var]

    def __repr__(self):
        return '<NotSum(%s, %s)>' % (self.exclude_var, '*'.join([repr(f) for f in self.factors]))

def make_factor_node_message(node, target_node):
    '''
    The rules for a factor node are:
    take the product of all the incoming
    messages (except for the destination
    node) and then take the sum over
    all the variables except for the
    destination variable.
    >>> def f(x1, x2, x3): pass
    >>> node = object()
    >>> node.func = f
    >>> target_node = object()
    >>> target_node.name = 'x2'
    >>> make_factor_node_message(node, target_node)
    '''
    if node.is_leaf():
        not_sum = NotSum(target_node.name , [node.func])
        message = FactorMessage(node , target_node ,not_sum )
        return message
        
    args = set(get_args(node.func))
    
    # Compile list of factors for message
    factors = [node.func]
    
    # Now add the message that came from each
    # of the non-destination neighbours...
    neighbours = node.children + node.parents
    for neighbour in neighbours:
        if neighbour == target_node:
            continue
    #when we pass on a message, we unwrap the original
    #payload and wrap it in new headers,this is purely to verify
    # the procedure is correct according to usual nomenclature
        in_message = node.received_messages[neighbour.name]
        if in_message.destination != node:
            out_message = VariableMessage(neighbour,
                                          node,in_message.factors)
            out_message.argspec = in_message.argspec
        else:
            out_message = in_message
        factors.append(out_message)
    # Now we need to add any other variables 
    # that were added from the other factors
    

    #args = args.difference(set([target_node.name]))

    # Now we sum over every variable in every factor
    # that will comprise this message except for 
    # the target node...
    not_sum = NotSum(target_node.name,factors)
    message = FactorMessage(node , target_node , not_sum)
    return message

def make_variable_node_message(node , target_node):
    '''
     To construct the message from 
    a variable node to a factor
    node we take the product of
    all messages received from
    neighbours except for any
    message received from the target.
    If the source node is a leaf node
    then send the unity function.
    '''
    if node.is_leaf():
        message = VariableMessage(node , target_node , [unity])
        return message
    factors = []
    neighbours = node.children + node.parents
    #print(neighbours)
    for neighbour in neighbours:
        if neighbour == target_node:
            continue
        #print(neighbour.func.__name__)
        factors.append(node.received_messages[neighbour.name])
    
    
    message = VariableMessage(node,target_node,factors)
    return message

def get_args(func):
    '''
    Return the names of the arguments
    of a function as a list of strings.
    This is so that we can omit certain
    variables when we marginalize.
    Note that functions created by
    make_product_func do not return
    an argspec, so we add a argspec
    attribute at creation time.
    '''
    if hasattr(func, 'argspec'):
        return func.argspec
    return inspect.getargspec(func).args


def make_product_func(factors):
    '''
    Return a single callable from
    a list of factors which correctly
    applies the arguments to each 
    individual factor
    '''
    args_map = {}
    all_args = []
    for factor in factors:
        #print('\n',factors,'-----',factor,'\n')
        args_map[factor] = get_args(factor)
        all_args += args_map[factor]

    # Now we need to make a callable that
    # will take all the arguments and correctly
    # apply them to each factor...
    args = list(set(all_args))
    #args.sort()
    args_list = expand_parameters(args,[True,False])
    def product_func(*args):
        result = 1
        for factor in factors:
            result *=factor(args)
        return result
    product_func.argspec = args
    product_func.factors = factors
    return product_func
            
def make_unity(args):
    def unity(x):
        return 1
    unity.argspec = args
    return unity

def unity():
    return 1
    
def expand_parameters(args, vals):
    '''
    Given a list of args and values
    we return a list of tuples
    containing all possible n length
    sequences of vals where n is the
    length of args.
    '''

    result = []
    if not args:
        return [result]
    rest = expand_parameters(args[1:], vals)
    for r in rest:
        result.append([True] + r)
        result.append([False] + r)
    return result


def pollution_func(P):
    if P == True:
        return 0.1
    elif P == False:
        return 0.9
    raise 'pdf cannot resolve for %s' % x


def smoker_func(S):
    if S == True:
        return 0.3
    if S == False:
        return 0.7


def cancer_func(P, S, C):
    ''' 
    This needs to be a joint probability distribution
    over the inputs and the node itself
    '''
    table = dict()
    table['ttt'] = 0.05
    table['ttf'] = 0.95
    table['tft'] = 0.02
    table['tff'] = 0.98
    table['ftt'] = 0.03
    table['ftf'] = 0.97
    table['fft'] = 0.001
    table['fff'] = 0.999
    key = ''
    key = key + 't' if P else key + 'f'
    key = key + 't' if S else key + 'f'
    key = key + 't' if C else key + 'f'
    return table[key]


def xray_func(C, X):
    table = dict()
    table['tt'] = 0.9
    table['tf'] = 0.1
    table['ft'] = 0.2
    table['ff'] = 0.8
    key = ''
    key = key + 't' if c else key + 'f'
    key = key + 't' if x else key + 'f'
    return table[key]


def dyspnoea_func(C, D):
    table = dict()
    table['tt'] = 0.65
    table['tf'] = 0.35
    table['ft'] = 0.3
    table['ff'] = 0.7
    key = ''
    key = key + 't' if c else key + 'f'
    key = key + 't' if d else key + 'f'
    return table[key]














