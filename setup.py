from setuptools import setup

setup(
    name='waterbg',
    version='1.0.1',
    py_modules=['waterbg'],
    license='MIT',
    author='Szabolcs Dombi',
    author_email='cprogrammer1994@gmail.com',
    url='https://github.com/szabolcsdombi/pyodide-water-background',
    project_urls={
        'Source': 'https://github.com/szabolcsdombi/pyodide-water-background',
    },
    classifiers=['Topic :: Multimedia :: Graphics :: 3D Rendering'],
    keywords=['pyodide', 'console', 'background'],
    install_requires=['zengl'],
)
