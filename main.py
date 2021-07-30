from pyfiglet import main


class Object:
    def __init__(self) -> None:
        self.string = "Hello world"
    
    def __get__(self, instance, owner):
        return self.string

class Main:
    classobject = Object()
    def __init__(self) -> None:
        self.object = Object()

m = Main()
print(m.classobject) #prints hello world
print(m.object)  #prints object location