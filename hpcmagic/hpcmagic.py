# This code can be put in any Python module, it does not require IPython
# itself to be running already.  It only creates the magics subclass but
# doesn't instantiate it yet.
from __future__ import print_function
from IPython.core.magic import (Magics, magics_class, line_magic,
                                cell_magic, line_cell_magic)

import subprocess
import os
import sys
import argparse
import configparser
import site
import time

# Define successful compilation
SUCCESS=bool(0)

class Code_Helper:
    
    def __init__(self, configfile):
        # Read the default configuration from file
        self.config=configparser.ConfigParser()
        self.config.read(configfile)

        # Do we overlay environment variables?
        self.overlay_environment()

    def overlay_environment(self):
        # Overlay any environment variables into the configuration
        for key in self.config["DEFAULT"]:
            if key in os.environ:
                self.config["DEFAULT"][key] = os.environ[key]

    def modify_config(self, config_string):
        # Suck a new configuration into the string
        for token in config_string.split(":"):
            try:
                (key, equals, value)=token.partition("=")
                self.config["DEFAULT"][key]=str(value)        
            except:
                pass
    
    def post_init_tasks(self):
        # Run post_init_tasks
        self.run_dir=str(self.config["DEFAULT"]["RUN_DIR"])
        try:
            os.makedirs(self.run_dir, exist_ok=True)
        except:
            pass

        # Set the number of OpenMP threads
        os.environ["OMP_NUM_THREADS"]=self.config["DEFAULT"]["OMP_NUM_THREADS"]

    def compile_code(self, fnames):

        try:
            # Return value
            return_val = None

            # Compile the code
            logfile=os.path.join(self.run_dir,"compile.log")
            fd=open(logfile, "w")

            # Last fname is the one to get the name of output code
            if isinstance(fnames,str):
                filenames=[fnames]
            else:
                filenames=list(fnames)
            objects=[]

            # Did we error out?
            had_error=False

            # Loop through and compile each file
            for fname in filenames:
                (root,ext)=os.path.splitext(fname)
                object_fname=root+".o"
                objects.append(object_fname)
                if ext==".f90":
                    commands=[self.config["DEFAULT"]["FC"],
                              *self.config["DEFAULT"]["FCFLAGS"].split(),"-c",fname,"-o",object_fname]
                elif ext==".cpp":
                    commands=[self.config["DEFAULT"]["CXX"],
                              *self.config["DEFAULT"]["CXXFLAGS"].split(),"-c",fname,"-o",object_fname]
                elif ext==".c":
                    commands=[self.config["DEFAULT"]["CC"],
                              *self.config["DEFAULT"]["CFLAGS"].split(),"-c",fname,"-o",object_fname]

                if self.config["DEFAULT"]["VERBOSE"].lower()=="yes":
                    print("Compiling: {}".format(" ".join(commands)))
                result = subprocess.run(commands, stderr=fd, stdout=fd)
                if result.returncode != SUCCESS:
                    raise OSError(result.returncode, f"Error in compiling file {fname}", fname) 

            # Program name is derived from last file
            (program_name, ext)=os.path.splitext(filenames[-1])
            
            # Add an extension
            program_name=program_name+".exe"
            
            # Now link the object files and return the name of the program
            commands=[  self.config["DEFAULT"]["LINKER"],
                        *self.config["DEFAULT"]["PRELINKFLAGS"].split(),
                        *objects,
                        "-o",
                        program_name,
                        *self.config["DEFAULT"]["POSTLINKFLAGS"].split()]

            if self.config["DEFAULT"]["VERBOSE"].lower()=="yes":
                print("Linking: {}".format(" ".join(commands)))
            result = subprocess.run(commands, stderr=fd, stdout=fd)
            if result.returncode != SUCCESS:
                raise OSError(result.returncode, f"Error in linking file {program_name}", program_name) 
        
            # Set the Return value
            return_val = program_name

        except Exception as e:
            print(str(e))
        finally:
            # Close the file
            fd.close()

            # Replay the entire logfile
            self.recite_file(logfile)
            
        return return_val
    
    def run_text(self, text, fname, pargs=[]):
        self.save_code(text, fname)
        program=self.compile_code(fname)
        if program is not None:
            self.exec_program(program, pargs)
    
    def exec_program(self, program, pargs=[]):
        logfile=os.path.join(self.run_dir,"exec.log")
        with open(logfile,"w") as fd:
            commands=[self.config['DEFAULT']['MPIEXEC'], *self.config['DEFAULT']['MPIEXECFLAGS'].split(), program, *pargs]
            if self.config["DEFAULT"]["VERBOSE"].lower()=="yes":
                print("Running: {}".format(" ".join(commands)))
            t1 = time.perf_counter()
            subprocess.run(commands, stderr=fd, stdout=fd)
            t2 = time.perf_counter()
       
        # Open the logfile for writing
        self.recite_file(logfile)
        print(f"Execution of the program took {t2-t1:.4E} seconds")
    
    def save_code(self, text, fname):
        with open(fname, 'w') as fd:
            fd.write(text)

    def recite_file(self, logfile):
        with open(logfile, "r") as fd:
            for line in fd:
                print(line)


# The class MUST call this class decorator at creation time
@magics_class
class HPCMagics(Magics):

    def __init__(self, shell):
        super(HPCMagics, self).__init__(shell)
        # Argument parser
        self.parser=argparse.ArgumentParser()
        self.parser.add_argument('--sysargs', dest='sysargs', type=str, default="")
        self.parser.add_argument('--pargs', dest='pargs', type=str, default="")
        self.parser.add_argument('--verbose', dest='verbose', type=bool, default=True)

        # Configuration file for code compilation
        self.configfile=os.path.join(site.USER_BASE,"hpcmagic","hpcmagic.ini") 

        if not os.path.exists(self.configfile):
            self.configfile=os.path.join(sys.prefix, "hpcmagic", "hpcmagic.ini")

        print(f"Using configfile at {self.configfile}")

    @line_magic
    def lmagic(self, line):
        "my line magic"
        print("Full access to the main IPython object:", self.shell)
        print("Variables in the user namespace:", list(self.shell.user_ns.keys()))
        return line

    def run_cell(self, line, cell, ext):
        chelper=Code_Helper(self.configfile)
        # Parse the input command
        tokens_to_parse=line.split(";")
        tokens=[]
        for token in tokens_to_parse:
            sample_token=token.strip()
            if (sample_token!=""):
                tokens.append(sample_token)

        args=self.parser.parse_args(tokens)

        # Incorporate any system args into the configuration
        chelper.modify_config(args.sysargs)

        # Run post init tasks
        chelper.post_init_tasks()
        
        # Filename to save to
        fname=os.path.join(chelper.run_dir,"code"+ext)
            
        # Compile and run the text
        chelper.run_text(cell, fname, args.pargs.split(" "))

    @cell_magic
    def CPP(self, line, cell):
        ext=".cpp"
        self.run_cell(line, cell, ext)

    @cell_magic
    def C(self, line, cell):
        ext=".c"
        self.run_cell(line, cell, ext)
   
    @cell_magic
    def FORTRAN(self, line, cell):
        ext=".f90"
        self.run_cell(line, cell, ext)

    @line_cell_magic
    def lcmagic(self, line, cell=None):
        "Magic that works both as %lcmagic and as %%lcmagic"
        if cell is None:
            print("Called as line magic")
            return line
        else:
            print("Called as cell magic")
            return line, cell

# In order to actually use these magics, you must register them with a
# running IPython.

def load_ipython_extension(ipython):
    """
    Any module file that define a function named `load_ipython_extension`
    can be loaded via `%load_ext module.path` or be configured to be
    autoloaded by IPython at startup time.
    """
    # You can register the class itself without instantiating it.  IPython will
    # call the default constructor on it.
    hpcmagics = HPCMagics(ipython)
    ipython.register_magics(hpcmagics)
