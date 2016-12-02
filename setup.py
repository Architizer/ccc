from setuptools import setup

setup(name='ccc',
      version='0.1',
      description='Fetch pages from commoncrawl',
      url='http://github.com/archtizer/ccc',
      author='Baldur Gudbjornsson',
      author_email='baldur@architizer.com',
      include_package_data=True,
      license='MIT',
      packages=['ccc'],
      scripts=['bin/ccc'],
      zip_safe=False)
