from setuptools import setup, find_packages

setup(name="client_messenger",
      version="0.0.1",
      description="messendger_client",
      author="MadEngine",
      author_email="scorpio-84@mail.ru",
      packages=find_packages(),
      install_requires=['PyQt6', 'sqlalchemy']
      )
