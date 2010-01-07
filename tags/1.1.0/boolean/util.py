from itertools import *
import sys, os, logging, random, re, string
import cPickle as pickle
import tokenizer, helper

def warn(message):
    sys.stderr.write('*** Warning: %s\n' % message )
    sys.stderr.flush()

class Problem(Exception):
    pass

# provides a user friendly ID to each state
STATE_MAPPER  = {} 
STATE_COUNTER = 0

class State(object):
    """
    Maintains the node state as attributes.
    """
    def __init__(self, **kwds ):
        self.__dict__.update( **kwds )
    
    def __getitem__(self, key):
        return self.__dict__[key]
    
    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __repr__(self):  
        "Default string format"
        keys = self.keys()
        values = [ self.__dict__[key] for key in keys ]
        items  = [ '%s=%s' % (k, v) for k,v in zip(keys, values) ]
        return ', '.join(items)
    
    def keys(self):
        "Returns the sorted keys"
        hdrs = self.__dict__.keys()
        hdrs.sort()
        return hdrs

    def values(self):
        "Returns the values by sorted keys"
        values = [ self.__dict__[key] for key in self.keys() ]
        return values

    def items( self):
        "Returns the items by sorted keys"
        return [ (k, self[k]) for k in self.keys() ]

    def __iter__(self):
        return iter( self.keys() )

    def copy(self):            
        "Duplicates itself"
        s = State( **self.__dict__ )
        return s

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def fp(self):
        "Returns a unique user friendly state definition"
        global STATE_MAPPER, STATE_COUNTER
        value = hash( str(self) )
        
        if value in STATE_MAPPER:
            return STATE_MAPPER[value]
        else:
            STATE_COUNTER += 1
            STATE_MAPPER[value] = 'S%d' % STATE_COUNTER
            return STATE_MAPPER[value]

class Collector(object):
    """
    Collects data over a run
    """
    def __init__(self):
        "Default constructor"
        self.store = {}

    def collect(self, states, nodes):
        "Collects the node values into a list"
        nodes = as_set( nodes )
        for node in nodes:
            values = [ int( getattr(state, node)) for state in states ]
            self.store.setdefault(node, []).append( values )

    def get_averages(self, normalize=True):
        """
        Averages the collected data for the each node
        Returns a dictionary keyes by nodes containing the

        """
        out = {}
        for node in self.store:
            all  = self.store[node]
            size = float( len(all) )        
            
            # this sums lists!
            def listadd( xlist, ylist ):
                return [ x+y for x, y in zip(xlist, ylist) ]
            
            values = reduce(listadd, all)
            
            if normalize:
                def divide(x):
                    return x/size
                values = map(divide, values)
            out[node] = values
        return out

def default_shuffler( alist ):
    "Default shuffler"
    temp = alist[:]
    random.shuffle( temp )
    return temp

def random_pick( alist ):
    "Picks a random line"
    line = random.choice( alist )
    return [ line ]

def add_ranks( text ):
    """
    A convenience function that adds the rank 1: to each line that does not have a rank
    
    """
    lines = text.splitlines()
    
    patt1 = re.compile('\*\W*=')
    patt2 = re.compile('\W*\d+:')
    
    def rank_adder (line):
        line = line.strip()
        if patt1.search(line) and not patt2.match(line):
            line = '1: ' + line
        return line
    
    lines = map( rank_adder, lines)
    return '\n'.join( lines )

def as_set( nodes ):
    """
    Wraps input into a set if needed. Allows single input or
    any iterable
    """
    if isinstance(nodes, str):
        return set( [ nodes ] )
    else:
        return set(nodes)    

def modify_states( text, turnon=[], turnoff=[] ):
    """
    Turns nodes on and off and comments out lines 
    that contain assignment to any of the nodes 
    
    Will use the main lexer.
    """
    text = add_ranks( text )        
    turnon  = as_set( turnon )
    turnoff = as_set( turnoff )
    tokens = tokenize( text )
    init_tokens = filter( lambda x: x[0].type == 'ID', tokens )
    body_tokens = filter( lambda x: x[0].type == 'RANK', tokens )
    init_lines  = map( tokenizer.tok2line, init_tokens )
    
    # append to the states to override other settings
    init_lines.extend( [ '%s=False' % node for node in turnoff ] )
    init_lines.extend( [ '%s=True' % node for node in turnon ] )
    
    common = list( turnon & turnoff )
    if common:
        raise Problem( "Nodes %s are turned both on and off" % ', '.join(common) )

    nodes = turnon | turnoff

    body_lines = []
    for tokens in body_tokens:
        
        # a sanity check
        values = [ t.value for t in tokens ]
        body_line = ' '.join( map(str, values ))
        assert len(tokens) > 4, 'Invalid line -> %s' % body_line
        
        # comment out certain nodes 
        if tokens[1].value in nodes:
            body_line = '#' + body_line
        body_lines.append( body_line )

    return '\n'.join( init_lines + body_lines )

def read( fname):
    """
    Returns the content of a file as text.
    """
    return file(fname, 'rU').read()

def get_lines ( text ):
    """
    Turns a text into lines filtering out comments and empty lines
    """
    lines = map(string.strip, text.splitlines() )
    lines = filter( lambda x: x.strip(), lines )  
    lines = filter( lambda x: not x.startswith('#'), lines )
    return lines

def all_nodes( text ):
    """
    >>> text = 'A and B or C and (A or C and not E)'
    >>> all_nodes( text )
    ['A', 'B', 'C', 'E']
    """
    lexer = tokenizer.Lexer()
    lexer.build()
    lines = get_lines( text )
    tokenlist = map( lexer.tokenize, lines)
    nodes = tokenizer.get_all_nodes( tokenlist )
    nodes = list( set( nodes ) )
    nodes.sort()
    return nodes

def case_sensitivity_check( tokenlist ):
    """
    Verifies IDs in the tokenlist. It may not contain
    the same ID with different capitalization
    """

    # extract all node values from the tokenlist
    toks  = filter(lambda tok: tok.type=='ID', chain( *tokenlist ) )
    names = map( lambda tok: tok.value, toks)

    regular, upper = set(), set()
    def comparator( name):
        uname = name.upper()
        flag = uname in upper and name not in regular
        regular.add(name)
        upper.add( uname )
        return flag
    dups = filter( comparator, names)    
    if dups:
        raise Exception( "Node '%s' present with other capitalization. Probably an error!" % ', '.join( dups ) )
        
def tokenize( text ):
    """
    Tokenizes a text into a list of token lists.
    """
    lines = get_lines( text )
    lexer = tokenizer.Lexer()
    lexer.build()
    tokenlist = map( lexer.tokenize, lines )
    case_sensitivity_check(tokenlist)
    return tokenlist

def join( alist, sep='\t', patt='%s\n'):
    """
    Joins a list with a separator and a pattern
    
    >>> join( [1,2,3], sep=',', patt='%s' )
    '1,2,3'
    """
    return patt % sep.join( map(str, alist) ) 

def log( msg ):
    """
    Logs messages from a source
    
    >>> log( 'logtest' )
    """
    sys.stderr.write( '%s' % msg ) 

def error( msg ):
    """
    Logs errors
    """
    # bail out for now
    raise Problem( msg )

def default_get_value(state, name, p):
    "Default get value function"
    return  getattr( state, name )

def default_set_value(state, name, value, p):
    "Default set value function"
    setattr( state, name, value )
    return value

def randomize(*args, **kwds):
    "Default randomizer function"
    return bool( random.randint(0,1) )

def alltrue(*args, **kwds):
    "Default true function"
    return True

def allfalse(*args, **kwds):
    "Default False function"
    return False

def bsave( obj, fname='data.bin' ):
    """
    Saves (pickles) objects
    >>> obj = { 1:[2,3], 2:"Hello" }
    >>> bsave( obj )
    >>> obj == bload()
    True
    """
    pickle.dump( obj, file(fname, 'wb'), protocol=2 ) # maximal compatibility

def bload( fname='data.bin' ):
    "Loads a pickle from a file"
    return pickle.load( file(fname, 'rb') )
    
def _test():
    """
    Main testrunnner
    """
    # runs the local suite
    import doctest
    doctest.testmod( optionflags=doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE )

if __name__ == '__main__':
    _test()
