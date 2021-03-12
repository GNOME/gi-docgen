import sys
from .gidocmain import GIDocGenApp
def main():
    """Main entry point. Instantiates the GIDocGen application and runs it.
    """
    if sys.version_info < (3, 6): # pragma: no cover
        print('GIDocGen requires Python >= 3.6, but you have version ' + sys.version_info)
        print('Please update your environment to use GIDocGen.')
        return 1

    return GIDocGenApp().run(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())