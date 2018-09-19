from setuptools import setup
import arzela

with open('README.md', 'r', encoding='utf-8') as fd:
  setup(
      name='arzela',
      version=arzela.__version__,
      author='chengscott',
      maintainer='chengscott',
      description=arzela.__doc__,
      long_description=fd.read(),
      long_description_content_type='text/markdown',
      url='https://github.com/chengscott/arzela',
      license='BSD',
      packages=['arzela'],
      entry_points={
          'console_scripts': ['arzela = arzela:run_main'],
      },
      install_requires=[
          'zmq',
          'requests',
      ],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Topic :: System :: Clustering',
          'Topic :: System :: Monitoring',
      ],
  )
