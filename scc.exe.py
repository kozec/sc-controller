#!/c/Python27/python
"""
Script that integrates everything SCC can do in one executable.
Created so scc-* stuff doesn't polute /usr/bin.
"""

import sys
sys.path.insert(0, ".")
import scc.platform.windows.override_paths

from scc.scripts import main

if __name__ == '__main__':
	main()
