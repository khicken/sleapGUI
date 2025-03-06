from setuptools import setup, find_packages

setup(
    name='sleapgui',
    version='0.1.0',      # PEP 440 versioning
    author='Kaleb Kim',
    author_email='mail@kalebkim.com',
    description='GUI application that automates specified commands for SLEAP',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/khicken/sleapGUI',
    packages=find_packages(),
    install_requires=[
        'PyQt5>=5.12.3',
        'sleap',
        'opencv-python',
    ],
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