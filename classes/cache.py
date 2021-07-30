
class Node:
    def __init__(self, val):
        self.val = val
        self.next = None
        self.prev = None

class Cache:

    def __init__(self, promptinstance, mode):
        self.promptinstance = promptinstance

        self.mode = mode
        self.head = Node(0)
        self.tail = Node(0)
        self.head.next = self.tail
        self.tail.prev = self.head

    @property
    def cachelength(self):
        if(self.mode):
            return int(self.promptinstance.notebook.env_vars["folder_cache_length"].val)
        else:
            return int(self.promptinstance.notebook.env_vars["file_cache_length"].val)


    def add(self, obj) -> None:
        if(self.cachelength == 0):
            return

        if(n:= self.findnode(obj)):
            self.movetofront(n)
            return

        if(self.mode):
            for name, file in obj.childfiles.items():
                file.cache_file()
        else:
            obj.cache_file()

        node = Node(obj)
        p = self.tail.prev
        p.next = node
        
        self.tail.prev = node
        node.next = self.tail

        node.prev = p 

        if(self.len() > self.cachelength and self.cachelength != -1):
            n = self.head.next
            if(self.mode):
                for name, file in n.val.childfiles.items():
                    file.uncache_file()
            else:
                n.val.uncache_file()
            self.remove(n)
                

    def remove(self, node: Node) -> None:
        p = node.prev
        n = node.next
        p.next = n
        n.prev = p

    def findnode(self, obj):
        current = self.head
          
        while True:
              
            if current.val == obj:
                node = current
                return node
            else:
                current = current.next 
                if(current == None):
                    return None

    def len(self):
        current = self.head
        
        clen = -1
        while True:
            current = current.next
            clen += 1
            if(current == None):
                return max(0, clen-1)


    def movetofront(self, node) -> None:
        self.remove(node)
        self.add(node.val) 

    def uncacheall(self):
        current = self.head
        while True:
            current = current.next 
            if(current == self.tail):
                return
            if(self.mode):
                for name, file in current.val.childfiles.items():
                    file.uncache_file()
            else:
                current.val.uncache_file()
    
    def cachelist(self):
        current = self.head
        ret = list()
        while True:
            current = current.next 
            if(current == self.tail):
                return ret
            ret.append(current.val)
