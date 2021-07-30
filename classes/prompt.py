import pickle
from prompt_toolkit import prompt
from prompt_toolkit import completion
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.filters.app import vi_recording_macro
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator, ValidationError
import itertools
import pathlib
from importlib import util
from classes.completers import *
from classes.command import *
from classes.cache import Cache
import string
import re
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory
from pyfiglet import Figlet #block, catwalk, chunky
from clint.textui import colored
import dill
from whoosh.writing import BufferedWriter
from distutils.util import strtobool


startbanner = """
{}
"help" for help on commands
notebook will be saved when you quit, quit with the "exit" command
"""

class InteractiveShell:
    currinst = None

    def __init__(self, fp, index, cwd) -> None:
        if(InteractiveShell.currinst):
            del InteractiveShell.currinst
        InteractiveShell.currinst = self
        completer = None 
        self.session = PromptSession(completer=completer, complete_while_typing=True)
        self.index = index
        self.writer = BufferedWriter(self.index)
        self.fp = fp
        self.cwd = cwd
        self.currargs = list()
        self.commands = dict()
        self.cogs = dict()
        self.mappedcommands = dict()

        self.notebook = self.load()
        self.path = PathInterpreter(self.notebook.root, self.notebook.root)

        self.updated = False

        self.load_all()

    @property
    def env_vars(self):
        return self.notebook.env_vars

    def add_commands(self, commands, cog):
        for command in commands:
            if(not self.commands.get(cog, None)):
                self.commands[cog] = list()
            self.commands[cog].append(command)
            self.mappedcommands[command.name] = command

    def printl(self, s, end="\n"):
        print(s, end="\n")

    def save(self):
        with open(self.fp, "rb+") as fs:
            dill.dump(self.notebook, fs, pickle.HIGHEST_PROTOCOL)
        if(self.updated):
            self.writer.commit()
            #self.writer.close()
            self.writer = BufferedWriter(self.index)
            self.updated = False

    def load(self):
        with open(self.fp, "rb+") as fs:
            return dill.load(fs)

    def startloop(self):
        completer = self.build_completer()
        f = Figlet(font='slant') #contessa , maxfour, mini
        banner = startbanner.format(colored.green(f.renderText('PyNoteTaker'))).lstrip("\n").rstrip("\n")
        print(banner)

        history = InMemoryHistory()
        self.history = history
        

        self.filecache = Cache(self, False) #true for caching directories
        self.dircache = Cache(self, True)
        self.dircache.add(self.path.cdir)
        
        self.exit=False
        while self.exit==False:
            try:
                text = prompt('{} [{}]$ '.format(self.notebook.name, self.path.cdir.fullpath), validator=Validator(self), completer=completer, history=history) #completer=self.build_completer()
            except KeyboardInterrupt:
                continue
            if(self.notebook.env_vars["save_after_command"].val):
                self.save()
            self.notebook.history.append(history.get_strings()[-1])
            text = text.split()
            commandname = text[:1]
            args = self.currargs[1:]
            self.command_runner(''.join(commandname), args)

        if(self.notebook.env_vars["reset_history"].val):
            self.notebook.history = list()

        self.dircache.uncacheall()
        self.filecache.uncacheall()
        self.save()
        self.writer.close()
        print("\nSaved and Exited...\nBye!")

    def build_completer(self):
        d = dict()
        for command, obj in self.mappedcommands.items():
            d[command] = {}
            parser = obj.parser
            for po in parser.positionals:
                d[command][po] = None
            for npo in parser.nonpositionals:
                d[command][npo] = None
        return MainCompleter.create_from_dict(d, self)

    def command_runner(self, commandname, args):
        if(not (command := self.mappedcommands.get(commandname, None))):
            print("No command found named {}".format(commandname))
        else:
            parseargs = command.parser.parse(args)
            command.callback(parseargs)
    
    def load_all(self):
        cwd = self.cwd
        for filename in os.listdir(os.path.join(cwd, "commands/")):
            if filename.endswith(".py"):
                spec = util.spec_from_file_location("commands", "{}/commands/{}".format(cwd, filename))
                module = util.module_from_spec(spec)
                spec.loader.exec_module(module)
                cog = module.setup(self)
                self.cogs[cog.__class__.__name__] = cog


class Validator(Validator):
    def __init__(self, promptinstance: InteractiveShell) -> None:
        self.promptinstance = promptinstance
        self.commands = promptinstance.mappedcommands

    def validate(self, document: Document) -> None:

        self.promptinstance.currargs = CommandParser.splitargs(document.text, keepquotes=True)
        commandname = ''.join(self.promptinstance.currargs[:1])
        args = self.promptinstance.currargs[1:]
        if(not (command := self.commands.get(commandname, None))):
            raise ValidationError(message='Invalid command: {}'.format(commandname))

        unterminated = Validator.unterminatedstring(' '.join(args))
        if(unterminated):
            raise ValidationError(message=unterminated)
        if(command.validation):
            parser = command.parser
            parsedargs = command.parser.parse(args)
            if(isinstance(parsedargs, str)):
                raise ValidationError(message=parsedargs)
            err = command.validation(parsedargs)
            if(err):
                raise ValidationError(message=err)

    @staticmethod
    def unterminatedstring(s):
        unterminated = False
        string = None
        uindex = None
        for i, c in enumerate(s):
            if(c in "'\""):
                if(c == string):
                    unterminated = False
                    string = None
                    uindex = None
                elif(string == None):
                    unterminated = True
                    string = c
                    uindex = i
        if(unterminated):
            return 'Unterminated quote: {}'.format(s[:uindex+1] + "<")

