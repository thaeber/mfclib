<!-- insertion marker -->
<a name="v0.2.2"></a>

## [v0.2.2](https://github.com/thaeber/mfclib/compare/v0.2.1...v0.2.2) (2024-05-17)

### Features

- Introducing PydanticQuantity to use pint quantities with pydantic objects ([c847b00](https://github.com/thaeber/mfclib/commit/c847b0051750d9f5e872d2ce57a4d632117d9416))

### Chore

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

