from ast import parse
from os import PRIO_PGRP, pread
import sys
from classes.prompt import *
import argparse
import re
from classes.argparser import *

class Cog:
    def __init__(self) -> None:
        self.cogname = self.__class__.__name__
        self.description = "Default category description"
        self.name = self.__class__.__name__

    def loadcommands(self, promptinstance):
        attrs = (getattr(self, name) for name in dir(self))
        commands = list(filter(lambda x: isinstance(x, Command) , attrs))
        commands = self._map_commands(commands, promptinstance)
        self.commands = commands
        self.build_parser()

    def build_parser(self):
        for command in self.commands:
            command.parser = command.completionargs(command.parser)


    def _map_commands(self, commands, promptinstance):

        def good_code(function, instance, promptinstance):
            def wrapper(*args, **kwargs):
                ret = function(instance, promptinstance,  *args, **kwargs)
                return ret
            return wrapper

        #def completionargs(function, instance, promptinstance)

        for command in commands:
            command.callback = good_code(command.callback, self, promptinstance)

            if(command.validation):
                command.validation = good_code(command.validation, self, promptinstance) #manually inject self
            if(command.completionargs):
                command.completionargs = good_code(command.completionargs, self, promptinstance)

        return commands

    @classmethod
    def load(cls, shell, *args):
        self = cls(*args)
        self.loadcommands(shell)
        shell.add_commands(self.commands, self)
        return self


class Command:
    def __init__(self, name, desc, examples, base=False) -> None:
        self.name = name
        self.desc = desc
        self.base = base
        self.examples = examples
        self.parser = CommandParser(self)
        self.validation = None
        self.completionargs = None

    def __call__(self, function):
        def wrapper(instance, promptinstance, parsedata):
            if(parsedata.help):
                print(self.parser.help)
            else:
                function(instance, promptinstance, parsedata)
        self.callback = wrapper
        return self


    def set_validation(self, function):
        def wrapper(instance, promptinstance, parsedata):
            if(parsedata.help):
                return
            else:
                return function(instance, promptinstance, parsedata)
        self.validation = wrapper
        return wrapper
    

    def set_completionargs(self, function):
        self.completionargs = function
        return function
