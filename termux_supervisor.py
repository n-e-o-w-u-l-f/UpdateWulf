"""Legacy compatibility entry point: replace this process with UpdateWulf."""
import argparse
import os
import sys
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',required=True,type=Path)
    ap.add_argument('--state',required=True,type=Path)
    args=ap.parse_args()
    script=Path(__file__).with_name('pc_mesh.py')
    os.execv(sys.executable,[sys.executable,str(script),'daemon','--config',str(args.config),'--state',str(args.state)])


if __name__=='__main__':
    main()
