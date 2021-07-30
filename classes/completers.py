from typing import Mapping
from classes.argparser import *
from classes.notebook import *
from os import error, pread, terminal_size
from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit import prompt
from prompt_toolkit import completion
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator, ValidationError

class WordCompleter(Completer):

    def __init__(self, words, ignore_case=True, checkfunc = None) -> None:
        if(not checkfunc):
            self.checkfunc = self.defaultcheck
        else:
            self.checkfunc = None
        self.ignore_case = ignore_case
        self.words = words

    def defaultcheck(self, word, lastword):
        return -len(lastword), word.startswith(lastword)

    def nonpositionalcheck(self, word, lastword):
        name, val = CommandParser._split_nonpositional(lastword)
        if(val == None):
            val = ""
        return  -len(val), word.startswith(val)

    def pathcheck(self, word, lastword):
        if(lastword.endswith("/")):
            lastword = ""
        else:
            lastword = CommandParser.splitargs(lastword, "/", keepquotes=True)
            if(lastword):
                lastword = lastword[-1]
            else:
                lastword = ""
        return -len(lastword), word.startswith(lastword)


    def get_completions(self, args, document: Document, complete_event: CompleteEvent):

        words = self.words

        lastword = args[-1]

        if self.ignore_case:
            lastword = lastword.lower()

        for a in words:
            word, display = a
            if(self.ignore_case):
                word = word.lower()
            start, match = self.checkfunc(word, lastword)
            if match:
                yield Completion(
                    word,
                    start,
                    display=display,
                )


class MainCompleter(Completer):
    def __init__(self, completions, promptinstance) -> None:
        self.promptinstance = promptinstance
        self.completions = completions

    @property
    def mapped_args(self):
        return self.promptinstance.currargs
    
    @classmethod
    def create_from_dict(cls, d: dict, promptinstance):
        ret = dict()
        for key, val in d.items():
            if(isinstance(val, dict)):
                ret[key] = val
                ret[key]["positional"] = list()
                ret[key]["nonpositional"] = list()
                for arg in ret[key].keys():
                    if(not isinstance(arg, ParseObject)):
                        continue
                    arg: ParseObject
                    if(arg.positional):
                        ret[key]["positional"].append(arg)
                    else:
                        ret[key]["nonpositional"].append(arg) 

            else:
                ret[key] = val
        return cls(ret, promptinstance)
    
    def get_completions(self, document: Document, complete_event: CompleteEvent):
        text = document.text_before_cursor.lstrip()
        try:
            new = text[-1] == " "
            input = self.mapped_args
            commandname = input[0]
            args = input[1:]
            if(new):
                args.append('')
        except:
            new = None
            commandname = ""
            args = []
            input = ['']

        if(not args):
            completion = WordCompleter(MainCompleter.mergelists(list(self.completions.keys()), list(self.completions.keys())), ignore_case=True)
            for c in completion.get_completions(input, document, complete_event):
                yield c
        else:
            currarg = MainCompleter.get_currentpos(args)
            commanddict = self.completions.get(commandname, None)
            if(not commanddict):
                return
            positionals = commanddict["positional"]
            nonpositionals = commanddict["nonpositional"]
            lastarg = args[-1]

            if(re.match(r'^-[\s\S]+=', lastarg)):
                name, val = CommandParser._split_nonpositional(lastarg)
                name = CommandParser.remove_quotes(name)
                val = CommandParser.remove_quotes(val)
                npo = [x for x in nonpositionals if x.name == name or x.alias == name]
                if(npo):
                    npo = npo[0]
                    vals = npo.vals
                    completion = WordCompleter(MainCompleter.mergelists(vals, vals), ignore_case=True)
                    completion.checkfunc = completion.nonpositionalcheck
                    for c in completion.get_completions(input, document, complete_event):
                        yield c
            else:

                try:
                    vals = positionals[currarg].vals

                    #print(positionals, currarg, positionals[currarg], vals)
                    for y in self.yield_vals(vals, document, complete_event, [commandname] + args):
                        yield y
                except Exception as err:
                    pass

                try:
                    vals = list(map(lambda x: "-"+ x.name, nonpositionals))
                    for y in self.yield_vals(vals, document, complete_event, [commandname] + args):
                        yield y
                except Exception as err:
                    return

    def yield_vals(self, vals, document, complete_event, input):
        path = [val for val in vals if isinstance(val, PathInterpreter)]
        if(path):
            #print("yes")
            path = path[0]
            wpath = input[-1]
            
            completions = path.completions_on_path(wpath)
            for i, completion in enumerate(completions):
                if(completion.endswith("/")):
                    complete = completion[:-1]
                else:
                    complete = completion
                display = completion
                completions[i] = [complete, display]

            completion = WordCompleter(completions, ignore_case=True)
            completion.checkfunc = completion.pathcheck
            for c in completion.get_completions(input, document, complete_event):
                yield c

        completion = WordCompleter(MainCompleter.mergelists(vals, vals), ignore_case=True)
        for c in completion.get_completions(input, document, complete_event):
            yield c

    @staticmethod
    def get_currentpos(args):
        currentpos = -1
        for arg in args:
            if(not re.match(r'^-[\s\S]+', arg)):
                currentpos += 1
        return max(0, currentpos)

    @staticmethod
    def mergelists(l1, l2):
        ret = list()
        for i, x in enumerate(l1):
            ret.append([x,l2[i]])
        return ret