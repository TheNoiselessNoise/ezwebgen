import argparse
from src.ezwebgen_objects import *

parser = argparse.ArgumentParser(epilog="by @TheNoiselessNoise", description="""
EzWebGenerator - A simple static website generator
""")
parser.add_argument("-c", "--config", help="path to config file", required=True)
parser.add_argument("-o", "--output", help="path to output (.html)", required=True)
parser.add_argument("--force", help="force overwrite of output file", action="store_true")
args = parser.parse_args()

def main():
    outpath = args.output

    if os.path.isdir(outpath):
        print(f"Can't use directory as output: {outpath}", file=sys.stderr)
        exit(1)

    if os.path.exists(outpath):
        print(f"Output file already exists: {outpath}", file=sys.stderr)
        if not args.force:
            print("Use --force to overwrite", file=sys.stderr)
            exit(1)
        else:
            print("Overwriting...", file=sys.stderr)

    if not os.path.exists(outpath):
        os.makedirs(outpath)

    toml = TomlWrapper(args.config)
    ezwebgen = EzWebGenerator(toml)
    ezwebgen.generate(outpath)

if __name__ == "__main__":
    if not len(sys.argv[1:]):
        parser.print_help()
        exit(1)

    main()
