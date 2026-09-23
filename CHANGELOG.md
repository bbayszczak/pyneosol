# Changelog

## [1.1.0](https://github.com/bbayszczak/pyneosol/compare/v1.0.0...v1.1.0) (2026-09-23)


### Features

* add unregister action ([#27](https://github.com/bbayszczak/pyneosol/issues/27)) ([e7e8c44](https://github.com/bbayszczak/pyneosol/commit/e7e8c446e78c3981a69c954cd6d468fe925e401f))

## [1.0.0](https://github.com/bbayszczak/pyneosol/compare/v0.4.2...v1.0.0) (2026-09-22)


### ⚠ BREAKING CHANGES

* every method that talks to the device is a coroutine and must be awaited: Dongle.open(), execute(), ping(), info(), channels(), channel(), used_channels(), transmit_power(), send(), open_shutter(), close_shutter(), stop(), favourite(), register(), close(), and find_ports(). Dongle implements __aenter__/__aexit__ instead of __enter__/__exit__, so `with Dongle.open()` becomes `async with Dongle.connect()`. The Transport interface replaces read_available() with an awaitable readline(), and write() and close() are coroutines; SerialTransport is built with `await SerialTransport.open(port)` rather than its constructor.

### Features

* drive the dongle with asyncio ([#24](https://github.com/bbayszczak/pyneosol/issues/24)) ([4037644](https://github.com/bbayszczak/pyneosol/commit/40376447836c3c88c542454a5a17528f464374a4))


### Bug Fixes

* **logging:** mask the serial number a port path carries ([#25](https://github.com/bbayszczak/pyneosol/issues/25)) ([2d3b023](https://github.com/bbayszczak/pyneosol/commit/2d3b023a55d6c2eab90488094208cd3cfa00471c))

## [0.4.2](https://github.com/bbayszczak/pyneosol/compare/v0.4.1...v0.4.2) (2026-09-20)


### Bug Fixes

* **dongle:** redact secrets in outgoing commands too ([#16](https://github.com/bbayszczak/pyneosol/issues/16)) ([cccb56f](https://github.com/bbayszczak/pyneosol/commit/cccb56f8f8e290f2e722b1d6060502fe66669283))
* **dongle:** stop reporting an empty AT$CP? answer as a timeout ([#13](https://github.com/bbayszczak/pyneosol/issues/13)) ([8f3abeb](https://github.com/bbayszczak/pyneosol/commit/8f3abebcd29534a570c5909f63f214553ac74763))


### Documentation

* **readme:** install from PyPI instead of the git repository ([#23](https://github.com/bbayszczak/pyneosol/issues/23)) ([73b6be8](https://github.com/bbayszczak/pyneosol/commit/73b6be807df7a08b8d2ef54b6ceed4d2afa7f5a0))

## [0.4.1](https://github.com/bbayszczak/pyneosol/compare/v0.4.0...v0.4.1) (2026-09-20)


### Bug Fixes

* **ci:** guard the branch name against an absent release pull request ([#20](https://github.com/bbayszczak/pyneosol/issues/20)) ([42f7195](https://github.com/bbayszczak/pyneosol/commit/42f7195db34eb8c7d9e3a0b9b4f1bf533e026598))

## [0.4.0](https://github.com/bbayszczak/pyneosol/compare/v0.3.0...v0.4.0) (2026-09-20)


### Features

* log the AT dialogue without leaking secrets ([#11](https://github.com/bbayszczak/pyneosol/issues/11)) ([d3ad93a](https://github.com/bbayszczak/pyneosol/commit/d3ad93a45dab04358907548ee191f0a09bab7246))


### Bug Fixes

* **ci:** create the uv.lock sync commit through the GitHub API ([#19](https://github.com/bbayszczak/pyneosol/issues/19)) ([b91eee0](https://github.com/bbayszczak/pyneosol/commit/b91eee0e8dc7b798fa2ab0bc7c0cc6e571439a07))
* **dongle:** wrap a non-numeric transmit power in ProtocolError ([#12](https://github.com/bbayszczak/pyneosol/issues/12)) ([4e560cd](https://github.com/bbayszczak/pyneosol/commit/4e560cd32a2a0d54f7e1bb882913d516121d3871))


### Documentation

* **readme:** add photos of the validated dongle ([#15](https://github.com/bbayszczak/pyneosol/issues/15)) ([e405433](https://github.com/bbayszczak/pyneosol/commit/e4054337294fab6407f91b32e9b8706f64722636))

## [0.3.0](https://github.com/bbayszczak/pyneosol/compare/v0.2.0...v0.3.0) (2026-09-18)


### Features

* add the dongle driver ([f04cddc](https://github.com/bbayszczak/pyneosol/commit/f04cddc815d5152e1e92584fdc0a3a643eba9f16))
* update README ([2d2048e](https://github.com/bbayszczak/pyneosol/commit/2d2048e4e55e708816482b470eba46e43d4cf30e))


### Documentation

* add AT protocol specification for the Neosol 868 dongle ([d02aa2b](https://github.com/bbayszczak/pyneosol/commit/d02aa2b0a16c19c186464910927a5c6eac80f30c))
* add project disclaimer and hardware identification ([0c750c9](https://github.com/bbayszczak/pyneosol/commit/0c750c93b185686716f5d07197cfa41ea7dbda77))
* add USB identification and the two rejection forms ([c4c9a8b](https://github.com/bbayszczak/pyneosol/commit/c4c9a8b7c3eb879a1298fdeebbf2be043af06816))
* confirm the favourite position action and how it is recorded ([4748b5f](https://github.com/bbayszczak/pyneosol/commit/4748b5fe97a12d94652b056434daac40fef2750b))
* document installation, usage and development ([f3e8039](https://github.com/bbayszczak/pyneosol/commit/f3e8039bc5adad5eb631a8ff9640673a2aaa798c))
* explain how to run the demonstration script ([7d122af](https://github.com/bbayszczak/pyneosol/commit/7d122af3c0d996c2964bc9ab3287444e7d128ed9))
* frame the project as compatible with the hardware, not derived from it ([14e4444](https://github.com/bbayszczak/pyneosol/commit/14e444451046bad2235de4c6ac7664b996c7d66e))
* record that the dongle has no usable radio reception ([499491a](https://github.com/bbayszczak/pyneosol/commit/499491a38093c48b44d150c84f32f2886cbbe937))
* use the exact dongle reference and drop the untested one ([c989827](https://github.com/bbayszczak/pyneosol/commit/c98982794ae318158f3c388a073f00cc76d32022))

## [0.2.0](https://github.com/bbayszczak/pyneosol/compare/v0.1.0...v0.2.0) (2026-09-18)


### Features

* add the dongle driver ([e41e284](https://github.com/bbayszczak/pyneosol/commit/e41e284fec4763a2b4252db31e51581023371395))
* update README ([534c10f](https://github.com/bbayszczak/pyneosol/commit/534c10f7ffe93fa8806535decdc3603bf0ce225f))


### Documentation

* add AT protocol specification for the Neosol 868 dongle ([e8e2f36](https://github.com/bbayszczak/pyneosol/commit/e8e2f36c333166339f42695901d0df51e340bc13))
* add project disclaimer and hardware identification ([720a5f6](https://github.com/bbayszczak/pyneosol/commit/720a5f61b0190f59e7662944e2c688dab253fb41))
* add USB identification and the two rejection forms ([997bed3](https://github.com/bbayszczak/pyneosol/commit/997bed39ac82149fc144e32007edc323f8a2991d))
* confirm the favourite position action and how it is recorded ([ae09232](https://github.com/bbayszczak/pyneosol/commit/ae09232829c8fcc37b81e70bf8fa2a3a7a772790))
* document installation, usage and development ([569b1e0](https://github.com/bbayszczak/pyneosol/commit/569b1e02481880294482f0644704dd0ec5d7220e))
* explain how to run the demonstration script ([44e8deb](https://github.com/bbayszczak/pyneosol/commit/44e8debd9e6433f45ec3574c0516adbbe3da9e4f))
* frame the project as compatible with the hardware, not derived from it ([3f6cd9a](https://github.com/bbayszczak/pyneosol/commit/3f6cd9a1901d976536548137dc3c605670cff1af))
* record that the dongle has no usable radio reception ([9aa1a1f](https://github.com/bbayszczak/pyneosol/commit/9aa1a1fcb9197a9f503ffc04addd859ad32e4967))
* use the exact dongle reference and drop the untested one ([49c2b60](https://github.com/bbayszczak/pyneosol/commit/49c2b60521a9e53afc8e96638f0a4e3bbdebda0f))
