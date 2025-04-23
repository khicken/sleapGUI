# sleapGUI
GUI application that automates specified commands for SLEAP.

## Installation
This application uses the same Qt bindings as SLEAP, through the QtPy compatibility layer, i.e. must be run in the SLEAP conda environment.

1. Activate the SLEAP environment:
```conda activate sleap```
2. Install sleapGUI:
<pre>
<code>pip install --no-deps git+https://github.com/khicken/sleapGUI.git</code>
</pre>
<button onclick="navigator.clipboard.writeText('pip install --no-deps git+https://github.com/khicken/sleapGUI.git')"></button>

- Make sure that [Git](https://git-scm.com/downloads) is downloaded to your computer.

_Note: if updating, run:_
<pre>
<code>pip uninstall -y sleapgui</code>
</pre>
<button onclick="navigator.clipboard.writeText('pip uninstall -y sleapgui')"></button>

_Then rerun command 2_


## Usage
<p>Simply run:</p>

<pre>
<code>sleapgui</code>
</pre>
<button onclick="navigator.clipboard.writeText('sleapgui')"></button>

<p>There are currently two types of analysis: <code>face</code> and <code>pupil</code>.</p>

<ul>
  <li><code>face</code> uses 12 pose estimation points: 4 for the Eyelids, 2 for the Nose, 2 for the Mouth, and 4 for the Whiskers.<br/>
    <img src="./assets/face_picture.png" alt="face picture is here" width="400"/>
  </li>
  <li><code>pupil</code> uses 4 pose estimation points: Top, Bottom, Right, and Left.<br/>
    <img src="./assets/pupil_image.png" alt="pupil picture is here" width="400"/>
  </li>
</ul>

<p>The default analysis is for <code>face</code>. For pupil analysis, run:</p>

<pre>
<code>sleapgui pupil</code>
</pre>
<button onclick="navigator.clipboard.writeText('sleapgui pupil')"></button>

<p><code>sleapgui face</code> works in the same manner as <code>sleapgui</code>. To explicitly use face analysis, run:</p>

<pre>
<code>sleapgui face</code>
</pre>
<button onclick="navigator.clipboard.writeText('sleapgui face')"></button>


## Compatibility
| Platform | Python Version | SLEAP Version |
|----------|----------------|---------------|
| Windows  | 3.7 | 1.4.1 |
| MacOS  | 3.7 | 1.4.1 |
| Linux  | 3.7 | 1.4.1 |

The GUIs works well when you analyze multiple videos.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
