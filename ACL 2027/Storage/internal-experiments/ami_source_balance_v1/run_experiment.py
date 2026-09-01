#!/usr/local/bin/python3.11
"""Run a text-nonexporting AMI source-balance classification experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Sequence

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
import scipy
import sklearn
from defusedxml import ElementTree as ET
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)
from sklearn.preprocessing import normalize


STUDY_ID = "ami-source-balance-internal-v1"
SEED = 20260826
BOOTSTRAP_REPLICATES = 5000
LABELS = ("a", "b", "c", "d")
ROLES = ("PM", "ID", "UI", "ME")
CONDITIONS = (
    "majority",
    "dominant_role_tfidf",
    "pooled_tfidf",
    "role_balanced_tfidf",
)
EXPECTED_ARCHIVE_SHA256 = (
    "b56e5babb2496b8795deeeda7e71178d7fbc9963f94276cf2a3f4b56ebbc9f9d"
)
EXPECTED_LICENSE_SHA256 = (
    "d52fd9c7c19eec9f0bec3107554c10937203e261259d73b01637a61501fec7f7"
)
EXPECTED_MEETINGS = 138
EXPECTED_WORD_ELEMENTS = 793_764
EXPECTED_COMPONENT_SIZES = {3: 2, 4: 33}
EXPECTED_ROLE_WORDS = {"PM": 261_194, "ID": 180_401, "UI": 165_500, "ME": 186_669}
EXPECTED_DOMINANT_ROLES = {"PM": 79, "ID": 20, "UI": 16, "ME": 23}
EXPECTED_SEEN_FOLD_SIZES = {1: 12, 2: 12, 3: 11, 4: 12, 5: 12, 6: 12, 7: 12, 8: 12, 9: 12, 10: 11}
EXPECTED_SEEN_PHASES = {"a": 29, "b": 30, "c": 30, "d": 29}
EXPECTED_UNSEEN_PHASES = {"a": 5, "b": 5, "c": 5, "d": 5}

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
SOURCE_ROOT = (
    PROJECT_ROOT
    / "dataset"
    / "ami_meetings"
    / "raw"
    / "extracted"
    / "ami_public_manual_1.6.2_scenario"
)
WORDS_DIR = SOURCE_ROOT / "words"
MEETINGS_XML = SOURCE_ROOT / "corpusResources" / "meetings.xml"
LICENSE_FILE = SOURCE_ROOT / "LICENCE.txt"
ARCHIVE = (
    PROJECT_ROOT
    / "dataset"
    / "ami_meetings"
    / "raw"
    / "upstream"
    / "ami_public_manual_1.6.2.zip"
)
PROTOCOL = HERE / "PROTOCOL.md"
FROZEN_RUN = HERE / "FROZEN_RUN.json"
RESULTS_DIR = HERE / "results"

TFIDF_COMMON = {
    "lowercase": True,
    "strip_accents": "unicode",
    "stop_words": "english",
    "token_pattern": r"(?u)\b[^\W\d_][^\W\d_]+\b",
    "ngram_range": (1, 1),
    "min_df": 2,
    "max_df": 0.98,
    "sublinear_tf": True,
    "norm": "l2",
    "dtype": np.float64,
}


@dataclass(frozen=True)
class MeetingMetadata:
    raw_meeting_id: str
    phase: str
    k10: int
    official_split: str
    agent_to_role: dict[str, str]
    raw_speakers: tuple[str, ...]


@dataclass(frozen=True)
class MeetingRecord:
    raw_meeting_id: str
    component_key: str
    phase: str
    k10: int
    official_split: str
    role_text: dict[str, str]
    role_word_counts: dict[str, int]


class UnionFind:
    def __init__(self, items: Iterable[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            parent = self.parent[item]
            self.parent[item] = root
            item = parent
        return root

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def check_runtime() -> dict[str, str]:
    versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "defusedxml": importlib.metadata.version("defusedxml"),
    }
    expected = {
        "python": "3.11.1",
        "numpy": "1.24.2",
        "scipy": "1.11.1",
        "scikit_learn": "1.3.0",
        "defusedxml": "0.7.1",
    }
    if versions != expected:
        raise RuntimeError("Runtime versions do not match the frozen requirements")
    return versions


def check_frozen_run(
    archive_sha256: str,
    license_sha256: str,
    bootstrap_replicates: int,
) -> dict[str, object]:
    if FROZEN_RUN.is_symlink() or not FROZEN_RUN.is_file():
        raise RuntimeError("The pre-fit frozen run record is missing or unsafe")
    try:
        frozen = json.loads(FROZEN_RUN.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("The pre-fit frozen run record is unreadable") from exc
    expected = {
        "study_id": STUDY_ID,
        "status": "frozen_before_model_fit",
        "source_archive_sha256": archive_sha256,
        "license_sha256": license_sha256,
        "protocol_sha256": sha256_file(PROTOCOL),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "seed": SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
    }
    for key, value in expected.items():
        if frozen.get(key) != value:
            raise RuntimeError("The current run does not match its pre-fit freeze")
    if bootstrap_replicates != BOOTSTRAP_REPLICATES:
        raise RuntimeError("Full runs must use the frozen bootstrap replicate count")
    return frozen


def parse_meeting_metadata() -> tuple[list[MeetingMetadata], set[str]]:
    if MEETINGS_XML.is_symlink() or not MEETINGS_XML.is_file():
        raise RuntimeError("Meeting metadata resource is missing or unsafe")
    root = ET.parse(MEETINGS_XML).getroot()
    metadata: list[MeetingMetadata] = []
    raw_speaker_ids: set[str] = set()
    observation_pattern = re.compile(r"^(?:ES|IS|TS)\d{4}[a-d]$")
    for element in root:
        if local_name(element.tag) != "meeting" or element.get("type") != "scenario":
            continue
        raw_meeting_id = element.get("observation", "")
        if not observation_pattern.fullmatch(raw_meeting_id):
            raise RuntimeError("Unexpected scenario meeting identifier shape")
        phase = raw_meeting_id[-1]
        try:
            k10 = int(element.get("k10", ""))
        except ValueError as exc:
            raise RuntimeError("Invalid official k10 fold metadata") from exc
        if k10 not in range(1, 11):
            raise RuntimeError("Official k10 fold is outside 1..10")
        visibility = element.get("visibility")
        if visibility == "unseen":
            official_split = "unseen"
        elif visibility == "seen" and element.get("seen_type") in {
            "training",
            "development",
        }:
            official_split = str(element.get("seen_type"))
        else:
            raise RuntimeError("Unexpected official split metadata")
        agent_to_role: dict[str, str] = {}
        meeting_speakers: list[str] = []
        for child in element:
            if local_name(child.tag) != "speaker":
                continue
            agent = child.get("nxt_agent", "")
            role = child.get("role", "")
            raw_speaker = child.get("global_name", "")
            if agent not in {"A", "B", "C", "D"} or role not in ROLES:
                raise RuntimeError("Unexpected AMI agent or role mapping")
            if not raw_speaker:
                raise RuntimeError("Missing AMI global-speaker linkage")
            agent_to_role[agent] = role
            meeting_speakers.append(raw_speaker)
            raw_speaker_ids.add(raw_speaker)
        if set(agent_to_role) != {"A", "B", "C", "D"}:
            raise RuntimeError("Scenario meeting does not have four mapped agents")
        if set(agent_to_role.values()) != set(ROLES):
            raise RuntimeError("Scenario meeting does not have the four expected roles")
        if len(set(meeting_speakers)) != 4:
            raise RuntimeError("Scenario meeting does not have four distinct speakers")
        metadata.append(
            MeetingMetadata(
                raw_meeting_id=raw_meeting_id,
                phase=phase,
                k10=k10,
                official_split=official_split,
                agent_to_role=agent_to_role,
                raw_speakers=tuple(sorted(meeting_speakers)),
            )
        )
    if len(metadata) != EXPECTED_MEETINGS:
        raise RuntimeError("Scenario meeting count does not match the frozen protocol")
    if len({item.raw_meeting_id for item in metadata}) != EXPECTED_MEETINGS:
        raise RuntimeError("Scenario meeting identifiers are not unique")
    return sorted(metadata, key=lambda item: item.raw_meeting_id), raw_speaker_ids


def build_component_map(metadata: Sequence[MeetingMetadata]) -> dict[str, str]:
    meeting_ids = [item.raw_meeting_id for item in metadata]
    union_find = UnionFind(meeting_ids)
    first_meeting_for_speaker: dict[str, str] = {}
    for item in metadata:
        for raw_speaker in item.raw_speakers:
            earlier = first_meeting_for_speaker.setdefault(raw_speaker, item.raw_meeting_id)
            union_find.union(item.raw_meeting_id, earlier)
    grouped: dict[str, list[str]] = defaultdict(list)
    for meeting_id in meeting_ids:
        grouped[union_find.find(meeting_id)].append(meeting_id)
    components = [tuple(sorted(values)) for values in grouped.values()]
    size_distribution = Counter(len(values) for values in components)
    if dict(sorted(size_distribution.items())) != EXPECTED_COMPONENT_SIZES:
        raise RuntimeError("Connected-component structure does not match the frozen source manifest")
    metadata_by_id = {item.raw_meeting_id: item for item in metadata}
    component_map: dict[str, str] = {}
    for values in components:
        folds = {metadata_by_id[value].k10 for value in values}
        splits = {metadata_by_id[value].official_split for value in values}
        if len(folds) != 1 or len(splits) != 1:
            raise RuntimeError("A linked-speaker component crosses an evaluation boundary")
        component_key = "|".join(values)
        for value in values:
            component_map[value] = component_key
    if len(set(component_map.values())) != 35:
        raise RuntimeError("Expected 35 meeting-speaker components")
    return component_map


def parse_word_resource(path: Path) -> tuple[str, int, int]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("A required word resource is missing or unsafe")
    root = ET.parse(path).getroot()
    words: list[str] = []
    element_count = 0
    empty_count = 0
    for element in root.iter():
        if local_name(element.tag) != "w":
            continue
        element_count += 1
        value = (element.text or "").strip()
        if value:
            words.append(value)
        else:
            empty_count += 1
    return " ".join(words), element_count, empty_count


def load_records(
    metadata: Sequence[MeetingMetadata], component_map: dict[str, str]
) -> tuple[list[MeetingRecord], dict[str, int]]:
    records: list[MeetingRecord] = []
    word_element_count = 0
    retained_word_count = 0
    empty_word_count = 0
    for item in metadata:
        role_text: dict[str, str] = {}
        role_word_counts: dict[str, int] = {}
        for agent in ("A", "B", "C", "D"):
            text, elements, empty = parse_word_resource(
                WORDS_DIR / f"{item.raw_meeting_id}.{agent}.words.xml"
            )
            role = item.agent_to_role[agent]
            role_text[role] = text
            role_word_counts[role] = elements - empty
            word_element_count += elements
            retained_word_count += elements - empty
            empty_word_count += empty
        if set(role_text) != set(ROLES):
            raise RuntimeError("A meeting is missing an expected role transcript")
        records.append(
            MeetingRecord(
                raw_meeting_id=item.raw_meeting_id,
                component_key=component_map[item.raw_meeting_id],
                phase=item.phase,
                k10=item.k10,
                official_split=item.official_split,
                role_text=role_text,
                role_word_counts=role_word_counts,
            )
        )
    if word_element_count != EXPECTED_WORD_ELEMENTS:
        raise RuntimeError("Orthographic word-element count does not match the source manifest")
    role_totals = {
        role: sum(record.role_word_counts[role] for record in records) for role in ROLES
    }
    if role_totals != EXPECTED_ROLE_WORDS:
        raise RuntimeError("Role-level word counts do not match the frozen adapter contract")
    ties = sum(
        1
        for record in records
        if list(record.role_word_counts.values()).count(max(record.role_word_counts.values())) > 1
    )
    if ties:
        raise RuntimeError("Unexpected dominant-role tie in the source snapshot")
    dominant_counts = Counter(dominant_role(record) for record in records)
    if dict(dominant_counts) != EXPECTED_DOMINANT_ROLES:
        raise RuntimeError("Dominant-role distribution does not match the frozen adapter contract")
    return records, {
        "orthographic_word_elements": word_element_count,
        "retained_nonempty_word_elements": retained_word_count,
        "empty_word_elements": empty_word_count,
        "role_word_elements": role_totals,
        "dominant_role_meetings": dict(dominant_counts),
        "dominant_role_ties": ties,
    }


def pooled_text(record: MeetingRecord) -> str:
    return " ".join(record.role_text[role] for role in ROLES)


def dominant_role(record: MeetingRecord) -> str:
    return max(ROLES, key=lambda role: (record.role_word_counts[role], -ROLES.index(role)))


def make_classifier() -> LogisticRegression:
    return LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=3000,
        multi_class="ovr",
        random_state=SEED,
        solver="liblinear",
    )


def fit_predict(
    train: Sequence[MeetingRecord],
    test: Sequence[MeetingRecord],
    condition: str,
) -> tuple[list[str], int]:
    y_train = [record.phase for record in train]
    if set(y_train) != set(LABELS):
        raise RuntimeError("A training fold is missing a phase class")
    if condition == "majority":
        counts = Counter(y_train)
        prediction = sorted(LABELS, key=lambda label: (-counts[label], label))[0]
        return [prediction] * len(test), 0

    if condition not in {
        "pooled_tfidf",
        "dominant_role_tfidf",
        "role_balanced_tfidf",
    }:
        raise RuntimeError("Unknown experimental condition")

    vectorizer = TfidfVectorizer(max_features=30_000, **TFIDF_COMMON)
    vectorizer.fit([pooled_text(record) for record in train])
    feature_count = len(vectorizer.vocabulary_)
    if condition == "pooled_tfidf":
        train_matrix = vectorizer.transform([pooled_text(record) for record in train])
        test_matrix = vectorizer.transform([pooled_text(record) for record in test])
    elif condition == "dominant_role_tfidf":
        train_matrix = vectorizer.transform(
            [record.role_text[dominant_role(record)] for record in train]
        )
        test_matrix = vectorizer.transform(
            [record.role_text[dominant_role(record)] for record in test]
        )
    else:
        train_blocks = [
            vectorizer.transform([record.role_text[role] for record in train])
            for role in ROLES
        ]
        test_blocks = [
            vectorizer.transform([record.role_text[role] for record in test])
            for role in ROLES
        ]
        train_matrix = train_blocks[0].copy()
        test_matrix = test_blocks[0].copy()
        for block in train_blocks[1:]:
            train_matrix = train_matrix + block
        for block in test_blocks[1:]:
            test_matrix = test_matrix + block
        train_matrix = normalize(train_matrix * 0.25, norm="l2")
        test_matrix = normalize(test_matrix * 0.25, norm="l2")

    classifier = make_classifier()
    classifier.fit(train_matrix, y_train)
    predictions = [str(value) for value in classifier.predict(test_matrix)]
    return predictions, feature_count


def prediction_rows(
    records: Sequence[MeetingRecord],
    predictions: Sequence[str],
    condition: str,
    scope: str,
    fold: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record, prediction in zip(records, predictions):
        rows.append(
            {
                "scope": scope,
                "condition": condition,
                "phase": record.phase,
                "fold": fold,
                "predicted_phase": prediction,
                "correct": int(prediction == record.phase),
                "_meeting_key": record.raw_meeting_id,
                "_component_key": record.component_key,
            }
        )
    return rows


def run_evaluations(
    records: Sequence[MeetingRecord],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    fits: list[dict[str, object]] = []
    seen_records = [record for record in records if record.official_split != "unseen"]
    seen_fold_sizes = Counter(record.k10 for record in seen_records)
    if dict(sorted(seen_fold_sizes.items())) != EXPECTED_SEEN_FOLD_SIZES:
        raise RuntimeError("Seen-only k10 fold sizes do not match the frozen protocol")
    if dict(Counter(record.phase for record in seen_records)) != EXPECTED_SEEN_PHASES:
        raise RuntimeError("Seen-only phase support does not match the frozen protocol")
    for fold in range(1, 11):
        train = [record for record in seen_records if record.k10 != fold]
        test = [record for record in seen_records if record.k10 == fold]
        train_components = {record.component_key for record in train}
        test_components = {record.component_key for record in test}
        if train_components & test_components:
            raise RuntimeError("A k10 fold leaks a connected component")
        for condition in CONDITIONS:
            predictions, feature_count = fit_predict(train, test, condition)
            rows.extend(
                prediction_rows(
                    test,
                    predictions,
                    condition,
                    "official_k10_cv",
                    str(fold),
                )
            )
            fits.append(
                {
                    "scope": "official_k10_cv",
                    "fold": str(fold),
                    "condition": condition,
                    "training_meetings": len(train),
                    "evaluation_meetings": len(test),
                    "feature_count": feature_count,
                }
            )

    seen = [record for record in records if record.official_split != "unseen"]
    unseen = [record for record in records if record.official_split == "unseen"]
    if dict(Counter(record.phase for record in unseen)) != EXPECTED_UNSEEN_PHASES:
        raise RuntimeError("Unseen phase support does not match the frozen protocol")
    if {record.component_key for record in seen} & {
        record.component_key for record in unseen
    }:
        raise RuntimeError("The official unseen split leaks a connected component")
    for condition in CONDITIONS:
        predictions, feature_count = fit_predict(seen, unseen, condition)
        rows.extend(
            prediction_rows(
                unseen,
                predictions,
                condition,
                "official_unseen",
                "unseen",
            )
        )
        fits.append(
            {
                "scope": "official_unseen",
                "fold": "unseen",
                "condition": condition,
                "training_meetings": len(seen),
                "evaluation_meetings": len(unseen),
                "feature_count": feature_count,
            }
        )
    return rows, fits


def stable_seed(*parts: str) -> int:
    suffix = int(hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:8], 16)
    return (SEED + suffix) % (2**32 - 1)


def metric_value(rows: Sequence[dict[str, object]], metric: str) -> float:
    true = [str(row["phase"]) for row in rows]
    predicted = [str(row["predicted_phase"]) for row in rows]
    if metric == "macro_f1":
        return float(
            f1_score(true, predicted, labels=list(LABELS), average="macro", zero_division=0)
        )
    if metric == "accuracy":
        return float(accuracy_score(true, predicted))
    raise RuntimeError("Unsupported metric")


def bootstrap_interval(
    rows: Sequence[dict[str, object]],
    metric: str,
    replicates: int,
    seed_parts: Sequence[str],
) -> tuple[float, float]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["_component_key"])].append(row)
    components = sorted(grouped)
    generator = np.random.default_rng(stable_seed(*seed_parts, metric))
    values = np.empty(replicates, dtype=float)
    for index in range(replicates):
        selected = generator.choice(components, size=len(components), replace=True)
        sample = [row for component in selected for row in grouped[str(component)]]
        values[index] = metric_value(sample, metric)
    low, high = np.quantile(values, [0.025, 0.975])
    return float(low), float(high)


def summarize_condition(
    rows: Sequence[dict[str, object]], replicates: int
) -> dict[str, object]:
    true = [str(row["phase"]) for row in rows]
    predicted = [str(row["predicted_phase"]) for row in rows]
    macro_f1 = metric_value(rows, "macro_f1")
    accuracy = metric_value(rows, "accuracy")
    macro_ci = bootstrap_interval(
        rows,
        "macro_f1",
        replicates,
        (str(rows[0]["scope"]), str(rows[0]["condition"])),
    )
    accuracy_ci = bootstrap_interval(
        rows,
        "accuracy",
        replicates,
        (str(rows[0]["scope"]), str(rows[0]["condition"])),
    )
    per_phase = f1_score(
        true, predicted, labels=list(LABELS), average=None, zero_division=0
    )
    return {
        "meetings": len(rows),
        "components": len({str(row["_component_key"]) for row in rows}),
        "macro_f1": macro_f1,
        "macro_f1_ci95": list(macro_ci),
        "accuracy": accuracy,
        "accuracy_ci95": list(accuracy_ci),
        "balanced_accuracy": float(balanced_accuracy_score(true, predicted)),
        "per_phase_f1": {
            label: float(value) for label, value in zip(LABELS, per_phase)
        },
        "confusion_matrix": confusion_matrix(
            true, predicted, labels=list(LABELS)
        ).tolist(),
    }


def paired_difference(
    condition_rows: Sequence[dict[str, object]],
    reference_rows: Sequence[dict[str, object]],
    metric: str,
    replicates: int,
    label: str,
) -> dict[str, object]:
    condition_by_meeting = {str(row["_meeting_key"]): row for row in condition_rows}
    reference_by_meeting = {str(row["_meeting_key"]): row for row in reference_rows}
    if set(condition_by_meeting) != set(reference_by_meeting):
        raise RuntimeError("Paired conditions do not contain identical meetings")
    component_to_meetings: dict[str, list[str]] = defaultdict(list)
    for meeting_id, row in condition_by_meeting.items():
        component_to_meetings[str(row["_component_key"])].append(meeting_id)
    components = sorted(component_to_meetings)

    estimate = metric_value(condition_rows, metric) - metric_value(reference_rows, metric)
    generator = np.random.default_rng(stable_seed(label, metric))
    values = np.empty(replicates, dtype=float)
    for index in range(replicates):
        selected = generator.choice(components, size=len(components), replace=True)
        meeting_ids = [
            meeting_id
            for component in selected
            for meeting_id in component_to_meetings[str(component)]
        ]
        condition_sample = [condition_by_meeting[meeting_id] for meeting_id in meeting_ids]
        reference_sample = [reference_by_meeting[meeting_id] for meeting_id in meeting_ids]
        values[index] = metric_value(condition_sample, metric) - metric_value(
            reference_sample, metric
        )
    low, high = np.quantile(values, [0.025, 0.975])
    return {"estimate": float(estimate), "ci95": [float(low), float(high)]}


def source_concentration(records: Sequence[MeetingRecord]) -> dict[str, object]:
    dominant_shares: list[float] = []
    normalized_hhi: list[float] = []
    by_phase: dict[str, list[float]] = defaultdict(list)
    for record in records:
        counts = np.array([record.role_word_counts[role] for role in ROLES], dtype=float)
        shares = counts / counts.sum()
        dominant_share = float(shares.max())
        hhi = float(np.square(shares).sum())
        normalized = (hhi - 0.25) / 0.75
        dominant_shares.append(dominant_share)
        normalized_hhi.append(normalized)
        by_phase[record.phase].append(dominant_share)

    def distribution(values: Sequence[float]) -> dict[str, float]:
        array = np.asarray(values, dtype=float)
        return {
            "mean": float(array.mean()),
            "median": float(np.median(array)),
            "q25": float(np.quantile(array, 0.25)),
            "q75": float(np.quantile(array, 0.75)),
            "minimum": float(array.min()),
            "maximum": float(array.max()),
        }

    return {
        "dominant_role_word_share": distribution(dominant_shares),
        "normalized_four_role_hhi": distribution(normalized_hhi),
        "dominant_role_word_share_by_phase": {
            label: distribution(by_phase[label]) for label in LABELS
        },
    }


def summarize_results(
    rows: Sequence[dict[str, object]], replicates: int
) -> dict[str, object]:
    results: dict[str, object] = {"scopes": {}, "paired_differences": {}}
    for scope in ("official_k10_cv", "official_unseen"):
        scope_rows = [row for row in rows if row["scope"] == scope]
        scope_result: dict[str, object] = {}
        by_condition = {
            condition: [row for row in scope_rows if row["condition"] == condition]
            for condition in CONDITIONS
        }
        for condition in CONDITIONS:
            scope_result[condition] = summarize_condition(
                by_condition[condition], replicates
            )
        results["scopes"][scope] = scope_result

        differences: dict[str, object] = {}
        for metric in ("macro_f1", "accuracy"):
            differences[f"pooled_minus_dominant_{metric}"] = paired_difference(
                by_condition["pooled_tfidf"],
                by_condition["dominant_role_tfidf"],
                metric,
                replicates,
                f"{scope}|pooled-minus-dominant",
            )
            differences[f"role_balanced_minus_pooled_{metric}"] = paired_difference(
                by_condition["role_balanced_tfidf"],
                by_condition["pooled_tfidf"],
                metric,
                replicates,
                f"{scope}|role-balanced-minus-pooled",
            )
        results["paired_differences"][scope] = differences
    return results


def summary_csv(metrics: dict[str, object]) -> str:
    fields = [
        "scope",
        "condition",
        "meetings",
        "components",
        "macro_f1",
        "macro_f1_ci_low",
        "macro_f1_ci_high",
        "accuracy",
        "accuracy_ci_low",
        "accuracy_ci_high",
        "balanced_accuracy",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    scopes = metrics["scopes"]
    assert isinstance(scopes, dict)
    for scope in ("official_k10_cv", "official_unseen"):
        scope_metrics = scopes[scope]
        assert isinstance(scope_metrics, dict)
        for condition in CONDITIONS:
            item = scope_metrics[condition]
            assert isinstance(item, dict)
            writer.writerow(
                {
                    "scope": scope,
                    "condition": condition,
                    "meetings": item["meetings"],
                    "components": item["components"],
                    "macro_f1": f"{float(item['macro_f1']):.6f}",
                    "macro_f1_ci_low": f"{float(item['macro_f1_ci95'][0]):.6f}",
                    "macro_f1_ci_high": f"{float(item['macro_f1_ci95'][1]):.6f}",
                    "accuracy": f"{float(item['accuracy']):.6f}",
                    "accuracy_ci_low": f"{float(item['accuracy_ci95'][0]):.6f}",
                    "accuracy_ci_high": f"{float(item['accuracy_ci95'][1]):.6f}",
                    "balanced_accuracy": f"{float(item['balanced_accuracy']):.6f}",
                }
            )
    return buffer.getvalue()


def result_report(metrics: dict[str, object], concentration: dict[str, object]) -> str:
    scopes = metrics["scopes"]
    differences = metrics["paired_differences"]
    assert isinstance(scopes, dict) and isinstance(differences, dict)

    def interval(value: dict[str, object], metric: str) -> str:
        estimate = float(value[metric])
        low, high = value[f"{metric}_ci95"]
        return f"{estimate:.3f} [{float(low):.3f}, {float(high):.3f}]"

    lines = [
        "# AMI source-balance internal results",
        "",
        "These are real-corpus, local-only exploratory results. They do not measure",
        "human qualitative validity and do not populate the WarrantRoute result tables.",
        "",
        "## Classification results",
        "",
        "| Scope | Condition | Macro F1 [95% component bootstrap] | Accuracy [95% component bootstrap] |",
        "|---|---|---:|---:|",
    ]
    for scope in ("official_k10_cv", "official_unseen"):
        scope_values = scopes[scope]
        assert isinstance(scope_values, dict)
        for condition in CONDITIONS:
            value = scope_values[condition]
            assert isinstance(value, dict)
            lines.append(
                f"| {scope} | {condition} | {interval(value, 'macro_f1')} | "
                f"{interval(value, 'accuracy')} |"
            )

    cv_differences = differences["official_k10_cv"]
    assert isinstance(cv_differences, dict)
    h1 = cv_differences["pooled_minus_dominant_macro_f1"]
    h2 = cv_differences["role_balanced_minus_pooled_macro_f1"]
    assert isinstance(h1, dict) and isinstance(h2, dict)
    h1_low, h1_high = h1["ci95"]
    h2_low, h2_high = h2["ci95"]
    h1_supported = float(h1_low) > 0
    h2_supported = float(h2_low) > -0.05

    dominant = concentration["dominant_role_word_share"]
    hhi = concentration["normalized_four_role_hhi"]
    assert isinstance(dominant, dict) and isinstance(hhi, dict)
    lines.extend(
        [
            "",
            "## Prespecified comparisons",
            "",
            f"- Pooled minus dominant-role macro F1 in official k10 CV: "
            f"{float(h1['estimate']):.3f} [{float(h1_low):.3f}, {float(h1_high):.3f}]. "
            f"H1 supported: {'yes' if h1_supported else 'no'}.",
            f"- Role-balanced minus pooled macro F1 in official k10 CV: "
            f"{float(h2['estimate']):.3f} [{float(h2_low):.3f}, {float(h2_high):.3f}]. "
            f"H2 noninferiority at -0.05 supported: {'yes' if h2_supported else 'no'}.",
            "",
            "## Source concentration",
            "",
            f"Across 138 meetings, the median largest-role word share was "
            f"{float(dominant['median']):.3f} (IQR {float(dominant['q25']):.3f}–"
            f"{float(dominant['q75']):.3f}). The median normalized four-role HHI was "
            f"{float(hhi['median']):.3f}.",
            "",
            "## Interpretation limits",
            "",
            "The task predicts an elicited scenario phase from lexical content. It does not",
            "show that a model produced a valid theme, preserved participant voice, detected",
            "a serious error, routed expertise correctly, or repaired an interpretation.",
            "The official-unseen sensitivity set contains only five connected components, so",
            "its interval is descriptive. No transcript terms or examples were inspected or",
            "selected for this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def check_for_identifier_leaks(
    contents: dict[str, str], raw_meeting_ids: set[str], raw_speaker_ids: set[str]
) -> dict[str, object]:
    combined = "\n".join(contents.values())
    raw_matches = [
        value
        for value in raw_meeting_ids | raw_speaker_ids
        if value and value in combined
    ]
    pattern_matches = []
    for pattern in (
        r"\b(?:ES|IS|TS)\d{4}[a-d]?\b",
        r"\b[MF][IET][EDO]\d{3}\b",
        r"\bstarttime\b",
        r"\bendtime\b",
        r"\.words\b",
        r"\.segments\b",
        r"\bglobal_name\b",
        r"\bnite:id\b",
        r"\bobservation\b",
    ):
        if re.search(pattern, combined, flags=re.IGNORECASE):
            pattern_matches.append(pattern)
    if raw_matches or pattern_matches:
        raise RuntimeError("Generated output failed the raw-identifier leak check")
    return {
        "raw_identifier_leak_scan_passed": True,
        "raw_identifiers_scanned": len(raw_meeting_ids) + len(raw_speaker_ids),
        "forbidden_patterns_scanned": 9,
        "transcript_text_exported": False,
        "feature_names_exported": False,
        "per_meeting_predictions_exported": False,
        "raw_timestamps_exported": False,
    }


def write_outputs(contents: dict[str, str]) -> dict[str, str]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(RESULTS_DIR, 0o700)
    hashes: dict[str, str] = {}
    for name, content in contents.items():
        path = RESULTS_DIR / name
        path.write_text(content, encoding="utf-8")
        os.chmod(path, 0o600)
        hashes[name] = sha256_text(content)
    return hashes


def validation_record(
    records: Sequence[MeetingRecord],
    word_counts: dict[str, int],
    archive_sha256: str,
    license_sha256: str,
) -> dict[str, object]:
    return {
        "study_id": STUDY_ID,
        "source_archive_sha256_matches": archive_sha256 == EXPECTED_ARCHIVE_SHA256,
        "license_sha256_matches": license_sha256 == EXPECTED_LICENSE_SHA256,
        "scenario_meetings": len(records),
        "meeting_speaker_components": len({record.component_key for record in records}),
        "component_size_distribution": {
            str(size): count for size, count in EXPECTED_COMPONENT_SIZES.items()
        },
        "official_split_meetings": dict(
            sorted(Counter(record.official_split for record in records).items())
        ),
        "official_k10_meetings": {
            str(key): value
            for key, value in sorted(Counter(record.k10 for record in records).items())
        },
        "phase_meetings": dict(sorted(Counter(record.phase for record in records).items())),
        **word_counts,
        "raw_text_persisted_by_adapter": False,
        "external_model_or_service_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and count the minimized adapter without fitting models.",
    )
    parser.add_argument(
        "--bootstrap-replicates",
        type=int,
        default=BOOTSTRAP_REPLICATES,
        help="Component-bootstrap replicates; default is frozen at 5000.",
    )
    args = parser.parse_args()
    if args.bootstrap_replicates < 100:
        raise SystemExit("--bootstrap-replicates must be at least 100")
    runtime_versions = check_runtime()
    if not all(
        path.is_file() and not path.is_symlink()
        for path in (ARCHIVE, LICENSE_FILE, PROTOCOL)
    ):
        raise SystemExit("Required source or protocol file is missing or unsafe")

    archive_sha256 = sha256_file(ARCHIVE)
    if archive_sha256 != EXPECTED_ARCHIVE_SHA256:
        raise SystemExit("AMI archive checksum does not match the frozen protocol")
    license_sha256 = sha256_file(LICENSE_FILE)
    if license_sha256 != EXPECTED_LICENSE_SHA256:
        raise SystemExit("AMI license checksum does not match the frozen protocol")
    frozen_run: dict[str, object] | None = None
    if not args.validate_only:
        frozen_run = check_frozen_run(
            archive_sha256, license_sha256, args.bootstrap_replicates
        )

    metadata, raw_speaker_ids = parse_meeting_metadata()
    component_map = build_component_map(metadata)
    records, word_counts = load_records(metadata, component_map)
    validation = validation_record(
        records, word_counts, archive_sha256, license_sha256
    )

    raw_meeting_ids = {item.raw_meeting_id for item in metadata}
    if args.validate_only:
        validation_content = json.dumps(validation, indent=2, sort_keys=True) + "\n"
        leak_check = check_for_identifier_leaks(
            {"validation_only.json": validation_content},
            raw_meeting_ids,
            raw_speaker_ids,
        )
        validation.update(leak_check)
        write_outputs(
            {
                "validation_only.json": json.dumps(
                    validation, indent=2, sort_keys=True
                )
                + "\n"
            }
        )
        print("AMI adapter validation passed; no model was fit and no transcript text was exported.")
        return 0

    rows, fits = run_evaluations(records)
    expected_prediction_rows = (
        118 * len(CONDITIONS)
        + 20 * len(CONDITIONS)
    )
    if len(rows) != expected_prediction_rows:
        raise RuntimeError("Prediction row count is incomplete")
    metrics = summarize_results(rows, args.bootstrap_replicates)
    concentration = source_concentration(records)
    metrics["source_concentration"] = concentration
    metrics["bootstrap_replicates"] = args.bootstrap_replicates

    summary_content = summary_csv(metrics)
    metrics_content = json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    report_content = result_report(metrics, concentration)
    validation_content = json.dumps(validation, indent=2, sort_keys=True) + "\n"
    generated_contents = {
        "summary.csv": summary_content,
        "metrics.json": metrics_content,
        "report.md": report_content,
        "validation.json": validation_content,
    }
    leak_check = check_for_identifier_leaks(
        generated_contents, raw_meeting_ids, raw_speaker_ids
    )
    validation.update(leak_check)
    generated_contents["validation.json"] = (
        json.dumps(validation, indent=2, sort_keys=True) + "\n"
    )
    output_hashes = write_outputs(generated_contents)

    manifest = {
        "study_id": STUDY_ID,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "private_offline_internal_experiment",
        "manuscript_table_eligible": False,
        "source": {
            "corpus": "AMI Meeting Corpus scenario subset",
            "official_artifact": "ami_public_manual_1.6.2.zip",
            "archive_sha256": archive_sha256,
            "license_sha256": license_sha256,
            "license": "CC-BY-4.0",
        },
        "protocol_sha256": sha256_file(PROTOCOL),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "frozen_run_sha256": sha256_file(FROZEN_RUN),
        "frozen_at_utc": frozen_run["frozen_at_utc"] if frozen_run else None,
        "seed": SEED,
        "bootstrap_replicates": args.bootstrap_replicates,
        "environment": {
            **runtime_versions,
            "platform": platform.platform(),
        },
        "fits": fits,
        "output_sha256": output_hashes,
        **leak_check,
    }
    manifest_content = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    check_for_identifier_leaks(
        {"run_manifest.json": manifest_content}, raw_meeting_ids, raw_speaker_ids
    )
    write_outputs({"run_manifest.json": manifest_content})

    cv = metrics["scopes"]["official_k10_cv"]
    assert isinstance(cv, dict)
    print("AMI internal experiment completed.")
    for condition in CONDITIONS:
        value = cv[condition]
        assert isinstance(value, dict)
        print(
            f"{condition}: macro-F1={float(value['macro_f1']):.3f}, "
            f"accuracy={float(value['accuracy']):.3f}"
        )
    print(f"Results: {RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
