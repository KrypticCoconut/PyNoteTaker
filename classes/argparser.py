from argparse import RawDescriptionHelpFormatter
from os import fwalk, stat
import re
import operator
import prompt_toolkit

helpstringformat = """
Usage: {}
Description: {}

Mandatory arguments are marked with [Mandatory] flag
Bool value arguments (only need non-positional specifier to switch) have [Bool] flag
Non-Positional arguments are marked with [Non-Positional] flag and have a "-" before them:
Arguments that ignore all other args (like -help) are marked with [Ignore-All]
{}
{}
"""

class CommandParser:
    def __init__(self, command) -> None:
        self.commandname = command.name
        self.desc = command.desc
        self.examples = command.examples

        self.positionals = list()
        self.nonpositionals = list()

        self.add_arg("help", "h", "Shows help page for command", False, False, True, True)


    def add_arg(self, name, alias, help, positional=False, required=False, bool=False, ignoreall=False):
        arg = ParseObject(name, alias, help, positional, required, bool, ignoreall)
        if(not arg.positional):
            self.nonpositionals.append(arg)
            # list(map(lambda x: x.name, parser.nonpositionals))
            # self.nonpositionals = sorted(self.nonpositionals, key=lambda x: x.name)
            return arg

        if(arg.required):
            for i, p in enumerate(self.positionals):
                if(not p.required):
                    self.positionals.insert(i-1, arg)
                    return arg
        self.positionals.append(arg)
        return arg

    def order_npo(self):
        cindex = 0
        new = list()
        for npo in self.nonpositionals:
            if(npo.ignoreall):
                new.insert(cindex, npo)
                cindex += 1
            else:
                new.append(npo)
        return new



    def parse(self, args):
        positionals = list()
        nonpositionals = dict()
        ignore = False
        
        self.nonpositionals = self.order_npo()

        for arg in args:
            if(re.match(r'^-[\s\S]+', arg)):
                name, val = CommandParser._split_nonpositional(arg)
                nonpositionals[CommandParser.remove_quotes(name)] = CommandParser.remove_quotes(val)
            else:
                positionals.append(CommandParser.remove_quotes(arg))

        ret = ParseData()

        parsed = list()
        for npo in self.nonpositionals:
            name = npo.name
            alias = npo.alias
            cnpo  = [key for key in nonpositionals.keys() if key == name or key==alias]
            if(not cnpo):
                if(npo.bool):
                    ret.add(npo.name, False)
                    continue
                if(npo.required and not ignore):
                    return "Missing requried non-positional argument \"{}\"".format(npo.name)
                else:
                    ret.add(npo.name, None)
                    continue
            cnpo = cnpo[0]
            if(npo.bool):
                if(nonpositionals[cnpo] is not True):
                    continue
                if(npo.ignoreall):
                    ignore = True
                ret.add(npo.name, True)
                parsed.append(cnpo)
                continue
            parsed.append(cnpo)
            ret.add(npo.name, nonpositionals[cnpo])


        i=-1 #clear code
        for i, po in enumerate(positionals):
            if(len(self.positionals)-1 < i):
                return "Extra positional argument \"{}\"".format(po)
            opo = self.positionals[i]
            ret.add(opo.name, po)

        left = self.positionals[i+1:]
        if(left):
            for x in left:
                if(x.required and not ignore):
                    return "Missing requried positional argument \"{}\"".format(x.name)
                else:
                    ret.add(x.name, None)


        for extra in set(parsed).symmetric_difference(set(nonpositionals.keys())):
            # if(ignore):
            #     break
            return "Extra non-positional argument \"{}\"".format(extra)

        return ret
    
    @staticmethod
    def _get_npo_in_list(l, npo):
        for i, x in enumerate(l):
            if(npo.name == x[0] or npo.alias == x[0]):
                ret = x
                if(npo.bool):
                    if(ret[1] != None):
                        return None
                    del l[i]    
                    return True
                del l[i]
                return ret[1]
        if(npo.bool):
            return False
        return None

    @staticmethod
    def _split_nonpositional(npo):
        onpo = npo[1:]
        npo = CommandParser.splitargs(onpo, "=", keepquotes=True, onetime=True)
        name = ''.join(npo[:1])
        val = ''.join(npo[1:])
        if(val == ''):
            val = None
        if(not val and len(name)-1 == len(onpo)-1):
            val = True
        return name, val 

    @staticmethod
    def splitargs(argstring, splitter=" ", keepquotes=False, keepnonespaces=False, onetime=False):
        #good code and efficient dont @ me
        lock = [False, None]
        args = list()
        word = str()
        first = False
        for i, char in enumerate(argstring):
            if(char in "'\""):
                if(not lock[0]):
                    lock[1] = char
                    lock[0] = True
                    if(keepquotes):
                        word += char
                elif(lock[1] == char):
                    lock[1] = None
                    lock[0] = False
                    if(keepquotes):
                        word += char
                else:
                    word += char
            else:
                word += char
            if(not lock[0] and char == splitter and not (onetime and first)):
                if(word[:-1] == ""):
                    if(keepnonespaces):
                        pass
                    else:
                        word = ""
                        continue
                args.append(word[:-1])
                first = True
                word = ""
                continue
            if(i == len(argstring)-1):
                if(word == ""):
                    if(keepnonespaces):
                        pass
                    else:
                        word = ""
                        continue
                args.append(word)
                word = ""
        
        return args

    @staticmethod
    def remove_quotes(string):
        string: str
        if(not isinstance(string, str)):
            return string
        if(string.startswith("\"") and string.endswith("\"")):
            string = string[1:-1]
        if(string.startswith("'") and string.endswith("'")):
            string = string[1:-1]
        return string

    @property
    def usage(self):
        string = "{} ".format(self.commandname)
        for po in self.positionals:
            string += "{} ".format(po.name)

        for npo in self.nonpositionals:
            t = "-{}"
            if(npo.alias):
                t = t + ", -{}"
            t = ("[" + t + "]").format(npo.name, npo.alias)
            string +=  "{} ".format(t)
        return string
    
    @property
    def help(self):
        global helpstringformat
        argstring = ""
        for arg in self.nonpositionals + self.positionals:
            arg: ParseObject
            if(arg.positional):
                name = arg.name
            else:
                name = "-{}"
                if(arg.alias):
                    name += ", -{}"
                name = name.format(arg.name, arg.alias)

            help = arg.help
            modifiers = ""
            if(arg.positional):
                modifiers += "[Positional] "
            if(arg.required):
                modifiers += "[Required] "
            if(arg.bool):
                modifiers += "[Bool] "
            if(arg.ignoreall):
                modifiers += "[Ignore-All] "
            argstring += " {:<18} {:<30} {:<30}\n".format(name, help, modifiers)
        return helpstringformat.format(self.usage, self.desc, argstring.rstrip("\n"), self.examples).rstrip("\n").lstrip("\n")


class ParseObject:
    def __init__(self, name, alias, help, positional, required, bool, ignoreall) -> None:
        self.name = name
        self.help = help
        self.bool = bool
        self.ignoreall = ignoreall
        self.vals = list()
        if(self.ignoreall):
            self.bool = True
        if(self.bool):
            self.required=False
            self.positional = False
        else:
            self.required = required
            self.positional = positional
        if(self.positional):
            self.alias = None
        else:
            self.alias = alias

        


class ParseData:
    def __init__(self) -> None:
        self.data = dict()

    def add(self, name, value) -> None:
        setattr(self, name, value)
        self.data[name] = value