from setuptools import setup
import pymon

with open('README.md', 'r', encoding='utf-8') as fd:
  setup(
      name='pymon',
      version=pymon.__version__,
      author='chengscott',
      maintainer='chengscott',
      description=pymon.__doc__,
      long_description=fd.read(),
      long_description_content_type='text/markdown',
      url='https://github.com/chengscott/pymon',
      license='BSD',
      packages=['pymon'],
      entry_points={
          'console_scripts': ['pymon = pymon:run_main'],
      },
      classifiers=[
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
      ],
  )
