# watney

[![PyPI - Version](https://img.shields.io/pypi/v/watney.svg)](https://pypi.org/project/watney)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/watney.svg)](https://pypi.org/project/watney)

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install watney
```

## License

`watney` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.


## Deployment

Build the container image using the included Containerfile.

```bash
podman build -t watney .
podman push watney quay.io/btweed/watney
```

Then, use the associated yaml to deploy to Openshift.