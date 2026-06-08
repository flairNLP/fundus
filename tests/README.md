# Test suite

A quick orientation for contributors. The suite is plain `pytest`; everything below is
convention, not magic.

## Running

```bash
python -m pytest                 # full suite
python -m pytest -m "not integration"   # fast inner loop — skip the slow tests
python -m pytest tests/scraping/pipeline/source/test_web.py   # one module
```

Note `pyproject.toml` sets `filterwarnings = ["error"]`: any warning emitted during a test
fails it.

## Layout — mirror the source tree

A test's **location** mirrors the package it covers. The test for
`src/fundus/<path>/<module>.py` lives at `tests/<path>/test_<module>.py`, so "where's the
test for `web.py`?" has exactly one answer.

```
tests/
├── conftest.py            # auto-loads fixture_*.py as plugins; autouse __EVENTS__ reset
├── utility.py             # shared helpers, imported as `tests.utility`
├── exceptions.py          #   and `tests.exceptions`
├── fixtures/              # builders, fakes, and @pytest.fixture wrappers (see below)
├── resources/             # recorded HTML, parser test data, frozen snapshots
├── parser/                # mirrors src/fundus/parser/
├── publishers/            # mirrors src/fundus/publishers/
├── scraping/              # mirrors src/fundus/scraping/  (pipeline/, crawler/, ...)
└── utils/                 # mirrors src/fundus/utils/
```

Every directory under `tests/` except `fixtures/` has an `__init__.py`, so same-named modules
in different packages — `scraping/crawler/test_web.py` vs.
`scraping/pipeline/source/test_web.py` — get distinct dotted names and don't collide.
(`fixtures/` is reached through the `fixture_*` plugin glob, not as a package, so it needs
none.)

**Location is by subject, never by speed.** A file's speed class drifts as it grows; the
module it tests does not. Cost/scope rides on **markers**, not directories (see below). We
deliberately rejected a `unit/component/integration/` directory split — it would tear
cohesive single-module files in half and add a permanent "which bucket?" tax for a benefit
the marker already delivers.

## Markers

Only one marker today, defined in `pyproject.toml`:

- **`integration`** — slow, multi-component tests with mocked I/O (may spawn threads or
  processes), e.g. `scraping/crawler/test_integration.py`. Select with `-m integration` or
  skip with `-m "not integration"`.

## Test data helpers: builders vs. fixtures vs. fakes vs. doubles

All shared test-data machinery lives in `tests/fixtures/builders.py`, where **the prefix tells
you what you get back**:

- **`make_*`** → a **real** domain object (`make_publisher`, `make_html`, `make_article`, ...).
- **`stub_*`** → a hand-rolled **stub** standing in for a real type (`stub_publisher`).
- **`mock_*`** → a **`MagicMock`** for a collaborator that isn't worth (or can't be) built real
  (`mock_response`, `mock_robots`).

Reach for them in this order:

**Builders (`make_*`)** — the default way to construct a domain object. One keyword-only
builder per type, each with sensible defaults. Builders nest, so a test about one layer
needn't know how to assemble the layers beneath it (`make_article` → `make_html` →
`make_source_info`). For a non-default value, compose at the call site so the object graph
stays visible:

```python
make_article(html=make_html(requested_url="...", publisher="pub_a"))
```

Don't add caller-specific shortcut kwargs to the global builders; if one file repeats the
same composition many times *and* it hurts readability, add a small local helper in that file.

**Fixtures (`fixture_*.py`)** — thin `@pytest.fixture` wrappers, mostly default no-arg
builder calls, for inject-by-name convenience (`publisher`, `parser_proxy_with_version`, the
publisher-group fixtures, `patched_web_session_handler`, ...). Use a fixture when the
constructed object is ceremony the test never inspects; construct inline (via a builder)
when the test asserts on the *specific values you put in*.

**Fakes (`fakes.py`)** — behavior-correct simplified subclasses of production classes
(e.g. `FakeCrawler`) for tests that need a real-ish object, not a stand-in.

**Doubles (`stub_*` / `mock_*`)** — the fallback when you can't (or needn't) use a real or
fake object. Default to a hand-rolled **`stub_*`**; reach for **`mock_*`** (`MagicMock`) only
when the stub can't do the job:

- **`stub_*`** — a small hand-rolled class. Clearer about its interface, picklable, and honest
  under `isinstance`. Use it for data-shaped collaborators a test just threads through
  (`stub_publisher`: scraping tests that carry a publisher without exercising the real one).
- **`mock_*`** — a `MagicMock`. Use it only when the test needs call-recording
  (`mock.foo.assert_called_with(...)`), the real surface is wide and unpredictable
  (`mock_response` → `curl_cffi.Response`), or the collaborator is behavioral rather than
  data-shaped (`mock_robots` → `Robots`, with its `can_fetch` / `crawl_delay`).

> **Plugin rule:** `conftest.py` auto-registers every `tests/fixtures/fixture_*.py` as a
> pytest plugin, and plugin modules must contain **only** `@pytest.fixture` callables. Bare
> helper functions and classes belong in non-plugin modules (`builders.py`, `fakes.py`).
> Mixing the two trips pytest's assertion-rewrite ordering.

## A couple of conventions worth knowing

- **Assert behavior, not structure.** Avoid `isinstance`/type/shape assertions — a test that
  still passes with the feature ripped out isn't testing the feature.
- **`xfail` pins live bugs.** When the bug is fixed, remove the `xfail` rather than the test.
- **`__EVENTS__` is process-global** cancellation state. `conftest.py` has an autouse fixture
  (`_reset_events_registry`) that calls `__EVENTS__.reset()` after every test, so tests may
  exercise the registry freely without leaking into the next one.