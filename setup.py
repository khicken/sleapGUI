from setuptools import setup, find_packages

setup(
    name='sleapgui',
    version='0.1.0a0',      # PEP 440 versioning
    author='Kaleb Kim',
    author_email='mail@kalebkim.com',
    description='GUI application that automates specified commands for SLEAP',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/khicken/sleapGUI',
    packages=find_packages(),
    install_requires=[
        'numpy>=1.26.0,<2',
        'opencv-python>=4.8.1,<5',
        'PyQt6>=6.6.0,<7',
        'PyQt6-Qt6>=6.6.0,<7',
        'PyQt6-sip>=13.5.0,<14'
    ],
    entry_points={
        "console_scripts": [
            "sleapgui=sleapgui.main:main",
        ],
    },
    package_data={
        'mediagui': ['openh264-1.8.0-win64.dll'],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    keywords="sleap, gui, video analysis",
    python_requires='>=3.7',
)