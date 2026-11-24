import argparse
import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("gh_pr_watch.py")
MODULE_SPEC = importlib.util.spec_from_file_location("gh_pr_watch", MODULE_PATH)
gh_pr_watch = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC.loader is not None
MODULE_SPEC.loader.exec_module(gh_pr_watch)


def sample_pr():
    return {
        "number": 123,
        "url": "https://github.com/openai/codex/pull/123",
        "repo": "openai/codex",
        "head_sha": "abc123",
        "base_sha": "base123",
        "head_branch": "feature",
        "state": "OPEN",
        "merged": False,
        "closed": False,
        "mergeable": "MERGEABLE",
        "merge_state_status": "CLEAN",
        "review_decision": "",
    }


def sample_checks(**overrides):
    checks = {
        "pending_count": 0,
        "failed_count": 0,
        "passed_count": 12,
        "all_terminal": True,
    }
    checks.update(overrides)
    return checks


def test_collect_snapshot_fetches_review_items_before_ci(monkeypatch, tmp_path):
    call_order = []
    pr = sample_pr()

    monkeypatch.setattr(gh_pr_watch, "resolve_pr", lambda *args, **kwargs: pr)
    monkeypatch.setattr(gh_pr_watch, "load_state", lambda path: ({}, True))
    monkeypatch.setattr(
        gh_pr_watch,
        "get_authenticated_login",
        lambda: call_order.append("auth") or "octocat",
    )
    monkeypatch.setattr(
        gh_pr_watch,
        "fetch_new_review_items",
        lambda *args, **kwargs: call_order.append("review") or [],
    )
    monkeypatch.setattr(
        gh_pr_watch,
        "get_pr_checks",
        lambda *args, **kwargs: call_order.append("checks") or [],
    )
    monkeypatch.setattr(
        gh_pr_watch,
        "summarize_checks",
        lambda checks: call_order.append("summarize") or sample_checks(),
    )
    monkeypatch.setattr(
        gh_pr_watch,
        "get_workflow_runs_for_sha",
        lambda *args, **kwargs: call_order.append("workflow") or [],
    )
    monkeypatch.setattr(
        gh_pr_watch,
        "failed_runs_from_workflow_runs",
        lambda *args, **kwargs: call_order.append("failed_runs") or [],
    )
    monkeypatch.setattr(
        gh_pr_watch,
        "failed_jobs_from_workflow_runs",
        lambda *args, **kwargs: call_order.append("failed_jobs") or [],
    )
    monkeypatch.setattr(
        gh_pr_watch,
        "recommend_actions",
        lambda *args, **kwargs: call_order.append("recommend") or ["idle"],
    )
    monkeypatch.setattr(gh_pr_watch, "save_state", lambda *args, **kwargs: None)

    args = argparse.Namespace(
        pr="123",
        repo=None,
        state_file=str(tmp_path / "watcher-state.json"),
        max_flaky_retries=3,
    )

    gh_pr_watch.collect_snapshot(args)

    assert call_order.index("review") < call_order.index("checks")
    assert call_order.index("review") < call_order.index("workflow")


def test_recommend_actions_prioritizes_review_comments():
    actions = gh_pr_watch.recommend_actions(
        sample_pr(),
        sample_checks(failed_count=1),
        [{"run_id": 99}],
        [],
        [{"kind": "review_comment", "id": "1"}],
        0,
        3,
    )

    assert actions == [
        "process_review_comment",
        "diagnose_ci_failure",
        "retry_failed_checks",
    ]


def test_dirty_merge_state_recommends_immediate_rebase():
    pr = sample_pr()
    pr["merge_state_status"] = "DIRTY"
    actions = gh_pr_watch.recommend_actions(
        pr, sample_checks(), [], [], [], 0, 3, rebase_due=True, rebase_reason="merge_conflict"
    )
    assert actions == ["rebase_pr"]


def test_periodic_rebase_is_not_repeated_when_base_is_unchanged():
    state = {
        "last_seen_base_sha": "base-1",
        "rebase_tracking_started_at": 0,
        "last_rebase_recommendation_at": 100,
        "last_rebase_recommendation_base_sha": "base-1",
        "last_rebase_recommendation_head_sha": "head-1",
    }
    pr = sample_pr()
    pr.update({"base_sha": "base-1", "head_sha": "head-1"})
    assert gh_pr_watch.rebase_recommendation(pr, state, 150, 100) == (False, None)
    assert gh_pr_watch.rebase_recommendation(pr, state, 201, 100) == (True, "cadence_elapsed")
    state["last_rebase_recommendation_at"] = 201
    assert gh_pr_watch.rebase_recommendation(pr, state, 202, 100) == (True, "cadence_elapsed")


def test_base_movement_and_elapsed_cadence_survive_persisted_state(tmp_path):
    path = tmp_path / "state.json"
    state = {
        "last_seen_base_sha": "base-1",
        "rebase_tracking_started_at": 10,
        "last_rebase_recommendation_at": 20,
        "last_rebase_recommendation_base_sha": "base-1",
        "last_rebase_recommendation_head_sha": "head-1",
    }
    gh_pr_watch.save_state(path, state)
    loaded, _ = gh_pr_watch.load_state(path)
    pr = sample_pr()
    pr.update({"base_sha": "base-2", "head_sha": "head-1"})
    assert gh_pr_watch.rebase_recommendation(pr, loaded, 30, 100) == (True, "base_moved")
    loaded["rebase_request"] = None
    loaded["rebase_ack"] = {"base_sha": "base-2", "head_sha": "head-1"}
    loaded.update({"last_rebase_recommendation_at": 30, "last_rebase_recommendation_base_sha": "base-2", "last_rebase_recommendation_head_sha": "head-1"})
    gh_pr_watch.save_state(path, loaded)
    loaded_again, _ = gh_pr_watch.load_state(path)
    assert gh_pr_watch.rebase_recommendation(pr, loaded_again, 131, 100) == (True, "cadence_elapsed")


def test_rebase_request_persists_until_matching_ack_and_tracks_new_head():
    state = {"last_seen_base_sha": "base-1", "last_rebase_recommendation_at": 1}
    pr = sample_pr()
    pr.update({"base_sha": "base-2", "head_sha": "head-1"})
    assert gh_pr_watch.rebase_recommendation(pr, state, 2, 100) == (True, "base_moved")
    pr["head_sha"] = "head-after-rebase"
    assert gh_pr_watch.rebase_recommendation(pr, state, 3, 100) == (True, "base_moved")
    assert state["rebase_request"]["head_sha"] == "head-after-rebase"


def test_ack_clears_request_only_for_current_base_and_head(tmp_path):
    path = tmp_path / "state.json"
    gh_pr_watch.save_state(path, {"rebase_request": {"reason": "base_moved"}})
    pr = sample_pr()
    with pytest.raises(RuntimeError):
        gh_pr_watch.acknowledge_rebase(path, pr, "wrong-base", pr["head_sha"], now=10)
    state, _ = gh_pr_watch.load_state(path)
    assert state["rebase_request"] is not None
    gh_pr_watch.acknowledge_rebase(path, pr, pr["base_sha"], pr["head_sha"], now=11)
    state, _ = gh_pr_watch.load_state(path)
    assert state["rebase_request"] is None
    assert state["rebase_ack"]["acknowledged_at"] == 11


def test_base_movement_invalidates_ack_and_ready_requires_current_ack():
    pr = sample_pr()
    state = {
        "last_seen_base_sha": pr["base_sha"],
        "rebase_ack": {"base_sha": pr["base_sha"], "head_sha": pr["head_sha"]},
    }
    assert gh_pr_watch.rebase_recommendation(pr, state, 1, 100) == (False, None)
    pr["base_sha"] = "new-base"
    assert gh_pr_watch.rebase_recommendation(pr, state, 2, 100) == (True, "base_moved")
    pr["rebase_ack"] = state["rebase_ack"]
    assert not gh_pr_watch.is_pr_ready_to_merge(pr, sample_checks(), [])


def test_ready_to_merge_requires_current_base_checkpoint():
    pr = sample_pr()
    assert gh_pr_watch.recommend_actions(pr, sample_checks(), [], [], [], 0, 3) == ["idle"]
    pr["rebase_ack"] = {"base_sha": pr["base_sha"], "head_sha": pr["head_sha"]}
    assert gh_pr_watch.recommend_actions(pr, sample_checks(), [], [], [], 0, 3) == ["ready_to_merge"]


def test_dirty_recommendation_stays_outstanding_until_ack():
    pr = sample_pr()
    pr["merge_state_status"] = "DIRTY"
    state = {}
    assert gh_pr_watch.rebase_recommendation(pr, state, 1, 100) == (True, "merge_conflict")
    pr["merge_state_status"] = "CLEAN"
    assert gh_pr_watch.rebase_recommendation(pr, state, 2, 100) == (True, "merge_conflict")


def test_new_head_after_rebase_does_not_repeat_immediately():
    state = {
        "last_seen_base_sha": "base-2",
        "last_rebase_recommendation_at": 100,
        "last_rebase_recommendation_base_sha": "base-2",
        "last_rebase_recommendation_head_sha": "head-before-rebase",
    }
    pr = sample_pr()
    pr.update({"base_sha": "base-2", "head_sha": "head-after-rebase"})
    assert gh_pr_watch.rebase_recommendation(pr, state, 101, 3600) == (False, None)
    assert state["last_rebase_recommendation_at"] == 101


def ready_snapshot(pr=None):
    return {
        "pr": pr or sample_pr(),
        "checks": sample_checks(),
        "failed_runs": [],
        "failed_jobs": [],
        "new_review_items": [],
        "actions": ["ready_to_merge"],
        "retry_state": {
            "current_sha_retries_used": 0,
            "max_flaky_retries": 3,
        },
    }


def test_run_watch_notifies_once_for_ready_snapshot(monkeypatch, tmp_path):
    events = []
    state_path = tmp_path / "watcher-state.json"

    monkeypatch.setattr(
        gh_pr_watch,
        "collect_snapshot",
        lambda args: (ready_snapshot(), state_path),
    )
    monkeypatch.setattr(
        gh_pr_watch,
        "print_event",
        lambda event, payload: events.append((event, payload)),
    )

    assert gh_pr_watch.run_watch(argparse.Namespace(poll_seconds=30)) == 0

    assert [event for event, _ in events] == ["snapshot", "ready_to_merge"]
    payload = events[-1][1]
    assert payload == {
        "pr": {
            "number": 123,
            "url": "https://github.com/openai/codex/pull/123",
            "head_sha": "abc123",
            "base_sha": "base123",
        },
        "checks": sample_checks(),
        "actions": ["ready_to_merge"],
        "state_file": str(state_path),
    }
    state, _ = gh_pr_watch.load_state(state_path)
    assert state["ready_notified"] == {"head_sha": "abc123", "base_sha": "base123"}


def test_run_watch_keeps_polling_when_ready_pair_was_already_notified(monkeypatch, tmp_path):
    events = []
    state_path = tmp_path / "watcher-state.json"
    gh_pr_watch.save_state(
        state_path,
        {"ready_notified": {"head_sha": "abc123", "base_sha": "base123"}},
    )
    monkeypatch.setattr(gh_pr_watch, "collect_snapshot", lambda args: (ready_snapshot(), state_path))
    monkeypatch.setattr(gh_pr_watch, "print_event", lambda event, payload: events.append((event, payload)))
    monkeypatch.setattr(gh_pr_watch.time, "sleep", lambda seconds: None)

    assert gh_pr_watch.run_watch(
        argparse.Namespace(poll_seconds=1, max_polls=2, max_duration_seconds=None)
    ) == 0

    assert [event for event, _ in events] == ["snapshot", "snapshot", "stop"]
    assert events[-1][1]["actions"] == ["stop_bounded_watch"]
    state, _ = gh_pr_watch.load_state(state_path)
    assert state["ready_notified"] == {"head_sha": "abc123", "base_sha": "base123"}


def test_run_watch_notifies_again_for_new_head_sha(monkeypatch, tmp_path):
    events = []
    state_path = tmp_path / "watcher-state.json"
    gh_pr_watch.save_state(
        state_path,
        {"ready_notified": {"head_sha": "old-head", "base_sha": "base123"}},
    )
    pr = sample_pr()
    pr["head_sha"] = "new-head"
    monkeypatch.setattr(gh_pr_watch, "collect_snapshot", lambda args: (ready_snapshot(pr), state_path))
    monkeypatch.setattr(gh_pr_watch, "print_event", lambda event, payload: events.append((event, payload)))

    assert gh_pr_watch.run_watch(argparse.Namespace(poll_seconds=30)) == 0

    assert [event for event, _ in events] == ["snapshot", "ready_to_merge"]
    assert events[-1][1]["pr"]["head_sha"] == "new-head"
    state, _ = gh_pr_watch.load_state(state_path)
    assert state["ready_notified"] == {"head_sha": "new-head", "base_sha": "base123"}


def test_run_watch_clears_ready_notification_when_snapshot_is_not_ready(monkeypatch, tmp_path):
    events = []
    state_path = tmp_path / "watcher-state.json"
    gh_pr_watch.save_state(
        state_path,
        {"ready_notified": {"head_sha": "abc123", "base_sha": "base123"}},
    )
    snapshot = ready_snapshot()
    snapshot["actions"] = ["idle"]
    monkeypatch.setattr(gh_pr_watch, "collect_snapshot", lambda args: (snapshot, state_path))
    monkeypatch.setattr(gh_pr_watch, "print_event", lambda event, payload: events.append((event, payload)))
    monkeypatch.setattr(gh_pr_watch.time, "sleep", lambda seconds: None)

    assert gh_pr_watch.run_watch(
        argparse.Namespace(poll_seconds=1, max_polls=1, max_duration_seconds=None)
    ) == 0

    state, _ = gh_pr_watch.load_state(state_path)
    assert "ready_notified" not in state


def test_failed_jobs_include_direct_logs_endpoint(monkeypatch):
    jobs_by_run = {
        99: [
            {
                "id": 555,
                "name": "unit tests",
                "status": "completed",
                "conclusion": "failure",
                "html_url": "https://github.com/openai/codex/actions/runs/99/job/555",
            },
            {
                "id": 556,
                "name": "lint",
                "status": "completed",
                "conclusion": "success",
            },
        ]
    }

    monkeypatch.setattr(
        gh_pr_watch,
        "get_jobs_for_run",
        lambda repo, run_id: jobs_by_run[run_id],
    )

    failed_jobs = gh_pr_watch.failed_jobs_from_workflow_runs(
        "openai/codex",
        [
            {
                "id": 99,
                "name": "CI",
                "status": "in_progress",
                "conclusion": "",
                "head_sha": "abc123",
            }
        ],
        "abc123",
    )

    assert failed_jobs == [
        {
            "run_id": 99,
            "workflow_name": "CI",
            "run_status": "in_progress",
            "run_conclusion": "",
            "job_id": 555,
            "job_name": "unit tests",
            "status": "completed",
            "conclusion": "failure",
            "html_url": "https://github.com/openai/codex/actions/runs/99/job/555",
            "logs_endpoint": "repos/openai/codex/actions/jobs/555/logs",
        }
    ]


def test_all_bot_logins_are_actionable_including_cubic_and_unknown():
    assert gh_pr_watch.is_actionable_review_bot_login("cubic-ai[bot]")
    assert gh_pr_watch.is_actionable_review_bot_login("new-reviewer[bot]")
    assert gh_pr_watch.is_bot_author({"author": "cubic-ai", "author_type": "Bot"})


def test_cubic_and_unknown_bots_surface_from_all_review_sources(monkeypatch):
    def payload(endpoint, repo=None):
        if "/issues/" in endpoint:
            return [{"id": 1, "user": {"login": "cubic-ai[bot]", "type": "Bot"}, "body": "issue finding"}]
        if endpoint.endswith("/comments"):
            return [{"id": 2, "user": {"login": "new-bot[bot]", "type": "Bot"}, "body": "inline finding"}]
        return [{"id": 3, "user": {"login": "cubic-ai[bot]", "type": "Bot"}, "body": "review finding"}]

    monkeypatch.setattr(gh_pr_watch, "gh_api_list_paginated", payload)
    monkeypatch.setattr(gh_pr_watch, "enrich_review_comment_threads", lambda *args: None)
    items = gh_pr_watch.fetch_new_review_items(sample_pr(), gh_pr_watch.migrate_legacy_state({}), False, "human")
    assert {item["kind"] for item in items} == {"issue_comment", "review_comment", "review"}
    assert {item["author"] for item in items} == {"cubic-ai[bot]", "new-bot[bot]"}


def test_unmapped_rest_resolution_is_treated_as_unresolved(monkeypatch):
    payload = [{"id": 9, "user": {"login": "review-bot[bot]", "type": "Bot"}, "body": "follow up", "resolved": True}]
    monkeypatch.setattr(gh_pr_watch, "gh_api_list_paginated", lambda endpoint, repo=None: payload)
    monkeypatch.setattr(gh_pr_watch, "enrich_review_comment_threads", lambda *args: None)
    state = gh_pr_watch.migrate_legacy_state({})
    surfaced = gh_pr_watch.fetch_new_review_items(sample_pr(), state, False, "human")
    assert surfaced[0]["body"] == "follow up"
    assert surfaced[0]["thread_resolved"] is None


def test_pending_item_persists_and_edit_resurfaces(monkeypatch):
    state = gh_pr_watch.migrate_legacy_state({})
    pr = sample_pr()
    payload = [{"id": 7, "user": {"login": "unknown[bot]", "type": "Bot"}, "body": "one"}]
    monkeypatch.setattr(gh_pr_watch, "gh_api_list_paginated", lambda endpoint, repo=None: payload)
    monkeypatch.setattr(gh_pr_watch, "enrich_review_comment_threads", lambda *args: None)
    first = gh_pr_watch.fetch_new_review_items(pr, state, False, "human")
    assert first[0]["body"] == "one"
    assert gh_pr_watch.fetch_new_review_items(pr, state, False, "human")[0]["body"] == "one"
    payload[0]["body"] = "edited"
    edited = gh_pr_watch.fetch_new_review_items(pr, state, False, "human")
    assert edited[0]["body"] == "edited"


def test_pending_item_remains_surfaced_when_later_marked_resolved(monkeypatch):
    state = gh_pr_watch.migrate_legacy_state({})
    payload = [{"id": 8, "user": {"login": "reviewer[bot]", "type": "Bot"}, "body": "finding"}]
    monkeypatch.setattr(gh_pr_watch, "gh_api_list_paginated", lambda endpoint, repo=None: payload)
    monkeypatch.setattr(gh_pr_watch, "enrich_review_comment_threads", lambda *args: None)
    assert gh_pr_watch.fetch_new_review_items(sample_pr(), state, False, "human")
    payload[0]["resolved"] = True
    surfaced = gh_pr_watch.fetch_new_review_items(sample_pr(), state, False, "human")
    assert surfaced[0]["status"] == "pending"
    assert state["feedback_items"]["issue_comment:8"]["status"] == "pending"


def test_graphql_thread_mapping_associates_followups_and_resolution(monkeypatch):
    graphql_payload = {
        "data": {"repository": {"pullRequest": {"reviewThreads": {
            "nodes": [{"id": "PRRT_kw1", "isResolved": True, "comments": {"nodes": [{"databaseId": 22}, {"databaseId": 23}]}}],
            "pageInfo": {"hasNextPage": False},
        }}}}
    }
    monkeypatch.setattr(gh_pr_watch, "gh_json", lambda args, repo=None: graphql_payload)
    items = gh_pr_watch.normalize_review_comments([{"id": 22}, {"id": 23}])
    gh_pr_watch.enrich_review_comment_threads("openai/codex", 123, items)
    assert {(item["thread_id"], item["thread_resolved"]) for item in items} == {("PRRT_kw1", True)}


def test_unmapped_review_comment_is_unresolved_when_graphql_fails(monkeypatch):
    monkeypatch.setattr(gh_pr_watch, "gh_json", lambda *args, **kwargs: (_ for _ in ()).throw(gh_pr_watch.GhCommandError("offline")))
    item = gh_pr_watch.normalize_review_comments([{"id": 24, "pull_request_review_id": 999}])[0]
    gh_pr_watch.enrich_review_comment_threads("openai/codex", 123, [item])
    assert item["thread_id"] is None
    assert item["thread_resolved"] is None


def test_bot_triage_keeps_substantive_feedback_actionable_but_not_lgtm():
    informational = {"author": "unknown[bot]", "author_type": "Bot", "body": "LGTM, no findings."}
    substantive = {"author": "cubic-ai[bot]", "author_type": "Bot", "body": "Warning: this fails when the input is empty."}
    assert gh_pr_watch.classify_bot_feedback(informational) == "informational"
    assert gh_pr_watch.classify_bot_feedback(substantive) == "needs-triage"
    assert "process_review_comment" not in gh_pr_watch.recommend_actions(sample_pr(), sample_checks(), [], [], [informational], 0, 3)
    assert "process_review_comment" in gh_pr_watch.recommend_actions(sample_pr(), sample_checks(), [], [], [substantive], 0, 3)


def test_disposition_is_durable_and_legacy_seen_ids_are_not_handled(tmp_path):
    path = tmp_path / "state.json"
    state = {"seen_issue_comment_ids": ["7"], "seen_review_comment_ids": [], "seen_review_ids": []}
    gh_pr_watch.save_state(path, state)
    loaded, _ = gh_pr_watch.load_state(path)
    assert loaded["legacy_seen_ids"]["issue_comment"] == ["7"]
    loaded["feedback_items"] = {"issue_comment:7": {"fingerprint": "x", "body": "finding"}}
    gh_pr_watch.save_state(path, loaded)
    record = gh_pr_watch.disposition_feedback_item(path, "issue_comment:7", "fixed")
    assert record["status"] == "dispositioned"
    assert record["disposition_history"][0]["disposition"] == "fixed"


def test_bounded_watch_stops_after_requested_polls(monkeypatch):
    events = []
    monkeypatch.setattr(gh_pr_watch, "collect_snapshot", lambda args: ({"pr": sample_pr(), "checks": sample_checks(), "actions": ["idle"]}, Path("/tmp/state")))
    monkeypatch.setattr(gh_pr_watch, "print_event", lambda event, payload: events.append((event, payload)))
    monkeypatch.setattr(gh_pr_watch.time, "sleep", lambda seconds: None)
    assert gh_pr_watch.run_watch(argparse.Namespace(poll_seconds=1, max_polls=2, max_duration_seconds=None)) == 0
    assert events[-1][0] == "stop"
    assert events[-1][1]["actions"] == ["stop_bounded_watch"]


def test_duration_bounded_watch_caps_sleep_to_remaining_time(monkeypatch):
    sleeps = []
    clock = iter([0.0, 0.01, 0.02, 0.11])
    monkeypatch.setattr(gh_pr_watch.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(gh_pr_watch, "collect_snapshot", lambda args: ({"pr": sample_pr(), "checks": sample_checks(), "actions": ["idle"]}, Path("/tmp/state")))
    monkeypatch.setattr(gh_pr_watch, "print_event", lambda *args: None)
    monkeypatch.setattr(gh_pr_watch.time, "sleep", lambda seconds: sleeps.append(seconds))
    assert gh_pr_watch.run_watch(argparse.Namespace(poll_seconds=30, max_polls=None, max_duration_seconds=0.1)) == 0
    assert sleeps == [0.08]
