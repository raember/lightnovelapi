from os.path import abspath, dirname

from spoofbot.util import clean_all_in

clean_all_in(dirname(abspath(__file__)))
