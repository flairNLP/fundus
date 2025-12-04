import os
import re
import tempfile
from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
from github import Github
from github.WorkflowRun import WorkflowRun
from tqdm import tqdm

load_dotenv()

# ---------- CONFIG ----------
__REPO__ = "flairNLP/fundus"
__WORKFLOW_NAME__ = "Publisher Coverage"
__ARTIFACT_NAME__ = "Publisher Coverage"
__TOKEN__ = os.getenv("GITHUB_TOKEN")  # needs to be a fine-grained token


# ----------------------------


def parse_arguments() -> Namespace:
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
        help=("the maximal number of artifacts to scan in descending order. (default 100)"),
    )

    arguments = parser.parse_args()

    return arguments


def parse_coverage_file(text: str) -> Optional[Dict[str, bool]]:
    """Extract lines like:
       ✔️ PASSED: 'NYTimes'
       ❌ FAILED: 'Guardian'
    Returns dict {publisher: True/False}
    """
    results = {}
    for line in text.splitlines():
        m = re.search(r"(PASSED|FAILED): '([^']+)'", line)
        if m:
            status = m.group(1) == "PASSED"
            name = m.group(2)
            results[name] = status

    # unfortunately we have to fall back to this really badly hard coded check to see if an action run through
    # the problem is that were only now (04.12.25) have a unique exit code, that's distinguishable from the
    # action just crashing. In the future we can replace this check and purely checking on the exit code
    if "Some publishers finished in a 'FAILED' state" not in text and "All publishers passed the tests" not in text:
        return None
    return results


def download_artifact_zip(run) -> Optional[str]:
    """Download the artifact ZIP and return text content of publisher_coverage.txt."""
    artifacts = run.get_artifacts()
    for a in artifacts:
        if a.name == __ARTIFACT_NAME__:
            zip_url = a.archive_download_url
            r = requests.get(zip_url, headers={"Authorization": f"token {__TOKEN__}"})
            if r.status_code != 200:
                return None

            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.write(r.content)
            tmp.close()

            import zipfile

            with zipfile.ZipFile(tmp.name) as z:
                for fname in z.namelist():
                    if fname.endswith(".txt"):
                        return z.read(fname).decode("utf-8")
    return None


def parse_run_time(run: WorkflowRun) -> datetime:
    return datetime.strptime(run.created_at.isoformat(), "%Y-%m-%dT%H:%M:%S%z")


def determine_timestamp(publisher: List[str], runs: List[WorkflowRun]) -> Dict[str, datetime]:
    publisher_history = {}  # {publisher_name: last_success}

    print("Scanning runs in descending date order...")

    current = set(publisher)

    with tqdm(total=len(runs)) as pbar:
        for run in runs:
            run_time = parse_run_time(run)

            pbar.set_description(f"Scanning run {run.id} from {run_time.date()}")

            txt = download_artifact_zip(run)

            pbar.update()

            if not txt:
                continue

            if not (parsed := parse_coverage_file(txt)):
                continue

            failed = {publisher for publisher, state in parsed.items() if state is False}

            if succeeded := (current - failed):
                for p in succeeded:
                    publisher_history[p] = run_time

            current &= failed

            if not current:
                break

        return publisher_history


if __name__ == "__main__":
    arguments = parse_arguments()

    if __TOKEN__ is None:
        raise RuntimeError("Set GITHUB_TOKEN environment variable.")

    gh = Github(__TOKEN__)
    repo = gh.get_repo(__REPO__)

    # 1. Find workflow ID
    workflows = repo.get_workflows()
    workflow_id = None
    for w in workflows:
        if w.name == __WORKFLOW_NAME__:
            workflow_id = w.id
            break

    if workflow_id is None:
        raise RuntimeError(f"Workflow '{__WORKFLOW_NAME__}' not found.")

    print(f"Found workflow ID: {workflow_id}")

    # 2. Retrieve workflow runs properly
    workflow = repo.get_workflow(workflow_id)
    runs = workflow.get_runs()

    if not runs:
        raise RuntimeError(f"No runs found for workflow '{__WORKFLOW_NAME__}'.")

    shift = 1 if runs[0].status in {"queued", "in_progress"} else 0

    sliced_runs: List[WorkflowRun]
    latest_run, sliced_runs = runs[0 + shift], list(
        runs[1 + shift : min(arguments.limit + 1, runs.totalCount - 1) + shift]
    )
    run_time = parse_run_time(latest_run)
    txt = download_artifact_zip(latest_run)
    if not txt:
        raise RuntimeError(f"Failed to download artifact '{__ARTIFACT_NAME__}' for latest run '{workflow_id}'.")

    if (parsed := parse_coverage_file(txt)) is None:
        raise RuntimeError(f"Couldn't parse latest coverage file for run {latest_run.id}")

    failed_publisher = [publisher for publisher, status in parse_coverage_file(txt).items() if not status]  # type: ignore[union-attr]

    print(f"Latest run on '{run_time}' with {len(failed_publisher)} failed publishers.")
    print(failed_publisher)

    publisher_history = determine_timestamp(failed_publisher, sliced_runs)

    max_length = max(len(key) for key in failed_publisher)
    print("\n====== Publisher Failure Timeline ======\n")
    print(f"{'Publisher':{max_length}} 'Last Success'")
    print("-" * 85)

    for pub, time in sorted(publisher_history.items(), key=lambda x: x[1], reverse=True):
        print(f"{pub:{max_length}} {time.date()}")

    for pub in set(failed_publisher) - set(publisher_history):
        print(f"{pub:{max_length}} UNKNOWN")
