# sleapGUI
GUI application that automates specified commands for SLEAP.

## Installation
This application uses the same Qt bindings as SLEAP, through the QtPy compatibility layer, i.e. must be run in the SLEAP conda environment.

1. Activate the SLEAP environment:
```conda activate sleap```
2. Install sleapGUI:
```pip install --no-deps git+https://github.com/khicken/sleapGUI.git```

## Usage
Simply run `sleapgui` in the environment to launch the application.

There are currently two types of analysis: `face` and `pupil`.

The default analysis is for `face`. For pupil analysis, run `sleapgui pupil`.

## Compatibility
| Platform | Python Version | SLEAP Version |
|----------|----------------|---------------|
| Windows  | 3.7 | 1.4.1 |
| MacOS  | 3.7 | 1.4.1 |
| Linux  | 3.7 | 1.4.1 |

## Contributing
Contributions are welcome! Please open an issue or submit a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
