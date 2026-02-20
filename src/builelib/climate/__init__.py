import os

# 気象データディレクトリの絶対パス（このファイルからの相対位置で解決）
CLIMATEDATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "climatedata") + "/"

from .climate import *
