from distutils.core import setup
from Cython.Build import cythonize
import numpy

setup(
    ext_modules=cythonize("*.pyx",  compiler_directives={'language_level': "3"}), requires=['Cython', 'numpy',
                                                                                                      'scipy'
                                                                                                      ],
    include_dirs=[numpy.get_include()])
