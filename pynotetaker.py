import argparse
from posixpath import join
from re import L
from commands.navigation import NotebookSchema
from classes.prompt import *
from whoosh import index
import pickle

"""
A command line utility to take notes
"""

def add_args(parser: argparse.ArgumentParser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-c', '--create',
                        action='store_true',
                        help='mode to create notebook')
    group.add_argument('-o', '--open',
                        action='store_true',
                        help='mode to create notebook')
    parser.add_argument('path',
                        metavar="path",
                        type=str,
                        help='path to notebook')
    parser.add_argument('name',
                        metavar="name",
                        type=str,
                        default="MyNtbk",
                        nargs='*',
                        help='name of notebook (only needed when creating)')

def verifypath(fullpath):
    path, file = os.path.split(fullpath)
    if(os.path.exists(path) or path == ''):
        if(os.path.exists(file)):
            return False
        else:
            return True
    else:
        return False

def create(fullpath, args):
    if(not verifypath(fullpath)):
        print("NoteBook already exists: {}".format(fullpath))
        sys.exit()
    os.makedirs(fullpath)
    indexdir = os.path.join(fullpath, "notebook.index")
    classfile = os.path.join(fullpath, "notebook.class")
    os.makedirs(indexdir)

    schema = NotebookSchema()
    ix = index.create_in(indexdir, schema)

    fs = open(classfile, "wb")
    pickle.dump(Notebook(args.name), fs, pickle.HIGHEST_PROTOCOL)
    fs.close()

    return classfile, ix

def load(fullpath, args):
    if(verifypath(fullpath)):
        print("NoteBook does not exist: {}".format(fullpath))
        sys.exit()
        
    indexdir = os.path.join(fullpath, "notebook.index")
    classfile = os.path.join(fullpath, "notebook.class")

    ix = index.open_dir(indexdir)

    return classfile, ix

def main():
    parser = argparse.ArgumentParser(description='argparser') 
    add_args(parser)
    args = parser.parse_args()

    path = args.path

    if(args.create):
        fs, index = create(path, args)
    else:
        fs, index = load(path, args)
    
    shell = InteractiveShell(fs, index, '/'.join(str(pathlib.Path(__file__).parent.absolute()).split("/")))
    shell.startloop()

if __name__ == "__main__":
    main()