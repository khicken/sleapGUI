from setuptools import setup, find_packages
import importlib.util

# Check if qtpy is already installed
qtpy_installed = importlib.util.find_spec("qtpy") is not None

# Base dependencies
install_requires = [
    'sleap',
    'opencv-python',
]

# Add qtpy only if it's not already installed
if not qtpy_installed:
    install_requires.append('qtpy')

setup(
    name='sleapgui',
    version='0.1.1',
    author='Kaleb Kim',
    author_email='mail@kalebkim.com',
    description='GUI application that automates specified commands for SLEAP',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/khicken/sleapGUI',
    packages=find_packages(),
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "sleapgui=sleapgui.main:main",
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    keywords="sleap, gui, video analysis",
    python_requires='>=3.7',
)