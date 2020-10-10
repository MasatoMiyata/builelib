from setuptools import setup, find_packages

with open("README.md", "r") as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='builelib',
    version='0.1.0',
    description='builelib: Building Energy-modeling Library',
    author='Masato Miyata',
    author_email='builelib@gmail.com',
    url='https://github.com/MasatoMiyata/builelib',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    package_data={'builelib': ['inputdata/*', 'database/*', 'climatedata/*']},
    include_package_data=True,
    python_requires='>=3.7',
)
