from setuptools import setup, find_packages

setup(name="server_messenger",
      version="0.0.1",
      description="messenger_server",
      author="MadEngine",
      author_email="scorpio-84@mail.ru",
      packages=find_packages(),
      install_requires=['PyQt6', 'sqlalchemy']
      )
