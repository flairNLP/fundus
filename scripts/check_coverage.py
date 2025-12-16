import os
import re
import tempfile
import zipfile
from argparse import ArgumentParser, Namespace
from datetime import date, datetime
from pathlib import Path
from typing import IO, Dict, Iterator, List, Optional, Union

import requests
from dotenv import load_dotenv
from github import Auth, Github
from github.PaginatedList import PaginatedList
from github.WorkflowRun import WorkflowRun
from tqdm import tqdm

from fundus import __development_base_path__ as __root__
from fundus.logging import create_logger

load_dotenv()

logger = create_logger(__name__)

# ---------- CONFIG ----------
__REPO__ = "flairNLP/fundus"
__WORKFLOW_NAME__ = "Publisher Coverage"
__ARTIFACT_NAME__ = "Publisher Coverage"
__TOKEN__ = os.getenv("GITHUB_TOKEN")  # needs to be a fine-grained token, doesn't have to have permissions
__CACHE_DIR__ = __root__ / ".cache" / "run_artifacts"  # cache directory for artifact downloads
__VERBOSE__ = False


# ----------------------------


def parse_arguments() -> Namespace:
    """
    Parse command-line arguments.

    Returns:
        Namespace: Parsed arguments containing 'limit'.
    """

    parser = ArgumentParser(
        prog="check_coverage",
        description=(
            "Scan Publisher Coverage workflow artifacts to determine the most recent "
            "successful run for each currently failing publisher."
        ),
    )

    parser.add_argument(
        "-n",
        "--limit",
        default=100,
        type=int,
        help="the maximal number of artifacts to scan in descending order. (default 90)",
    )

    parser.add_argument(
        "--nocache",
        action="store_true",
        help="do not use cached artifacts",
    )

    parser.add_argument(
        "-p",
        "--cachedir",
        default=None,
        type=Path,
        help="the directory to use for caching artifacts",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="set verbosity",
    )

    arguments = parser.parse_args()

    return arguments


def parse_coverage_file(text: str) -> Optional[Dict[str, bool]]:
    """
    Extract publisher test results from the workflow artifact content.

    Lines should be in the format:
        ✔️ PASSED: 'NYTimes'
        ❌ FAILED: 'Guardian'

    Args:
        text (str): Content of the coverage file.

    Returns:
        Optional[Dict[str, bool]]: Mapping of publisher to success status, or None if file
        is malformed/unparsable.
    """
    results: Dict[str, bool] = {}
    for line in text.splitlines():
        m = re.search(r"(PASSED|FAILED): '([^']+)'", line)
        if m:
            status = m.group(1) == "PASSED"
            name = m.group(2)
            results[name] = status

    if "Some publishers finished in a 'FAILED' state" not in text and "All publishers passed the tests" not in text:
        return None

    return results


def download_artifact_zip(run: WorkflowRun, use_cache: bool = True) -> Optional[str]:
    """
    Download artifact ZIP for a workflow run and extract 'publisher_coverage.txt'.
    Uses local cache to avoid re-downloading artifacts if use_cache is True.

    Args:
        run (WorkflowRun): GitHub workflow run object.
        use_cache (bool): If False, ignore the cache and always download fresh.

    Returns:
        Optional[str]: Content of the coverage text file or None if download failed.
    """
    cache_path = os.path.join(__CACHE_DIR__, f"{run.id}.zip")

    def unzip(file: Union[str, IO[bytes]]) -> Optional[str]:
        with zipfile.ZipFile(file) as z:
            for fname in z.namelist():
                if fname.endswith(".txt"):
                    return z.read(fname).decode("utf-8")
        return None

    # Use cached file if it exists and caching is enabled
    if use_cache and os.path.exists(cache_path):
        return unzip(cache_path)

    # Download artifact
    artifacts = run.get_artifacts()
    for a in artifacts:
        if a.name == __ARTIFACT_NAME__:
            if a.expired:
                if __VERBOSE__:
                    tqdm.write(f"Artifact has expired")
                return None
            zip_url = a.archive_download_url
            r = requests.get(zip_url, headers={"Authorization": f"token {__TOKEN__}"})
            if r.status_code != 200:
                if __VERBOSE__:
                    tqdm.write(f"Couldn't download {zip_url!r}: {r.text}")
                return None

            # Save to cache if enabled
            if use_cache:
                with open(cache_path, "wb") as f:
                    f.write(r.content)
                zip_source = cache_path
            else:
                # Write to a temporary file if not caching
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.write(r.content)
                tmp.close()
                zip_source = tmp.name

            return unzip(zip_source)

    return None


def parse_run_time(run: WorkflowRun) -> datetime:
    """
    Convert GitHub workflow run creation time to a datetime object.

    Args:
        run (WorkflowRun): GitHub workflow run object.

    Returns:
        datetime: Datetime of run creation.
    """
    return datetime.strptime(run.created_at.isoformat(), "%Y-%m-%dT%H:%M:%S%z")


def determine_timestamp(publishers: List[str], runs: List[WorkflowRun], use_cache: bool = True) -> Dict[str, datetime]:
    """
    Determine the last successful run timestamp for each publisher.

    Args:
        publishers (List[str]): List of currently failing publishers.
        runs (List[WorkflowRun]): Workflow runs to scan in descending order.
        use_cache (bool): If False, ignore the cache and always download fresh.

    Returns:
        Dict[str, datetime]: Mapping of publisher name to datetime of last success.
    """
    publisher_history: Dict[str, datetime] = {}
    print("Scanning runs in descending date order...")

    current = set(publishers)

    with tqdm(total=len(runs)) as pbar:
        for run in runs:
            run_time = parse_run_time(run)
            pbar.set_description(f"Scanning run {run.id} from {run_time.date()}")

            txt = download_artifact_zip(run, use_cache=use_cache)
            pbar.update()

            if not txt:
                if __VERBOSE__:
                    tqdm.write(f"Couldn't download artifact for {run.id!r}, created at {run.created_at.date()}")
                continue

            if not (parsed := parse_coverage_file(txt)):
                if __VERBOSE__:
                    tqdm.write(f"Couldn't parse artifact for {run.id!r}, created at {run.created_at.date()}")
                continue

            failed = {publisher for publisher, state in parsed.items() if not state}

            if succeeded := (current - failed):
                for p in succeeded:
                    publisher_history[p] = run_time

            current &= failed

            if not current:
                break

    return publisher_history


def get_latest_runs_per_day(runs: PaginatedList[WorkflowRun]) -> Iterator[WorkflowRun]:
    """Get latest run per day given a paginated list of workflow runs.

    Args:
        runs: workflow runs to filter.

    Returns:
        Latest run per day.
    """
    current_date: Optional[date] = None
    for run in runs:
        if current_date and run.created_at.date() == current_date:
            continue
        current_date = run.created_at.date()
        yield run


def main() -> None:
    """
    Main entry point: parse arguments, fetch workflow runs, analyze artifacts,
    and print a timeline of last successful runs for failing publishers.
    """
    global __CACHE_DIR__, __VERBOSE__

    arguments = parse_arguments()

    if arguments.verbose:
        __VERBOSE__ = arguments.verbose

    if arguments.cachedir is not None:
        __CACHE_DIR__ = arguments.cachedir

    # Ensure cache directory exists
    if not arguments.nocache:
        __CACHE_DIR__.mkdir(parents=True, exist_ok=True)

    if __TOKEN__ is None:
        raise RuntimeError("Set GITHUB_TOKEN environment variable.")

    gh = Github(auth=Auth.Token(__TOKEN__))
    repo = gh.get_repo(__REPO__)

    # 1. Find workflow ID
    workflows = repo.get_workflows()
    workflow_id: Optional[int] = None
    for w in workflows:
        if w.name == __WORKFLOW_NAME__:
            workflow_id = w.id
            break

    if workflow_id is None:
        raise RuntimeError(f"Workflow '{__WORKFLOW_NAME__}' not found.")

    print(f"Found workflow ID: {workflow_id}")

    # 2. Retrieve workflow runs; in order to address reruns, we filter for the latest run per day
    workflow = repo.get_workflow(workflow_id)
    runs = []
    for run in get_latest_runs_per_day(workflow.get_runs()):
        if run.status not in {"queued", "in_progress"}:
            runs.append(run)
            if len(runs) == arguments.limit:
                break

    if not runs:
        raise RuntimeError(f"No runs found for workflow '{__WORKFLOW_NAME__}'.")

    latest_run, sliced_runs = runs[0], runs[1:]

    run_time = parse_run_time(latest_run)
    txt = download_artifact_zip(latest_run, use_cache=not arguments.nocache)
    if not txt:
        raise RuntimeError(f"Failed to download artifact '{__ARTIFACT_NAME__}' for latest run '{workflow_id}'.")

    if (parsed := parse_coverage_file(txt)) is None:
        raise RuntimeError(f"Couldn't parse latest coverage file for run {latest_run.id}")

    failed_publishers = [publisher for publisher, status in parsed.items() if not status]  # type: ignore[union-attr]

    print(f"Latest run on '{run_time}' with {len(failed_publishers)} failed publishers.")
    print(failed_publishers)

    publisher_history = determine_timestamp(failed_publishers, sliced_runs, use_cache=not arguments.nocache)

    max_length = max(len(key) for key in failed_publishers) if failed_publishers else 0
    print("\n====== Publisher Failure Timeline ======\n")
    print(f"{'Publisher':{max_length}} 'Last Success'")
    print("-" * 85)

    for pub, time in sorted(publisher_history.items(), key=lambda x: x[1], reverse=True):
        print(f"{pub:{max_length}} {time.date()}")

    for pub in set(failed_publishers) - set(publisher_history):
        print(f"{pub:{max_length}} UNKNOWN")


if __name__ == "__main__":
    main()
