from tremolo import TremoloApp
import simplejson as json
import gevent

bomber_arena = [
   1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
   1,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,1,
   1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,
   1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,
   1,1,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,
   1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,
   1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,
   1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,1,
   1,1,1,1,1,0,1,0,1,0,1,0,1,1,1,0,1,0,1,
   1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,
   1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
]

def win(player):
    game = player.game
    for bomb in game.bombs:
        gevent.kill(bomb.task)
        bomb.destroy()
    lista_giocatori = []
    for p in game.players:
        lista_giocatori.append(p)
    for p in lista_giocatori:
        try:
            del(game.players[p])
        except:
            pass

"""
this task is execute one time per-bomb
"""
def bomb_task(bomb):
    player = bomb.player
    game = bomb.game
    pos = bomb.pos
    detonation_positions = [pos]
    # on which square the bomb has been dropped ?
    pos_y = pos/game.arena_block_w
    pos_x = pos%game.arena_block_w
    if pos_y > 0:
        detonation_positions.append(pos - game.arena_block_w)
    if pos_y < (game.arena_block_h -1):
        detonation_positions.append(pos + game.arena_block_w)
    if pos_x > 0:
        detonation_positions.append(pos-1)
    if pos_x < (game.arena_block_w -1):
        detonation_positions.append(pos+1)
    # the bomb will detonate in 3 seconds
    gevent.sleep(3)
    print "EXPLODE !!!!"
    # broadcast of the explosion
    bomb_msg = {'c':'x', 'p':player.id, 'i':bomb.id}
    player.game.broadcast(json.dumps(bomb_msg))
    # wait a bit (to allow last-time escapes)
    gevent.sleep(0.4)
    # death check (every dead player will be in this array)
    deaths = []
    for p_id in game.players:
        bp = game.players[p_id]
        p_pos = bp.position(bp.x, bp.y+bp.feet)
        #print p_pos
        if p_pos in detonation_positions:
            announce = {'c':'k', 'p':bp.id, 'a':bp.avatar, 'u':bp.name}
            bp.x = 0
            bp.y = 0
            # broadcast the death of a player
            player.game.broadcast(json.dumps(announce))
            deaths.append(bp.id)
    # remove dead players
    for id in deaths:
        try:
            del(player.game.players[id])
        except:
            pass
    # if at leats one player is dead and only one player is alive, we have a winner...
    if len(deaths) > 0 and len(game.players) == 1:
        winner = game.players[ game.players.keys()[0] ]
        print "VICTORY"
        victory = {'c':'v', 'p':winner.id, 'a':winner.avatar, 'u':winner.name}
        # broadcast the victory
        player.game.broadcast(json.dumps(victory))
        # cleanup the battlefield
        win(winner)
    gevent.sleep(0.6)
    bomb.destroy()

class BomberBomb():
    def __init__(self, player, pos):
        self.id = player.game.bomb_id
        self.player = player
        self.game = player.game
        self.pos = pos
        self.player.bombs_dropped+=1
        self.task = gevent.spawn(bomb_task, self)

    def destroy(self):
        self.game.bombs.remove(self) 
        self.player.bombs_dropped-=1
        
    

class BomberPlayer():

    def __init__(self, game, core_id, avatar):
        self.id = core_id
        self.game = game
        self.pos = 0
        self.direction = 's'
        self.old_direction = 's'
        self.real_old_direction = 's'
        self.avatar = avatar
        self.feet = 28
        self.w = 50
        self.h = 70
        self.x = 50
        self.y = 50+self.game.arena_block - self.h
        self.bombs_available = 3
        self.bombs_dropped = 0
        self.speed = 7
        self.recursion = 0

    def position(self, x, y):
        x1 = x/self.game.arena_block
        xd = x%self.game.arena_block

        y1 = y/self.game.arena_block
        yd = y%self.game.arena_block

        if xd > self.game.arena_block/2:
            x1 += 1

        if yd > self.game.arena_block/2:
            y1 += 1

        return (y1*self.game.arena_block_w)+x1

    def collision(self, x1, y1, w1, h1, x2, y2, w2, h2):
        if (y1 + h1) < y2: return 0
        if y1 > (y2 + h2): return 0
	if (x1 + w1) < x2: return 0
        if x1 > (x2+w2): return 0
        return 1

    def drop_bomb(self):
        if self.bombs_dropped+1 > self.bombs_available: return
        pos = self.position(self.x, self.y+self.feet)
        for bomb in self.game.bombs:
            if pos == bomb.pos: return
        self.game.bomb_id+=1
        pos_y = pos/self.game.arena_block_w
        pos_x = pos%self.game.arena_block_w
        self.bomb_x = pos_x*self.game.arena_block
        self.bomb_y = pos_y*self.game.arena_block
	bomb = {'c':'b', 'p':self.id, 'i':self.game.bomb_id, 'x':self.bomb_x, 'y':self.bomb_y}
        new_bomb = BomberBomb(self, pos)
        self.game.bombs.append(new_bomb)
        self.game.broadcast(json.dumps(bomb))

    def move_north(self):
        self.recursion += 1
        if self.recursion > 2: return
        coll = self.collide(self.x, (self.y+self.feet)-self.speed)
        if not coll:
            self.y -= self.speed
            self.old_direction = self.direction
            self.direction = 'n'
            self.real_old_direction = self.direction
            self.redraw()
        else:
            #print self.real_old_direction
            if self.real_old_direction == 'e':
                self.move_east()
            elif self.real_old_direction == 'w':
                self.move_west()

    def move_south(self):
        self.recursion += 1
        if self.recursion > 2: return
        coll = self.collide(self.x, (self.y+self.feet)+self.speed)
        if not coll:
            self.y += self.speed
            self.old_direction = self.direction
            self.direction = 's'
            self.real_old_direction = self.direction
            self.redraw()
        else:
            #print self.real_old_direction
            if self.real_old_direction == 'e':
                self.move_east()
            elif self.real_old_direction == 'w':
                self.move_west()

    def collide(self, x, y):
        pos = self.position(x, y)
        new_pos = pos
	pos_y = pos/self.game.arena_block_w
        pos_x = pos%self.game.arena_block_w
        # check the 9 surrounding blocks (0-8)
        # pos: 4,1,7
        positions = [pos]
        if pos_y > 0:
            positions.append( pos - self.game.arena_block_w)
        if pos_y < (self.game.arena_block_h-1):
            positions.append( pos + self.game.arena_block_w)
        # pos: 3,0,6
        if pos_x > 0:
            positions.append(pos-1)
            if pos_y > 0:
                positions.append( (pos - self.game.arena_block_w) -1)
            if pos_y < (self.game.arena_block_h-1):
                positions.append( (pos + self.game.arena_block_w) -1)
        # pos: 2,5,8
        if pos_x < (self.game.arena_block_w-1):
            positions.append(pos+1)
            if pos_y > 0:
                positions.append( (pos - self.game.arena_block_w) + 1)
            if pos_y < (self.game.arena_block_h-1):
                positions.append( (pos + self.game.arena_block_w) + 1)
        
	
        # collision con una delle 9 caselle circostanti
        for pos in positions:
            pos_y = (pos/self.game.arena_block_w) * self.game.arena_block
            pos_x = (pos%self.game.arena_block_w) * self.game.arena_block
            if self.game.arena[pos] != 0 and self.collision(x+5,y+5, 40, 40, pos_x, pos_y, self.game.arena_block, self.game.arena_block):
                return pos

        # collision con una bomba (solo in entrata)
        player_pos = self.position(self.x, self.y+self.feet)
        for bomb in self.game.bombs:
            if player_pos != bomb.pos:
                if new_pos == bomb.pos: return bomb.pos

        return None

    def move_east(self):
        self.recursion += 1
        if self.recursion > 2: return
        coll = self.collide(self.x+self.speed, self.y+self.feet)
        if not coll:
            self.x += self.speed
            self.old_direction = self.direction
            self.direction = 'e'
            self.real_old_direction = self.direction
            self.redraw()
        else:
            #print self.real_old_direction
            if self.real_old_direction == 'n':
                self.move_north()
            elif self.real_old_direction == 's':
                self.move_south()

    def move_west(self):
        self.recursion += 1
        if self.recursion > 2: return
        coll = self.collide(self.x-self.speed, self.y+self.feet)
        if not coll:
            self.x -= self.speed
            self.old_direction = self.direction
            self.direction = 'w'
            self.real_old_direction = self.direction
            self.redraw()
        else:
            #print self.real_old_direction
            if self.real_old_direction == 'n':
                self.move_north()
            elif self.real_old_direction == 's':
                self.move_south()

    def redraw(self):
        msg = {'c':'m', 'p':self.id, 'a':self.avatar, 'x':self.x, 'y':self.y, 'd':self.direction, 'o':self.old_direction}
        #print self.x,self.y
        self.game.broadcast(json.dumps(msg))

class BomberTab(TremoloApp):

    players = {}
    arena = bomber_arena
    bomb_id = 0
    arena_block = 50
    arena_block_w = 19
    arena_block_h = 11
    arena_w = arena_block_w * arena_block
    arena_h = arena_block_h * arena_block
    bombs = []
    commands = {}

    def __init__(self, *args, **kwargs):
        self.commands['n'] = self.north
        self.commands['s'] = self.south
        self.commands['e'] = self.east
        self.commands['w'] = self.west
        self.commands['b'] = self.bomb
        self.commands['0'] = self.stop
        super(BomberTab, self).__init__(*args, **kwargs) 

    def end(self, core_id):
        print "player %d disconnected" % core_id
        try:
            bp = self.players[core_id]
        except:
            return
        announce = {'c':'k', 'p':core_id, 'a':bp.avatar, 'u':bp.name}
        self.broadcast(json.dumps(announce))
        try:
            del(self.players[core_id])
        except:
            pass

    def websocket(self, core_id, js):
        msg = json.loads(js) 
        if msg['c'] == 'j':
            bp = BomberPlayer(self, core_id, msg['a'])
            bp.name = msg['u']
            lista_giocatori = []
            for player in self.players.keys():
                ep = self.players[player]
                lista_giocatori.append([ep.id, ep.avatar, ep.x, ep.y, ep.name])

            response = {'c': 'z', 'p':bp.id, 'b': self.arena, 'e': lista_giocatori, 'x':bp.x, 'y':bp.y, 'a': bp.avatar, 'u':bp.name}
            self.send(json.dumps(response))
            # broadcast new player presence
            announce = {'c':'p', 'p':bp.id, 'x':bp.x, 'y':bp.y, 'a': bp.avatar, 'u':bp.name}
            self.broadcast(json.dumps(announce))

            self.players[core_id] = bp
            # join the game
            print "new player", core_id
            return
        elif msg['c'] == 'J':
            bp = BomberPlayer(self, core_id, msg['a'])
            bp.name = msg['u']
            # broadcast new player presence
            announce = {'c':'p', 'p':bp.id, 'x':bp.x, 'y':bp.y, 'a': bp.avatar, 'u':bp.name}
            self.broadcast(json.dumps(announce))

            self.players[core_id] = bp
            # join the game
            print "player replay", core_id
        else:
            try:
                bp = self.players[msg['p']] 
                self.commands[msg['c']](bp, msg)
            except:
                pass
        #print msg

    # n
    def north(self, bp, msg):
        bp.recursion = 0
        bp.move_north()

    # s
    def south(self, bp, msg):
        bp.recursion = 0
        bp.move_south()

    # e
    def east(self, bp, msg):
        bp.recursion = 0
        bp.move_east()

    # w
    def west(self, bp, msg):
        bp.recursion = 0
        bp.move_west()

    # b
    def bomb(self, bp, msg):
        bp.drop_bomb()

    # 0
    def stop(self, bp, msg):
        announce = {'c':'0', 'p':bp.id, 'd':bp.direction, 'a':bp.avatar, 'u':bp.name}
        bp.direction = '0'
        self.broadcast(json.dumps(announce))

application = BomberTab(redis_host='127.0.0.1',redis_port=6379)
