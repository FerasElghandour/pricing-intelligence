"""Offline example using the public implementation; see README for evidence scope."""
import sys,json,pathlib,os
repo=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repo));sys.path.insert(0,str(repo/'src'));os.chdir(repo)
import numpy as np
from loop import run_one_sku
history=run_one_sku(10.,20.,-.5,-2.5,np.random.default_rng(42),rounds=8)
print(json.dumps({"fixture":"synthetic 8-round market, no historical benchmark","first":history.iloc[0].to_dict(),"last":history.iloc[-1].to_dict()}))
