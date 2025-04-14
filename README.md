# sleapGUI
GUI application that automates specified commands for SLEAP.

## Installation
This application uses the same Qt bindings as SLEAP, through the QtPy compatibility layer, i.e. must be run in the SLEAP conda environment.

1. Activate the SLEAP environment:
```conda activate sleap```
2. Install sleapGUI:
```pip install --no-deps git+https://github.com/khicken/sleapGUI.git```
- Make sure that [Git](https://git-scm.com/downloads) is downloaded to your computer.

_Note: if updating, run ```pip uninstall -y sleapgui``` then command 2)_

## Usage
Simply run `sleapgui` in the environment to launch the application.

There are currently two types of analysis: `face` and `pupil`.
- `face` uses 12 pose estimation points: 4 for the Eyelids, 2 for the Nose, 2 for the Mouth, and 4 for the Whiskers.  
  <img src="./assets/face_picture.png" alt="face picture is here" width="400"/>
- `pupil` uses 4 pose estimation points: Top, Bottom, Right, and Left.  
  <img src="./assets/pupil_image.png" alt="pupil picture is here" width="400"/>


  
The default analysis is for `face`. For pupil analysis, run ```sleapgui pupil```.

```sleapgui face``` works in the same manner as ```sleapgui```.

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
