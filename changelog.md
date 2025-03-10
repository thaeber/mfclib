<!-- insertion marker -->
<a name="v0.2.5"></a>

## [v0.2.5](https://github.com/thaeber/mfclib/compare/v0.2.4...v0.2.5) (2025-03-06)

### Bug Fixes

- Relaxed limits on dependency versions ([08718f8](https://github.com/thaeber/mfclib/commit/08718f83296d1924f6dc3b0cc28bfec55add3c9d))

<a name="v0.2.4"></a>

## [v0.2.4](https://github.com/thaeber/mfclib/compare/v0.2.3...v0.2.4) (2025-03-06)

### Bug Fixes

- Excluded autogenerated files from formatting by `black` and `pre-commit` ([4a79ac5](https://github.com/thaeber/mfclib/commit/4a79ac55b6519f5801fec1df1dbbb737faae1665))
- Failing test of MixtureGenerator due to floating point representation ([e2e7f63](https://github.com/thaeber/mfclib/commit/e2e7f63b5f9af3e401a38bde9329e0d999f4023a))
- Type checker issue on DataLoggingConfig ([9250304](https://github.com/thaeber/mfclib/commit/92503041c0a51b021be39690824e18167e0e105b))

### Features

- Updated MFC configuration file ([294779c](https://github.com/thaeber/mfclib/commit/294779c0d447be43f601a427724c8fbb3bdfdac6))
- Added grpcio[protobuf] as dependency ([e5740a3](https://github.com/thaeber/mfclib/commit/e5740a3e9ab091f8645426e2af9eef048ff1e617))
- MixtureGenerator model class (#8) ([d708937](https://github.com/thaeber/mfclib/commit/d70893752dddfeda38834b2617e06197a92da116))
- MFC descriptor class (#4) ([c032a1f](https://github.com/thaeber/mfclib/commit/c032a1fc758769511d24a6fd511f0e306dd7907c))

### Code Refactoring

- Mixture model class (#7) ([8ba937b](https://github.com/thaeber/mfclib/commit/8ba937b85ced93c7ad6a441b544b167a5e883aae))
- `mix` cli command (#6) ([701646d](https://github.com/thaeber/mfclib/commit/701646d3bbbe0c84798f653549d46816c3e364f1))
- Regroup python files in sub-modules models and cli (#5) ([aa43229](https://github.com/thaeber/mfclib/commit/aa4322974ea1dd12c2c9c58beb574948fbdb3640))

### Chore

- Updated mfc config ([d76bc7c](https://github.com/thaeber/mfclib/commit/d76bc7cab330a2e9b91aa3c02c38cefc54fad4b5))
- pre-commit run --all ([5645aef](https://github.com/thaeber/mfclib/commit/5645aefdea30af0471aa1aa0bde23fbaa498d7ac))
- Updated config yaml. ([493df4a](https://github.com/thaeber/mfclib/commit/493df4a85b158a01896017829becfb6e404462cb))

<a name="v0.2.3"></a>

## [v0.2.3](https://github.com/thaeber/mfclib/compare/v0.2.2...v0.2.3) (2024-11-28)

### Bug Fixes

- Incorrect parsing of units in PydanticQuantity ([4eb179d](https://github.com/thaeber/mfclib/commit/4eb179de2ae1439df1a995f1fa75f50142add764))

### Features

- Added Calibration class to hold and work with calibration data ([1c6384a](https://github.com/thaeber/mfclib/commit/1c6384a0445c18c18ca8c5307b86f147b8a10c0f))

### Code Refactoring

- Moved __version__ identifier to submodule version.py ([2e9a895](https://github.com/thaeber/mfclib/commit/2e9a895fac2afea7756a0ce1e9643ee419c8ca43))
- Use pint application registry by default and deprecate registration of custom units. ([e7cdac3](https://github.com/thaeber/mfclib/commit/e7cdac33f488065893184d2d69a891d7e9a1b3bd))

### Chore

- git-changelog -B patch ([cc75910](https://github.com/thaeber/mfclib/commit/cc7591081f470c75668ed5a057f1c010153a717d))
- Updating pyproject.toml ([2d2f651](https://github.com/thaeber/mfclib/commit/2d2f6510c847be050fa2d0728172384d6de977c0))
- Updated .ammonia mixture properties ([4c49fcb](https://github.com/thaeber/mfclib/commit/4c49fcb8573e92ebed0901dd39b7f4ace421f512))

### Tests

- Removed `unit_registry` pytest fixture ([7f3d84c](https://github.com/thaeber/mfclib/commit/7f3d84cf2c71ada29e91672a198260f9ae56bfb5))

<a name="v0.2.2"></a>

## [v0.2.2](https://github.com/thaeber/mfclib/compare/v0.2.1...v0.2.2) (2024-05-17)

### Features

- Introducing PydanticQuantity to use pint quantities with pydantic objects ([c847b00](https://github.com/thaeber/mfclib/commit/c847b0051750d9f5e872d2ce57a4d632117d9416))

### Chore

- Updated changelog.md ([edfecad](https://github.com/thaeber/mfclib/commit/edfecad1611b73d7001ad3f03574ccaaced91712))
- Running pre-commit with all files ([26ae330](https://github.com/thaeber/mfclib/commit/26ae3300030daba4fd2b765ce2b97368ac55ca4d))
- Added dev tools bumpy-my-version, git-changelog & pre-commit ([fd83516](https://github.com/thaeber/mfclib/commit/fd8351653b14d3c57853ccf2bc7436780b0c0d69))

<a name="v0.2.1"></a>

## [v0.2.1](https://github.com/thaeber/mfclib/compare/v0.2.0...v0.2.1) (2023-11-04)

<a name="v0.2.0"></a>

## [v0.2.0](https://github.com/thaeber/mfclib/compare/f6d2a2e5728e34d8992d8136416ab95c213a7b59...v0.2.0) (2023-08-16)

### Bug Fixes

- Missing return statement in ensure_mixture_type ([5cafe75](https://github.com/thaeber/mfclib/commit/5cafe757c2462d34ad242dba92d2831fdae20802))
- Resolved errors in the command line interface caused by the refactoring of the Mixture class ([4912cc9](https://github.com/thaeber/mfclib/commit/4912cc91c7d667ef00f282c572ad2ea84711e342))
- Removed poetry from environment.yaml ([c929e64](https://github.com/thaeber/mfclib/commit/c929e6452101c224a8b52e7e73ec130836a6eaf3))

### Code Refactoring

- Renaming configuration functions ([9a76fc3](https://github.com/thaeber/mfclib/commit/9a76fc313b87aa2cfbad8efcb7af4170d1ecd3e2))
- Restructured mfclib.config ([5f9f450](https://github.com/thaeber/mfclib/commit/5f9f4502620f437cd23e7632740255d5de33ec9a))
- Clean up dependencies ([3dd96ce](https://github.com/thaeber/mfclib/commit/3dd96ce0b5fe72e847c55b312f4209dd704332e4))
- Supply unit registry only via configuration to make the usage easier ([44676c2](https://github.com/thaeber/mfclib/commit/44676c2faf24a1fcd16e5cf9de5cef0a46899a3f))
- Make usage of unit registry explicit in calls to Mixture.__init__ ([0cf1179](https://github.com/thaeber/mfclib/commit/0cf117956d6710c572afce648bcbb061fdc246c2))

