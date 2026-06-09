from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import tomllib
import unittest


FORMULAS = {
    "build-base",
    "build-basic",
    "design-review",
    "do-work",
    "do-work-item",
    "fix-convoy",
    "gap-analysis",
    "github-issue-fix",
    "github-issue-fix-base",
    "github-issue-fix-design-review-work",
    "github-issue-triage-base",
    "github-issue-triage",
    "github-pr-review",
    "implement",
    "publish",
    "review",
    "same-session-implement",
}

ROLE_AGENTS = {
    "design-author",
    "design-implementation-reviewer",
    "design-test-risk-reviewer",
    "gap-analyst",
    "implementation-reviewer",
    "implementation-worker",
    "issue-triager",
    "publisher",
    "requirements-planner",
    "review-synthesizer",
    "run-operator",
    "task-decomposer",
}

CATALOG_FORMULAS = {
    "build-basic",
    "design-review",
    "gap-analysis",
    "github-issue-fix",
    "github-issue-triage",
    "github-pr-review",
    "implement",
    "review",
}

BUILD_BASE_STEPS = [
    "prepare",
    "requirements",
    "plan",
    "plan-review",
    "decompose",
    "implement",
    "implement-same-session",
    "review",
    "finalize",
    "publish",
]

THIRD_PARTY_BUILD_PACKS = {
    "compound-engineering": {
        "formula": "compound-build",
        "base_import_binding": "gc",
        "base_import_source": "../gascity",
        "vendor": "compound-engineering-plugin",
        "upstream": "https://github.com/EveryInc/compound-engineering-plugin",
        "commit": "b6250490bec4c0488d68ad66d72bd99f6edb95fd",
        "implementation_target": "compound-engineering.ce-work",
        "implementation_formula": "compound-work",
        "implementation_item_formula": "compound-work-item",
        "skills": {
            "requirements": "ce-brainstorm",
            "plan": "ce-plan",
            "implement": "ce-work",
            "review": "ce-code-review",
            "finalize": "ce-compound",
        },
        "expansions": {
            "plan-review": "compound-plan-review",
            "review": "compound-code-review",
            "finalize": "compound-resolution",
        },
        "review_expansion": "compound-code-review",
        "gap_analysis_target": "compound-engineering.ce-coherence-reviewer",
        "review_fix_asset": "assets/workflows/compound-code-review/{target}.apply-review-findings.md",
        "persona_assets": {
            "ce-architecture-strategist.md",
            "ce-adversarial-reviewer.md",
            "ce-agent-native-reviewer.md",
            "ce-api-contract-reviewer.md",
            "ce-coherence-reviewer.md",
            "ce-correctness-reviewer.md",
            "ce-data-migration-reviewer.md",
            "ce-deployment-verification-agent.md",
            "ce-feasibility-reviewer.md",
            "ce-julik-frontend-races-reviewer.md",
            "ce-learnings-researcher.md",
            "ce-maintainability-reviewer.md",
            "ce-performance-reviewer.md",
            "ce-pr-comment-resolver.md",
            "ce-previous-comments-reviewer.md",
            "ce-project-standards-reviewer.md",
            "ce-reliability-reviewer.md",
            "ce-scope-guardian-reviewer.md",
            "ce-security-reviewer.md",
            "ce-swift-ios-reviewer.md",
            "ce-testing-reviewer.md",
        },
    },
    "superpowers": {
        "formula": "superpowers-build",
        "base_import_binding": "gc",
        "base_import_source": "../gascity",
        "vendor": "superpowers",
        "upstream": "https://github.com/obra/superpowers",
        "commit": "6fd4507659784c351abbd2bc264c7162cfd386dc",
        "implementation_target": "superpowers.implementer",
        "implementation_formula": "superpowers-development",
        "implementation_item_formula": "superpowers-development-item",
        "skills": {
            "requirements": "brainstorming",
            "plan": "writing-plans",
            "implement": "executing-plans",
            "review": "requesting-code-review",
            "finalize": "finishing-a-development-branch",
        },
        "expansions": {
            "requirements": "superpowers-brainstorming",
            "plan-review": "superpowers-plan-review",
            "review": "superpowers-code-review",
        },
        "review_expansion": "superpowers-code-review",
        "gap_analysis_target": "superpowers.code-quality-reviewer",
        "review_fix_asset": "assets/workflows/superpowers-code-review/{target}.process-code-review.md",
        "prompt_assets": {
            "skills/brainstorming/spec-document-reviewer-prompt.md",
            "skills/brainstorming/visual-companion.md",
            "skills/subagent-driven-development/spec-reviewer-prompt.md",
            "skills/subagent-driven-development/implementer-prompt.md",
            "skills/subagent-driven-development/code-quality-reviewer-prompt.md",
            "skills/requesting-code-review/code-reviewer.md",
            "skills/writing-plans/plan-document-reviewer-prompt.md",
        },
    },
    "bmad": {
        "formula": "bmad-build",
        "base_import_binding": "gc",
        "base_import_source": "../gascity",
        "vendor": "bmad-method",
        "upstream": "https://github.com/bmad-code-org/BMAD-METHOD",
        "commit": "072d0a74587ef1ea744d51f2dd4436ee2895758d",
        "implementation_target": "bmad.story-implementer",
        "implementation_formula": "bmad-story-development",
        "implementation_item_formula": "bmad-story-development-item",
        "skills": {
            "requirements": "bmad-prd",
            "plan": "bmad-create-architecture",
            "plan-review": "bmad-create-architecture",
            "implementation-readiness": "bmad-check-implementation-readiness",
            "decompose": "bmad-create-epics-and-stories",
            "implement": "bmad-quick-dev",
            "review": "bmad-code-review",
        },
        "extra_steps": ["implementation-readiness"],
        "expansions": {
            "review": "bmad-code-review-flow",
        },
        "review_expansion": "bmad-code-review-flow",
        "gap_analysis_target": "bmad.story-self-checker",
        "review_fix_asset": "assets/workflows/bmad-code-review-flow/{target}.apply-bmad-review-findings.md",
    },
}


def load_formula(root: pathlib.Path, name: str) -> dict:
    return tomllib.loads((root / "formulas" / f"{name}.formula.toml").read_text(encoding="utf-8"))


def load_formula_from_dirs(formula_dirs: list[pathlib.Path], name: str) -> dict:
    for formula_dir in reversed(formula_dirs):
        path = formula_dir / f"{name}.formula.toml"
        if path.exists():
            return tomllib.loads(path.read_text(encoding="utf-8"))
    raise AssertionError(f"formula {name!r} not found in layered dirs")


def merged_steps(parent_steps: list[dict], child_steps: list[dict]) -> list[dict]:
    result = list(parent_steps)
    positions = {step["id"]: idx for idx, step in enumerate(result)}
    for step in child_steps:
        idx = positions.get(step["id"])
        if idx is None:
            positions[step["id"]] = len(result)
            result.append(step)
        else:
            result[idx] = step
    return result


def resolve_formula(root: pathlib.Path, name: str, seen: tuple[str, ...] = ()) -> dict:
    if name in seen:
        raise AssertionError(f"circular formula extends: {' -> '.join((*seen, name))}")
    data = load_formula(root, name)
    parents = data.get("extends", [])
    if not parents:
        return data

    merged: dict = {
        "formula": data["formula"],
        "description": data.get("description", ""),
        "version": data.get("version", 1),
        "contract": data.get("contract", ""),
        "target_required": data.get("target_required"),
        "vars": {},
        "steps": [],
    }
    for parent in parents:
        parent_data = resolve_formula(root, parent, (*seen, name))
        if not merged["contract"]:
            merged["contract"] = parent_data.get("contract", "")
        if merged["target_required"] is None:
            merged["target_required"] = parent_data.get("target_required")
        merged["vars"].update(parent_data.get("vars", {}))
        merged["steps"].extend(parent_data.get("steps", []))

    merged["vars"].update(data.get("vars", {}))
    merged["steps"] = merged_steps(merged["steps"], data.get("steps", []))
    if data.get("description"):
        merged["description"] = data["description"]
    return merged


def resolve_formula_from_dirs(formula_dirs: list[pathlib.Path], name: str, seen: tuple[str, ...] = ()) -> dict:
    if name in seen:
        raise AssertionError(f"circular formula extends: {' -> '.join((*seen, name))}")
    data = load_formula_from_dirs(formula_dirs, name)
    parents = data.get("extends", [])
    if not parents:
        return data

    merged: dict = {
        "formula": data["formula"],
        "description": data.get("description", ""),
        "version": data.get("version", 1),
        "contract": data.get("contract", ""),
        "target_required": data.get("target_required"),
        "vars": {},
        "steps": [],
    }
    for parent in parents:
        parent_data = resolve_formula_from_dirs(formula_dirs, parent, (*seen, name))
        if not merged["contract"]:
            merged["contract"] = parent_data.get("contract", "")
        if merged["target_required"] is None:
            merged["target_required"] = parent_data.get("target_required")
        merged["vars"].update(parent_data.get("vars", {}))
        merged["steps"].extend(parent_data.get("steps", []))

    merged["vars"].update(data.get("vars", {}))
    merged["steps"] = merged_steps(merged["steps"], data.get("steps", []))
    if data.get("description"):
        merged["description"] = data["description"]
    return merged


def effective_formula_text(root: pathlib.Path, name: str) -> str:
    data = load_formula(root, name)
    chunks = []
    for parent in data.get("extends", []):
        chunks.append(effective_formula_text(root, parent))
    formula_path = root / "formulas" / f"{name}.formula.toml"
    chunks.append(formula_path.read_text(encoding="utf-8"))
    for node in formula_nodes(data):
        description_file = node.get("description_file")
        if description_file:
            chunks.append((formula_path.parent / description_file).resolve().read_text(encoding="utf-8"))
    return "\n".join(chunks)


def effective_formula_text_from_dirs(formula_dirs: list[pathlib.Path], name: str) -> str:
    data = load_formula_from_dirs(formula_dirs, name)
    chunks = []
    for parent in data.get("extends", []):
        chunks.append(effective_formula_text_from_dirs(formula_dirs, parent))

    formula_path = None
    for formula_dir in reversed(formula_dirs):
        candidate = formula_dir / f"{name}.formula.toml"
        if candidate.exists():
            formula_path = candidate
            break
    if formula_path is None:
        raise AssertionError(f"formula {name!r} not found in layered dirs")

    chunks.append(formula_path.read_text(encoding="utf-8"))
    for node in formula_nodes(data):
        description_file = node.get("description_file")
        if description_file:
            chunks.append((formula_path.parent / description_file).resolve().read_text(encoding="utf-8"))
    return "\n".join(chunks)


def formula_nodes(data: dict) -> list[dict]:
    nodes = list(data.get("steps", []))
    for step in data.get("steps", []):
        nodes.extend(step.get("children", []))
    nodes.extend(data.get("template", []))
    for template in data.get("template", []):
        nodes.extend(template.get("children", []))
    return nodes


def node_description(root: pathlib.Path, node: dict) -> str:
    description_file = node.get("description_file")
    if description_file:
        return (root / "formulas" / description_file).resolve().read_text(encoding="utf-8")
    return node["description"]


def route_target_default(target: str, vars: dict) -> str:
    if target.startswith("{{") and target.endswith("}}"):
        var_name = target.removeprefix("{{").removesuffix("}}").strip()
        if var_name not in vars:
            raise AssertionError(f"templated route target {target!r} has no matching formula var")
        default = vars[var_name].get("default", "")
        if not default:
            raise AssertionError(f"templated route target {target!r} var has no default")
        return default
    if target.startswith("{") and target.endswith("}"):
        var_name = target.removeprefix("{").removesuffix("}").strip()
        if var_name not in vars:
            raise AssertionError(f"expansion route target {target!r} has no matching formula var")
        default = vars[var_name].get("default", "")
        if not default:
            raise AssertionError(f"expansion route target {target!r} var has no default")
        return default
    return target


def assert_role_route_target(test_case: unittest.TestCase, target: str, vars: dict) -> None:
    resolved = route_target_default(target, vars)
    test_case.assertTrue(resolved.startswith("gc."))
    test_case.assertIn(resolved.removeprefix("gc."), ROLE_AGENTS)
    test_case.assertNotIn("workflows.", resolved)


def assert_pack_or_role_route_target(
    test_case: unittest.TestCase,
    target: str,
    vars: dict,
    pack_root: pathlib.Path,
    pack_name: str,
) -> None:
    resolved = route_target_default(target, vars)
    if resolved.startswith("gc."):
        test_case.assertIn(resolved.removeprefix("gc."), ROLE_AGENTS)
        return

    prefix = f"{pack_name}."
    test_case.assertTrue(resolved.startswith(prefix), f"{resolved!r} must target {prefix}* or gc.*")
    local_agent = resolved.removeprefix(prefix)
    test_case.assertTrue((pack_root / "agents" / local_agent / "agent.toml").is_file())


class FormulaAssetTests(unittest.TestCase):
    def test_expected_formula_set_is_convoy_first(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        paths = sorted((root / "formulas").glob("*.formula.toml"))

        self.assertEqual({path.name.removesuffix(".formula.toml") for path in paths}, FORMULAS)
        for path in paths:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            name = path.name.removesuffix(".formula.toml")
            self.assertEqual(data["formula"], name)
            self.assertEqual(data["contract"], "graph.v2")
            var_names = set(data.get("vars", {}))
            self.assertNotIn("issue", var_names)
            self.assertNotIn("bead_id", var_names)
            self.assertNotIn("convoy_id", var_names, f"{path.name} must not redeclare reserved convoy_id")

    def test_expected_role_agents_are_providerless(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        roles_pack = tomllib.loads((root / "roles" / "pack.toml").read_text(encoding="utf-8"))
        paths = sorted((root / "roles" / "agents").glob("*/agent.toml"))

        self.assertEqual(roles_pack["pack"]["name"], "gc-roles")
        self.assertEqual({path.parent.name for path in paths}, ROLE_AGENTS)
        for path in paths:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["scope"], "rig")
            self.assertTrue(data["fallback"])
            self.assertNotIn("provider", data, f"{path} must inherit the city/workspace provider by default")
            self.assertTrue((path.parent / "prompt.template.md").is_file())
        self.assertIn(root / "roles" / "agents" / "run-operator" / "agent.toml", paths)

    def test_role_agent_prompts_include_graph_claim_protocol(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        shared_lines = (
            root / "roles" / "prompts" / "shared" / "gc-role-worker.md.tmpl"
        ).read_text(encoding="utf-8").splitlines()
        expected = "\n".join(shared_lines[1:-1]).strip()

        for fragment in (
            "GC_CLAIM",
            "`gc hook --claim --json` is the only permitted discovery source",
            "gc hook --claim --json",
            "CLAIMED_BEAD_ID",
            "CLAIM_REJECTED",
            "gc runtime drain-ack",
            "gc.continuation_group",
            "gc.scope_role=teardown",
            "check for more routed work before draining",
            "running the same `GC_CLAIM` block again",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, expected)
        self.assertNotIn("bd update \"$WORK_ID\" --claim --json", expected)

        for agent_name in ROLE_AGENTS:
            prompt = root / "roles" / "agents" / agent_name / "prompt.template.md"
            with self.subTest(agent=agent_name):
                self.assertEqual(prompt.read_text(encoding="utf-8").strip(), expected)

    def test_role_worker_protocol_fragment_matches_shared_prompt(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        shared = root / "roles" / "prompts" / "shared" / "gc-role-worker.md.tmpl"

        for fragment in (
            root / "template-fragments" / "gc-role-worker.template.md",
            root / "roles" / "template-fragments" / "gc-role-worker.template.md",
        ):
            with self.subTest(fragment=fragment):
                self.assertEqual(fragment.read_text(encoding="utf-8"), shared.read_text(encoding="utf-8"))

        pack_root = root.parent
        for pack_name in THIRD_PARTY_BUILD_PACKS:
            fragment = pack_root / pack_name / "template-fragments" / "gc-role-worker.template.md"
            with self.subTest(fragment=fragment):
                self.assertEqual(fragment.read_text(encoding="utf-8"), shared.read_text(encoding="utf-8"))

    def test_third_party_agents_include_gc_claim_protocol(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[2]
        include = '{{ template "gc-role-worker" . }}'
        expected_fragment = (
            root / "gascity" / "roles" / "prompts" / "shared" / "gc-role-worker.md.tmpl"
        ).read_text(encoding="utf-8")

        for pack_name in THIRD_PARTY_BUILD_PACKS:
            prompts = sorted((root / pack_name / "agents").glob("*/prompt.template.md"))
            self.assertGreater(len(prompts), 0, f"{pack_name} must define agent prompts")
            for prompt in prompts:
                with self.subTest(pack=pack_name, agent=prompt.parent.name):
                    text = prompt.read_text(encoding="utf-8")
                    self.assertIn(include, text)
                    self.assertEqual(text.count(include), 1)
                    local_fragment = prompt.parent / "template-fragments" / "gc-role-worker.template.md"
                    self.assertEqual(local_fragment.read_text(encoding="utf-8"), expected_fragment)

    def test_formula_route_targets_are_backed_by_providerless_role_agents(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        for path in sorted((root / "formulas").glob("*.formula.toml")):
            name = path.name.removesuffix(".formula.toml")
            data = resolve_formula(root, name)
            for step in data.get("steps", []):
                target = step.get("metadata", {}).get("gc.run_target", "")
                if not target:
                    continue
                with self.subTest(formula=path.name, step=step["id"], target=target):
                    assert_role_route_target(self, target, data.get("vars", {}))

    def test_formula_catalog_metadata_marks_user_runnable_workflows(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        catalog_names: set[str] = set()
        for path in sorted((root / "formulas").glob("*.formula.toml")):
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            name = path.name.removesuffix(".formula.toml")
            catalog = data.get("catalog")
            if catalog is None:
                continue
            with self.subTest(formula=name):
                self.assertEqual(catalog["name"], name)
                self.assertIsInstance(catalog.get("description"), str)
                self.assertGreater(len(catalog["description"].strip()), 0)
            catalog_names.add(name)

        self.assertEqual(catalog_names, CATALOG_FORMULAS)

    def test_build_base_is_full_lifecycle_virtual_contract(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = load_formula(root, "build-base")

        self.assertTrue(data["internal"])
        self.assertTrue(data["target_required"])
        self.assertNotIn("catalog", data)
        self.assertEqual([step["id"] for step in data["steps"]], BUILD_BASE_STEPS)
        self.assertNotIn("compound", BUILD_BASE_STEPS)
        self.assertEqual(data["vars"]["implementation_target"]["default"], "gc.implementation-worker")

        route_by_step = {step["id"]: step["metadata"]["gc.run_target"] for step in data["steps"]}
        self.assertEqual(route_by_step["prepare"], "gc.run-operator")
        self.assertEqual(route_by_step["requirements"], "gc.requirements-planner")
        self.assertEqual(route_by_step["plan"], "gc.design-author")
        self.assertEqual(route_by_step["plan-review"], "gc.review-synthesizer")
        self.assertEqual(route_by_step["decompose"], "gc.task-decomposer")
        self.assertEqual(route_by_step["implement"], "{{implementation_target}}")
        self.assertEqual(route_by_step["implement-same-session"], "{{implementation_target}}")
        self.assertEqual(route_by_step["review"], "gc.implementation-reviewer")
        self.assertEqual(route_by_step["finalize"], "gc.run-operator")
        self.assertEqual(route_by_step["publish"], "gc.publisher")

        for step in data["steps"]:
            description = node_description(root, step)
            with self.subTest(step=step["id"]):
                self.assertIn("override", description.lower())
                self.assertIn("build-base", description)

        decompose = next(step for step in data["steps"] if step["id"] == "decompose")
        decompose_description = node_description(root, decompose)
        for fragment in (
            "gc.input_convoy_id",
            "implementation convoy",
            "workflow root bead",
            "before closing",
        ):
            with self.subTest(step="decompose", fragment=fragment):
                self.assertIn(fragment, decompose_description)

        prepare = next(step for step in data["steps"] if step["id"] == "prepare")
        prepare_description = node_description(root, prepare)
        for fragment in (
            "artifact_root: {{artifact_root}}",
            "context_path: {{context_path}}",
            "requirements_path: {{requirements_path}}",
            "plan_path: {{plan_path}}",
            "decomposition_path: {{decomposition_path}}",
            "drain_policy: {{drain_policy}}",
            "implementation_target: {{implementation_target}}",
            "max_iterations: {{max_iterations}}",
            "push: {{push}}",
            "open_pr: {{open_pr}}",
            "plain scalar strings",
            "--metadata",
            "--set-metadata 'key=value'",
            "Do not write",
            'values like `"false"` or `"10"`',
        ):
            with self.subTest(step="prepare", fragment=fragment):
                self.assertIn(fragment, prepare_description)

    def test_build_basic_extends_full_lifecycle_base(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = load_formula(root, "build-basic")
        resolved = resolve_formula(root, "build-basic")

        self.assertEqual(data["extends"], ["build-base"])
        self.assertEqual([step["id"] for step in resolved["steps"]], BUILD_BASE_STEPS)
        self.assertEqual(data["catalog"]["name"], "build-basic")
        text = effective_formula_text(root, "build-basic")
        for fragment in (
            "generate-requirements",
            "implementation-plan",
            "design-review",
            "create-beads",
            "implementation summary path",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        self.assertNotIn('id = "compound"', text)

        decompose = next(step for step in data["steps"] if step["id"] == "decompose")
        decompose_description = node_description(root, decompose)
        for fragment in (
            "gc.input_convoy_id",
            "implementation convoy",
            "workflow root bead",
            "before closing",
        ):
            with self.subTest(step="decompose", fragment=fragment):
                self.assertIn(fragment, decompose_description)

    def test_third_party_build_packs_extend_base_and_vendor_sources(self) -> None:
        gascity_root = pathlib.Path(__file__).resolve().parents[1]
        packs_root = gascity_root.parent
        for pack_name, expected in THIRD_PARTY_BUILD_PACKS.items():
            with self.subTest(pack=pack_name):
                pack_root = packs_root / pack_name
                formula_name = expected["formula"]
                data = load_formula(pack_root, formula_name)
                resolved = resolve_formula_from_dirs(
                    [gascity_root / "formulas", pack_root / "formulas"],
                    formula_name,
                )

                self.assertEqual(data["extends"], ["build-base"])
                self.assertEqual(data["formula"], formula_name)
                self.assertEqual(data["catalog"]["name"], formula_name)
                self.assertEqual(data["vars"]["implementation_target"]["default"], expected["implementation_target"])
                expected_steps = BUILD_BASE_STEPS + expected.get("extra_steps", [])
                self.assertEqual([step["id"] for step in resolved["steps"]], expected_steps)
                self.assertNotIn("compound", [step["id"] for step in resolved["steps"]])
                step_by_id = {step["id"]: step for step in data["steps"]}
                if "implementation-readiness" in expected.get("extra_steps", []):
                    self.assertEqual(step_by_id["implementation-readiness"]["needs"], ["decompose"])
                    self.assertEqual(
                        step_by_id["implementation-readiness"]["metadata"]["gc.run_target"],
                        "bmad.readiness-reviewer",
                    )
                    self.assertEqual(step_by_id["implement"]["needs"], ["implementation-readiness"])
                    self.assertEqual(
                        step_by_id["implement-same-session"]["needs"],
                        ["implementation-readiness"],
                    )
                self.assertEqual(step_by_id["implement"]["metadata"]["gc.run_target"], "{{implementation_target}}")
                self.assertNotIn("expand", step_by_id["implement"])
                self.assertEqual(step_by_id["implement"]["condition"], "{{drain_policy}} == separate")
                self.assertEqual(step_by_id["implement"]["drain"]["context"], "separate")
                self.assertEqual(step_by_id["implement"]["drain"]["formula"], expected["implementation_formula"])
                self.assertEqual(step_by_id["implement"]["drain"]["member_access"], "exclusive")
                self.assertEqual(
                    step_by_id["implement-same-session"]["metadata"]["gc.run_target"],
                    "{{implementation_target}}",
                )
                self.assertEqual(
                    step_by_id["implement-same-session"]["condition"],
                    "{{drain_policy}} == same-session",
                )
                self.assertEqual(step_by_id["implement-same-session"]["drain"]["context"], "shared")
                self.assertEqual(
                    step_by_id["implement-same-session"]["drain"]["formula"],
                    expected["implementation_item_formula"],
                )
                self.assertEqual(
                    step_by_id["implement-same-session"]["drain"]["member_access"],
                    "exclusive",
                )
                self.assertEqual(
                    step_by_id["implement-same-session"]["drain"]["on_item_failure"],
                    "skip_remaining",
                )
                self.assertTrue(step_by_id["implement-same-session"]["drain"]["item"]["single_lane"])
                review_step = step_by_id["review"]
                self.assertEqual(review_step["expand"], expected["review_expansion"])
                self.assertEqual(
                    review_step["expand_vars"],
                    {
                        "implementation_target": "{{implementation_target}}",
                    },
                )

                pack_data = tomllib.loads((pack_root / "pack.toml").read_text(encoding="utf-8"))
                self.assertEqual(pack_data["pack"]["name"], pack_name)
                base_import = pack_data["imports"][expected["base_import_binding"]]
                self.assertEqual(base_import["source"], expected["base_import_source"])

                vendor_root = pack_root / "vendor" / expected["vendor"]
                self.assertTrue((vendor_root / "LICENSE").is_file())
                upstream = tomllib.loads((vendor_root / "upstream.toml").read_text(encoding="utf-8"))["upstream"]
                self.assertEqual(upstream["source"], expected["upstream"])
                self.assertEqual(upstream["commit"], expected["commit"])
                self.assertEqual(upstream["license"], "MIT")

                formula_text = effective_formula_text_from_dirs(
                    [gascity_root / "formulas", pack_root / "formulas"],
                    formula_name,
                )
                for step_id, skill_name in expected["skills"].items():
                    self.assertTrue((vendor_root / "skills" / skill_name / "SKILL.md").is_file())
                    self.assertTrue((pack_root / "skills" / skill_name / "SKILL.md").is_file())
                    self.assertIn(f"assets/workflows/{formula_name}/{step_id}.md", formula_text)

                for persona_asset in expected.get("persona_assets", set()):
                    self.assertTrue((vendor_root / "agents" / persona_asset).is_file())

                for prompt_asset in expected.get("prompt_assets", set()):
                    self.assertTrue((vendor_root / prompt_asset).is_file())

                decompose_text = effective_formula_text_from_dirs(
                    [gascity_root / "formulas", pack_root / "formulas"],
                    formula_name,
                )
                if pack_name == "bmad":
                    decompose_text = (pack_root / "assets/workflows/bmad-build/decompose.md").read_text(
                        encoding="utf-8",
                    )
                for fragment in (
                    "gc.input_convoy_id",
                    "implementation convoy",
                    "workflow root bead",
                    "before closing",
                ):
                    with self.subTest(pack=pack_name, step="decompose", fragment=fragment):
                        self.assertIn(fragment, decompose_text)

    def test_third_party_build_steps_expand_native_delegation_to_gascity_formulas(self) -> None:
        gascity_root = pathlib.Path(__file__).resolve().parents[1]
        packs_root = gascity_root.parent
        for pack_name, expected in THIRD_PARTY_BUILD_PACKS.items():
            pack_root = packs_root / pack_name
            build = load_formula(pack_root, expected["formula"])
            step_by_id = {step["id"]: step for step in build["steps"]}

            for step_id, expansion_name in expected["expansions"].items():
                with self.subTest(pack=pack_name, step=step_id, expansion=expansion_name):
                    self.assertEqual(step_by_id[step_id]["expand"], expansion_name)
                    expansion = load_formula(pack_root, expansion_name)
                    self.assertEqual(expansion["formula"], expansion_name)
                    self.assertEqual(expansion["type"], "expansion")
                    self.assertEqual(expansion["contract"], "graph.v2")

                    nodes = formula_nodes(expansion)
                    self.assertGreaterEqual(len(nodes), 4)
                    text = effective_formula_text(pack_root, expansion_name)
                    self.assertIn("Gas City", text)
                    self.assertIn("Do not invoke provider-native subagents", text)
                    self.assertNotIn("Task tool (general-purpose):", text)
                    self.assertNotIn("Dispatch implementer subagent", text)

                    for node in nodes:
                        target = node.get("metadata", {}).get("gc.run_target", "")
                        if target:
                            assert_pack_or_role_route_target(
                                self,
                                target,
                                expansion.get("vars", {}),
                                pack_root,
                                pack_name,
                            )
                        description_file = node.get("description_file")
                        self.assertIsNotNone(description_file)
                        self.assertTrue((pack_root / "formulas" / description_file).resolve().is_file())

            item_formula = load_formula(pack_root, expected["implementation_formula"])
            with self.subTest(pack=pack_name, item_formula=expected["implementation_formula"]):
                self.assertEqual(item_formula["formula"], expected["implementation_formula"])
                self.assertEqual(item_formula["contract"], "graph.v2")
                self.assertEqual(item_formula["extends"], ["do-work"])
                self.assertNotEqual(item_formula.get("type"), "expansion")
                self.assertTrue(item_formula["target_required"])

                resolved_item = resolve_formula_from_dirs(
                    [gascity_root / "formulas", pack_root / "formulas"],
                    expected["implementation_formula"],
                )
                if pack_name == "superpowers":
                    resolved_steps = {step["id"]: step for step in resolved_item["steps"]}
                    self.assertEqual(
                        set(resolved_steps),
                        {
                            "prepare-worktree",
                            "implement",
                            "write-failing-test",
                            "verify-test-fails",
                            "implement-change",
                            "verify-test-passes",
                            "record-item-result",
                            "close-source-anchor",
                        },
                    )
                    self.assertEqual(
                        {step_id: step.get("needs", []) for step_id, step in resolved_steps.items()},
                        {
                            "prepare-worktree": [],
                            "implement": ["prepare-worktree"],
                            "write-failing-test": ["implement"],
                            "verify-test-fails": ["write-failing-test"],
                            "implement-change": ["verify-test-fails"],
                            "verify-test-passes": ["implement-change"],
                            "record-item-result": ["verify-test-passes"],
                            "close-source-anchor": ["record-item-result"],
                        },
                    )
                else:
                    self.assertEqual(
                        [step["id"] for step in resolved_item["steps"]],
                        ["prepare-worktree", "implement", "close-source-anchor"],
                    )
                self.assertTrue(any(step["id"] == "implement" for step in item_formula["steps"]))
                text = effective_formula_text_from_dirs(
                    [gascity_root / "formulas", pack_root / "formulas"],
                    expected["implementation_formula"],
                )
                self.assertIn("Gas City", text)
                self.assertIn("Do not invoke provider-native subagents", text)
                self.assertNotIn("Task tool (general-purpose):", text)
                self.assertNotIn("Dispatch implementer subagent", text)

                for node in formula_nodes(resolved_item):
                    target = node.get("metadata", {}).get("gc.run_target", "")
                    if target:
                        assert_pack_or_role_route_target(
                            self,
                            target,
                            resolved_item.get("vars", {}),
                            pack_root,
                            pack_name,
                        )
                    description_file = node.get("description_file")
                    self.assertIsNotNone(description_file)
                    self.assertTrue(
                        any(
                            (formula_dir / description_file).resolve().is_file()
                            for formula_dir in (gascity_root / "formulas", pack_root / "formulas")
                        )
                    )

            shared_item_formula = load_formula(pack_root, expected["implementation_item_formula"])
            with self.subTest(pack=pack_name, item_formula=expected["implementation_item_formula"]):
                self.assertEqual(shared_item_formula["formula"], expected["implementation_item_formula"])
                self.assertEqual(shared_item_formula["contract"], "graph.v2")
                self.assertEqual(shared_item_formula["extends"], ["do-work-item"])
                self.assertNotEqual(shared_item_formula.get("type"), "expansion")
                self.assertTrue(shared_item_formula["target_required"])
                self.assertTrue(shared_item_formula["internal"])
                self.assertTrue(shared_item_formula["single_lane"])

                resolved_shared = resolve_formula_from_dirs(
                    [gascity_root / "formulas", pack_root / "formulas"],
                    expected["implementation_item_formula"],
                )
                if pack_name == "superpowers":
                    resolved_steps = {step["id"]: step for step in resolved_shared["steps"]}
                    self.assertEqual(
                        set(resolved_steps),
                        {
                            "implement-item",
                            "write-failing-test",
                            "verify-test-fails",
                            "implement-change",
                            "verify-test-passes",
                            "record-item-result",
                            "close-source-anchor",
                        },
                    )
                    self.assertEqual(
                        {step_id: step.get("needs", []) for step_id, step in resolved_steps.items()},
                        {
                            "implement-item": [],
                            "write-failing-test": ["implement-item"],
                            "verify-test-fails": ["write-failing-test"],
                            "implement-change": ["verify-test-fails"],
                            "verify-test-passes": ["implement-change"],
                            "record-item-result": ["verify-test-passes"],
                            "close-source-anchor": ["record-item-result"],
                        },
                    )
                else:
                    self.assertEqual([step["id"] for step in resolved_shared["steps"]], ["implement-item"])
                self.assertTrue(any(step["id"] == "implement-item" for step in shared_item_formula["steps"]))
                text = effective_formula_text_from_dirs(
                    [gascity_root / "formulas", pack_root / "formulas"],
                    expected["implementation_item_formula"],
                )
                self.assertIn("Gas City", text)
                self.assertIn("Do not invoke provider-native subagents", text)
                self.assertNotIn("Task tool (general-purpose):", text)
                self.assertNotIn("Dispatch implementer subagent", text)

                for node in formula_nodes(resolved_shared):
                    target = node.get("metadata", {}).get("gc.run_target", "")
                    if target:
                        assert_pack_or_role_route_target(
                            self,
                            target,
                            resolved_shared.get("vars", {}),
                            pack_root,
                            pack_name,
                        )
                    description_file = node.get("description_file")
                    self.assertIsNotNone(description_file)
                    self.assertTrue(
                        any(
                            (formula_dir / description_file).resolve().is_file()
                            for formula_dir in (gascity_root / "formulas", pack_root / "formulas")
                        )
                    )

            review_expansion = load_formula(pack_root, expected["review_expansion"])
            with self.subTest(pack=pack_name, expansion=expected["review_expansion"], route="review-fix"):
                self.assertEqual(
                    review_expansion["vars"]["implementation_target"]["default"],
                    expected["implementation_target"],
                )
                self.assertNotIn("drain_policy", review_expansion["vars"])
                review_fix_targets = [
                    node.get("metadata", {}).get("gc.run_target")
                    for node in formula_nodes(review_expansion)
                    if node.get("metadata", {}).get("gc.continuation_group", "").endswith("fixes")
                ]
                self.assertIn("{implementation_target}", review_fix_targets)
                gap_targets = [
                    node.get("metadata", {}).get("gc.run_target")
                    for node in formula_nodes(review_expansion)
                    if node["id"].endswith(".gap-analysis-review")
                ]
                self.assertEqual(gap_targets, [expected["gap_analysis_target"]])

    def test_superpowers_decomposition_keeps_procedure_in_drain_formula(self) -> None:
        packs_root = pathlib.Path(__file__).resolve().parents[2]
        pack_root = packs_root / "superpowers"
        build = load_formula(pack_root, "superpowers-build")
        step_by_id = {step["id"]: step for step in build["steps"]}

        self.assertIn("decompose", step_by_id)
        decompose_text = (
            pack_root / "assets" / "workflows" / "superpowers-build" / "decompose.md"
        ).read_text(encoding="utf-8")
        for fragment in (
            "Do not copy the plan checkbox steps into the implementation bead",
            "gc.input_convoy_id",
            "implementation convoy",
            "workflow root bead",
            "before closing",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, decompose_text)

        for formula_name in ("superpowers-development", "superpowers-development-item"):
            formula = load_formula(pack_root, formula_name)
            text = effective_formula_text_from_dirs(
                [packs_root / "gascity" / "formulas", pack_root / "formulas"],
                formula_name,
            )
            with self.subTest(formula=formula_name):
                self.assertIn("test-driven-development", text)
                self.assertIn("superpowers-task-{{issue}}", text)
                self.assertNotIn("superpowers-spec-fixes", text)
                self.assertNotIn("superpowers-quality-fixes", text)
                continuation_groups = [
                    node.get("metadata", {}).get("gc.continuation_group", "")
                    for node in formula_nodes(formula)
                    if node.get("metadata", {}).get("gc.continuation_group")
                ]
                self.assertGreaterEqual(len(continuation_groups), 5)
                self.assertTrue(
                    all(group == "superpowers-task-{{issue}}" for group in continuation_groups)
                )

    def test_superpowers_brainstorming_expansion_preserves_stock_loops(self) -> None:
        packs_root = pathlib.Path(__file__).resolve().parents[2]
        pack_root = packs_root / "superpowers"
        formula = load_formula(pack_root, "superpowers-brainstorming")
        templates = {template["id"]: template for template in formula["template"]}

        self.assertEqual(
            [template["id"] for template in formula["template"]],
            [
                "{target}.setup-superpowers-brainstorming",
                "{target}.superpowers-design-approval-loop",
                "{target}.superpowers-written-spec-loop",
                "{target}",
            ],
        )

        design_loop = templates["{target}.superpowers-design-approval-loop"]
        self.assertEqual(design_loop["needs"], ["{target}.setup-superpowers-brainstorming"])
        self.assertEqual(design_loop["check"]["max_attempts"], 6)
        self.assertEqual(
            design_loop["check"]["check"],
            {
                "mode": "exec",
                "path": ".gc/scripts/checks/design-review-approved.sh",
                "timeout": "10m",
            },
        )
        self.assertEqual(
            [child["id"] for child in design_loop["children"]],
            ["{target}.brainstorm-design", "{target}.confirm-design-approval"],
        )
        self.assertEqual(
            design_loop["children"][1]["metadata"]["gc.continuation_group"],
            "superpowers-design-fixes",
        )

        spec_loop = templates["{target}.superpowers-written-spec-loop"]
        self.assertEqual(spec_loop["needs"], ["{target}.superpowers-design-approval-loop"])
        self.assertEqual(spec_loop["check"]["max_attempts"], 6)
        self.assertEqual(
            spec_loop["check"]["check"],
            {
                "mode": "exec",
                "path": ".gc/scripts/checks/design-review-approved.sh",
                "timeout": "10m",
            },
        )
        self.assertEqual(
            [child["id"] for child in spec_loop["children"]],
            [
                "{target}.write-requirements-spec",
                "{target}.review-written-spec",
                "{target}.apply-spec-feedback",
                "{target}.confirm-spec-approval",
            ],
        )
        self.assertEqual(
            spec_loop["children"][-1]["metadata"]["gc.continuation_group"],
            "superpowers-spec-fixes",
        )

        design_approval = (
            pack_root
            / "assets"
            / "workflows"
            / "superpowers-brainstorming"
            / "{target}.confirm-design-approval.md"
        ).read_text(encoding="utf-8")
        write_spec = (
            pack_root
            / "assets"
            / "workflows"
            / "superpowers-brainstorming"
            / "{target}.write-requirements-spec.md"
        ).read_text(encoding="utf-8")
        spec_approval = (
            pack_root
            / "assets"
            / "workflows"
            / "superpowers-brainstorming"
            / "{target}.confirm-spec-approval.md"
        ).read_text(encoding="utf-8")
        final_requirements = (
            pack_root
            / "assets"
            / "workflows"
            / "superpowers-brainstorming"
            / "{target}.md"
        ).read_text(encoding="utf-8")

        self.assertIn("design_review.verdict=done|iterate", design_approval)
        self.assertIn("stock `User approves design?` gate", design_approval)
        self.assertIn("Use `done` only after explicit approval", design_approval)
        self.assertIn("gc session wait", design_approval)
        self.assertIn("send exactly one mail", design_approval)
        self.assertIn("gc mail send human", design_approval)
        self.assertIn("gc.build.design_gate_mail_sent=true", design_approval)
        self.assertIn("waiting-human", design_approval)
        self.assertIn("silence", design_approval)
        self.assertIn("re-opens the design loop", design_approval)
        self.assertIn("revision summary", design_approval)
        self.assertIn("specific design sections", design_approval)
        self.assertIn("stock Superpowers checklist items 6-7", write_spec)
        self.assertIn("Spec self-review", write_spec)
        self.assertIn("stock design-doc state", write_spec)
        self.assertIn("docs/superpowers/specs/", write_spec)
        self.assertIn("On repeated attempts", write_spec)
        self.assertIn("without clobbering loop feedback", write_spec)
        self.assertIn("written spec", spec_approval)
        self.assertIn("stock `User reviews spec?` approval gate", spec_approval)
        self.assertIn("stock checklist item 8", spec_approval)
        self.assertIn("change request loops back through the written spec pass", spec_approval)
        self.assertIn("transition to downstream planning", spec_approval)
        self.assertIn("design_review.verdict=done|iterate", spec_approval)
        self.assertIn("Use `done` only after explicit approval", spec_approval)
        self.assertIn("gc session wait", spec_approval)
        self.assertIn("send exactly one mail", spec_approval)
        self.assertIn("gc mail send human", spec_approval)
        self.assertIn("gc.build.spec_gate_mail_sent=true", spec_approval)
        self.assertIn("waiting-human", spec_approval)
        self.assertIn("silence", spec_approval)
        self.assertIn("spec revision summary", spec_approval)
        self.assertIn("stock brainstorming terminal state", final_requirements)
        self.assertIn("where Superpowers\nwould invoke `writing-plans`", final_requirements)
        self.assertIn("stock checklist item 9", final_requirements)
        self.assertIn("do not invoke that skill directly", final_requirements)
        self.assertIn("let the parent `superpowers-build` plan step", final_requirements)

        brainstorm_design = (
            pack_root
            / "assets"
            / "workflows"
            / "superpowers-brainstorming"
            / "{target}.brainstorm-design.md"
        ).read_text(encoding="utf-8")
        for fragment in (
            "stock Superpowers checklist items 1-5",
            "project context inspected",
            "Offer Visual Companion",
            "own message",
            "installed Visual\n  Companion guidance",
            "one clarifying question at a time",
            "two or three approaches",
            "recommended design presented in sections",
            "On repeated attempts",
            "revise that candidate in place",
            "unapproved",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, brainstorm_design)

        review_written_spec = (
            pack_root
            / "assets"
            / "workflows"
            / "superpowers-brainstorming"
            / "{target}.review-written-spec.md"
        ).read_text(encoding="utf-8")
        self.assertIn("stock spec reviewer subagent as a Gas City graph lane", review_written_spec)
        self.assertIn("spec-document-reviewer-prompt.md", review_written_spec)

        vendor_skill_root = pack_root / "vendor" / "superpowers" / "skills" / "brainstorming"
        installed_skill_root = pack_root / "skills" / "brainstorming"
        for relative_path in (
            "SKILL.md",
            "spec-document-reviewer-prompt.md",
            "visual-companion.md",
        ):
            with self.subTest(asset=relative_path):
                self.assertEqual(
                    (installed_skill_root / relative_path).read_text(encoding="utf-8"),
                    (vendor_skill_root / relative_path).read_text(encoding="utf-8"),
                )

        for relative_path in (
            "scripts/frame-template.html",
            "scripts/helper.js",
            "scripts/server.cjs",
            "scripts/start-server.sh",
            "scripts/stop-server.sh",
        ):
            with self.subTest(asset=relative_path):
                installed_path = installed_skill_root / relative_path
                self.assertTrue(installed_path.exists())

        for relative_path in ("scripts/start-server.sh", "scripts/stop-server.sh"):
            with self.subTest(executable=relative_path):
                self.assertTrue(os.access(installed_skill_root / relative_path, os.X_OK))

    def test_third_party_workflow_assets_guard_against_native_subagent_execution(self) -> None:
        gascity_root = pathlib.Path(__file__).resolve().parents[1]
        packs_root = gascity_root.parent
        forbidden_active_delegation = (
            "also use `{{pack_root}}/vendor/superpowers/skills/subagent-driven-development/SKILL.md`",
            "Hand `{spec_file}` to a sub-agent/task and let it implement",
            "Dispatch implementer subagent",
            "Task tool (general-purpose):",
            "{{pack_root}}/vendor",
            "{{pack_root}}/assets/scripts",
            "/SKILL.md",
            "Launch or reuse",
            "base `implement` formula",
            "read vendored files by path",
            "formula expansion is required",
            "formula already created",
        )

        for pack_name, expected in THIRD_PARTY_BUILD_PACKS.items():
            with self.subTest(pack=pack_name):
                pack_root = packs_root / pack_name
                asset_text = "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in sorted((pack_root / "assets" / "workflows").glob("**/*.md"))
                )
                self.assertIn("Do not invoke provider-native subagents", asset_text)
                for phrase in forbidden_active_delegation:
                    self.assertNotIn(phrase, asset_text)

                implement_asset = (
                    pack_root / "assets" / "workflows" / expected["formula"] / "implement.md"
                ).read_text(encoding="utf-8")
                self.assertIn("{{implementation_target}}", implement_asset)
                self.assertIn("assigned", implement_asset)
                self.assertIn("implementation", implement_asset)
                self.assertIn("convoy", implement_asset)
                self.assertNotIn("expensive", implement_asset)

                review_fix_asset = (pack_root / expected["review_fix_asset"]).read_text(encoding="utf-8")
                for fragment in (
                    "{{implementation_target}}",
                    "review-fix artifact",
                    "Do not invoke provider-native subagents",
                    "graph lane is the delegation\nmechanism",
                ):
                    with self.subTest(pack=pack_name, asset=expected["review_fix_asset"], fragment=fragment):
                        self.assertIn(fragment, review_fix_asset)

                build_text = effective_formula_text_from_dirs(
                    [gascity_root / "formulas", pack_root / "formulas"],
                    expected["formula"],
                )
                for step_id, expansion_name in expected["expansions"].items():
                    with self.subTest(pack=pack_name, step=step_id):
                        self.assertIn(f'expand = "{expansion_name}"', build_text)
                        self.assertIn(f"assets/workflows/{expected['formula']}/{step_id}.md", build_text)
                self.assertIn(f'formula = "{expected["implementation_formula"]}"', build_text)
                self.assertIn(f'formula = "{expected["implementation_item_formula"]}"', build_text)

    def test_build_methodology_assets_do_not_prompt_formula_launch_or_path_skills(self) -> None:
        gascity_root = pathlib.Path(__file__).resolve().parents[1]
        packs_root = gascity_root.parent
        workflow_roots = [
            gascity_root / "assets" / "workflows" / name
            for name in (
                "build-base",
                "build-basic",
                "github-issue-fix-base",
                "implement",
                "same-session-implement",
            )
        ]
        workflow_roots.extend(
            packs_root / pack_name / "assets" / "workflows"
            for pack_name in THIRD_PARTY_BUILD_PACKS
        )
        agent_roots = [
            packs_root / pack_name / "agents"
            for pack_name in THIRD_PARTY_BUILD_PACKS
        ]
        forbidden_fragments = (
            "{{pack_root}}/vendor",
            "/SKILL.md",
            "Launch or reuse",
            "launch or reuse",
            "base `implement` formula",
            "run implement on",
            "run implement until",
            "run the public\ngap-analysis formula",
            "run the generic review workflow",
            "This expansion formula",
            "The expansion formula",
            "formula owns",
            "formula already created",
            "formula expansion is required",
            "formula's child steps",
        )

        paths: list[pathlib.Path] = []
        for root in (*workflow_roots, *agent_roots):
            paths.extend(sorted(root.glob("**/*.md")))

        for path in paths:
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                with self.subTest(path=path.relative_to(packs_root), fragment=fragment):
                    self.assertNotIn(fragment, text)

    def test_formula_node_descriptions_delegate_to_shadowable_assets(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        for formula_path in sorted((root / "formulas").glob("*.formula.toml")):
            formula = formula_path.name.removesuffix(".formula.toml")
            data = tomllib.loads(formula_path.read_text(encoding="utf-8"))
            for node in formula_nodes(data):
                with self.subTest(formula=formula, node=node["id"]):
                    self.assertNotIn("description", node)
                    description_file = node.get("description_file")
                    self.assertEqual(
                        description_file,
                        f"../assets/workflows/{formula}/{node['id']}.md",
                    )
                    self.assertTrue((formula_path.parent / description_file).resolve().is_file())

    def test_implement_formula_uses_core_drain_steps(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = tomllib.loads((root / "formulas" / "implement.formula.toml").read_text(encoding="utf-8"))

        self.assertNotIn("infra_target", data["vars"])
        self.assertNotIn("hard_target", data["vars"])
        self.assertNotIn("worker_target", data["vars"])
        self.assertEqual(data["vars"]["implementation_target"]["default"], "gc.implementation-worker")

        step_ids = [step["id"] for step in data["steps"]]
        self.assertEqual(
            step_ids,
            ["prepare", "drain-separate", "drain-same-session", "wait-for-drain", "summarize", "publish"],
        )

        separate = data["steps"][1]
        same = data["steps"][2]
        self.assertEqual(data["steps"][0]["metadata"]["gc.run_target"], "gc.run-operator")
        self.assertEqual(separate["metadata"]["gc.run_target"], "{{implementation_target}}")
        self.assertEqual(separate["condition"], "{{drain_policy}} == separate")
        self.assertEqual(separate["drain"]["context"], "separate")
        self.assertEqual(separate["drain"]["formula"], "do-work")
        self.assertEqual(separate["drain"]["member_access"], "exclusive")
        self.assertEqual(same["metadata"]["gc.run_target"], "{{implementation_target}}")
        self.assertEqual(same["condition"], "{{drain_policy}} == same-session")
        self.assertEqual(same["drain"]["context"], "shared")
        self.assertEqual(same["drain"]["formula"], "do-work-item")
        self.assertEqual(same["drain"]["member_access"], "exclusive")
        self.assertTrue(same["drain"]["item"]["single_lane"])
        self.assertEqual(same["drain"]["on_item_failure"], "skip_remaining")
        self.assertEqual(data["steps"][3]["metadata"]["gc.run_target"], "gc.run-operator")
        self.assertEqual(data["steps"][4]["metadata"]["gc.run_target"], "gc.run-operator")
        self.assertEqual(data["steps"][5]["metadata"]["gc.run_target"], "gc.publisher")
        self.assertEqual(data["steps"][5]["needs"], ["summarize"])
        summarize = node_description(root, data["steps"][4])
        self.assertIn("gc.implementation.summary_path", summarize)
        wait = node_description(root, data["steps"][3])
        for fragment in (
            "Wait only on the core drain control bead",
            "gc.drain_manifest.v1",
            "Do not wait for or inspect downstream steps",
            "summarize, workflow-finalize, or root workflow closure",
            "cannot progress\nuntil this bead closes",
            "close only this wait step",
        ):
            with self.subTest(step="wait-for-drain", fragment=fragment):
                self.assertIn(fragment, wait)
        publish = node_description(root, data["steps"][5])
        for fragment in (
            "push {{push}}",
            "open_pr {{open_pr}}",
            "summary_path {{summary_path}}",
            "publish",
        ):
            with self.subTest(step="publish", fragment=fragment):
                self.assertIn(fragment, publish)

        helper = tomllib.loads((root / "formulas" / "same-session-implement.formula.toml").read_text(encoding="utf-8"))
        self.assertEqual(helper["vars"]["implementation_target"]["default"], "gc.implementation-worker")
        self.assertEqual(helper["steps"][0]["metadata"]["gc.run_target"], "{{implementation_target}}")
        self.assertEqual(helper["steps"][0]["drain"]["formula"], "do-work-item")
        self.assertEqual(helper["steps"][0]["drain"]["member_access"], "exclusive")

    def test_implement_prepare_is_validation_only(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = tomllib.loads((root / "formulas" / "implement.formula.toml").read_text(encoding="utf-8"))
        prepare = next(step for step in data["steps"] if step["id"] == "prepare")

        for fragment in (
            "validation only",
            "Do not edit source files in the launcher checkout",
            "Do not create, modify, or commit source code",
            "Do not run implementation or test-fix loops",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, node_description(root, prepare))

    def test_item_implementation_formulas_route_role_agents(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]

        do_work = tomllib.loads((root / "formulas" / "do-work.formula.toml").read_text(encoding="utf-8"))
        self.assertNotIn("infra_target", do_work["vars"])
        self.assertNotIn("hard_target", do_work["vars"])
        self.assertEqual(do_work["vars"]["implementation_target"]["default"], "gc.implementation-worker")
        self.assertEqual(do_work["steps"][0]["metadata"]["gc.run_target"], "gc.run-operator")
        self.assertEqual(do_work["steps"][1]["metadata"]["gc.run_target"], "{{implementation_target}}")
        self.assertEqual(do_work["steps"][2]["metadata"]["gc.run_target"], "gc.run-operator")

        do_work_item = tomllib.loads((root / "formulas" / "do-work-item.formula.toml").read_text(encoding="utf-8"))
        self.assertNotIn("infra_target", do_work_item["vars"])
        self.assertNotIn("hard_target", do_work_item["vars"])
        self.assertEqual(do_work_item["vars"]["implementation_target"]["default"], "gc.implementation-worker")
        self.assertEqual(do_work_item["steps"][0]["metadata"]["gc.run_target"], "{{implementation_target}}")

    def test_do_work_formula_requires_persisted_item_worktree(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        do_work = tomllib.loads((root / "formulas" / "do-work.formula.toml").read_text(encoding="utf-8"))
        steps = {step["id"]: step for step in do_work["steps"]}

        prepare = node_description(root, steps["prepare-worktree"])
        for fragment in (
            "current step bead metadata",
            "gc.root_bead_id",
            "gc.input_convoy_id",
            "gc.synthetic_kind",
            "gc.drain_member_id",
            "worktrees/<source-anchor-id>",
            "git worktree add",
            "bd update <source-anchor-id> --set-metadata work_dir=",
            "Do not edit source files in the launcher checkout",
        ):
            with self.subTest(step="prepare-worktree", fragment=fragment):
                self.assertIn(fragment, prepare)

        implement = node_description(root, steps["implement"])
        for fragment in (
            "Read `work_dir` from the source anchor",
            "cd \"$WORKTREE\"",
            "fail this step before editing",
            "Do not edit files in the launcher checkout",
            "Leave the source anchor open",
        ):
            with self.subTest(step="implement", fragment=fragment):
                self.assertIn(fragment, implement)

        close_source = node_description(root, steps["close-source-anchor"])
        for fragment in (
            "Read `work_dir` from the source anchor",
            "close only `<source-anchor-id>`",
            "bd show <source-anchor-id> --json",
            "status=closed",
            "gc.outcome=pass",
            "if either check fails",
            "anchor before closing this step",
        ):
            with self.subTest(step="close-source-anchor", fragment=fragment):
                self.assertIn(fragment, close_source)

    def test_wrapper_formulas_route_role_agents(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]

        issue_fix = resolve_formula(root, "github-issue-fix")
        self.assertNotIn("infra_target", issue_fix["vars"])
        self.assertNotIn("hard_target", issue_fix["vars"])
        route_by_step = {step["id"]: step["metadata"]["gc.run_target"] for step in issue_fix["steps"]}
        self.assertEqual(route_by_step["snapshot"], "gc.run-operator")
        self.assertEqual(route_by_step["triage"], "gc.issue-triager")
        self.assertEqual(route_by_step["triage-gate"], "gc.run-operator")
        self.assertEqual(route_by_step["resume-or-create-run"], "gc.run-operator")
        self.assertEqual(route_by_step["update-status-started"], "gc.run-operator")
        self.assertEqual(route_by_step["generate-requirements"], "gc.requirements-planner")
        self.assertEqual(route_by_step["implementation-plan"], "gc.design-author")
        self.assertEqual(route_by_step["design-review"], "gc.review-synthesizer")
        self.assertEqual(route_by_step["create-beads"], "gc.task-decomposer")
        self.assertEqual(route_by_step["build"], "{{implementation_target}}")
        self.assertEqual(route_by_step["publish-pr"], "gc.publisher")
        self.assertEqual(route_by_step["finalize"], "gc.run-operator")

        design_review = load_formula(root, "github-issue-fix-design-review-work")
        self.assertEqual(set(design_review.get("vars", {})), {"mode"})
        design_review_text = effective_formula_text(root, "github-issue-fix-design-review-work")
        for target in (
            "gc.run-operator",
            "gc.design-implementation-reviewer",
            "gc.design-test-risk-reviewer",
            "gc.review-synthesizer",
        ):
            with self.subTest(formula="github-issue-fix-design-review-work", target=target):
                self.assertIn(f'"gc.run_target" = "{target}"', design_review_text)
        self.assertNotIn("reviewer_one_target", design_review_text)
        self.assertNotIn("reviewer_two_target", design_review_text)
        self.assertNotIn("synthesizer_target", design_review_text)

    def test_base_formulas_do_not_ship_private_workflow_language(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]

        self.assertFalse((root / "formulas" / "release.formula.toml").exists())
        for path in sorted((root / "formulas").glob("*.formula.toml")):
            raw_text = path.read_text(encoding="utf-8")
            text = raw_text.lower()
            with self.subTest(formula=path.name):
                self.assertNotIn("homebrew", text)
                self.assertNotIn("goreleaser", text)
                self.assertNotIn("gastownhall/gascity", text)
                self.assertNotIn("bugflow", text)
                self.assertNotIn("Ralph", raw_text)
                self.assertNotIn(".ralph", text)

    def test_report_formulas_are_targetless_and_report_only(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        for name in ("gap-analysis", "review"):
            data = tomllib.loads((root / "formulas" / f"{name}.formula.toml").read_text(encoding="utf-8"))
            self.assertEqual(data["mode"], "report")
            self.assertFalse(data["target_required"])
            self.assertEqual([step["id"] for step in data["steps"]], ["validate-context", "write-report"])

    def test_github_adapter_formulas_are_targetless_url_adapters(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        expected = {
            "github-issue-triage": ("github_issue_url", {"artifact_root", "post_mode", "triage_rubric_path"}),
            "github-pr-review": ("github_pr_url", {"artifact_root", "context_path", "post_mode"}),
            "github-issue-fix": (
                "github_issue_url",
                {
                    "artifact_root",
                    "mode",
                    "pr_mode",
                    "drain_policy",
                    "implementation_target",
                },
            ),
        }
        for name, (url_var, optional_vars) in expected.items():
            with self.subTest(name=name):
                data = resolve_formula(root, name)
                self.assertEqual(data["contract"], "graph.v2")
                self.assertFalse(data["target_required"])
                self.assertTrue(data["vars"][url_var]["required"])
                self.assertEqual(set(data["vars"]) - {url_var}, optional_vars)
                text = effective_formula_text(root, name)
                self.assertIn("{{pack_root}}/assets/scripts/github_api.py", text)
                self.assertNotIn("{{pack_root}}" + "/scripts/", text)

    def test_github_adapter_formulas_define_source_bead_contract(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        expected = {
            "github-issue-triage": ("issue", "gc.github.body_hash"),
            "github-issue-fix": ("issue", "gc.github.body_hash"),
            "github-pr-review": ("pull", "gc.github.head_sha"),
        }
        required_common = {
            "bd list --metadata-field gc.kind=github_source",
            "bd create",
            "bd update",
            "--external-ref",
            "gc.github.kind",
            "gc.github.repo",
            "gc.github.number",
            "gc.github.url",
            "gc.github.snapshot_path",
            "Do not route the source bead",
        }

        for name, (github_kind, idempotency_key) in expected.items():
            with self.subTest(name=name):
                text = effective_formula_text(root, name)
                for fragment in required_common:
                    self.assertIn(fragment, text)
                self.assertIn(f"gc.github.kind={github_kind}", text)
                self.assertIn(idempotency_key, text)

    def test_github_adapter_formulas_define_artifact_root_semantics(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        for name in ("github-issue-triage", "github-issue-fix", "github-pr-review"):
            with self.subTest(name=name):
                text = effective_formula_text(root, name)
                self.assertIn("{{pack_root}}/assets/scripts/artifacts.py root", text)
                self.assertIn("{{pack_root}}/assets/scripts/artifacts.py path", text)
                self.assertIn("artifact-root-relative", text)
                self.assertIn("not filesystem-root absolute", text)
                self.assertIn("gc.github.snapshot_path=<absolute source.json path>", text)

    def test_github_pr_review_delegates_with_explicit_review_artifacts(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = resolve_formula(root, "github-pr-review")
        text = effective_formula_text(root, "github-pr-review")
        reuse_current = node_description(root, next(step for step in data["steps"] if step["id"] == "reuse-current-head"))
        run_review = node_description(root, next(step for step in data["steps"] if step["id"] == "run-review"))
        render_comment = node_description(root, next(step for step in data["steps"] if step["id"] == "render-comment"))

        for fragment in (
            "gc.github.review_dir=<absolute review directory>",
            "gc.github.review_subject_path",
            "gc.github.review_report_path",
            "gc.github.comment_path",
            "gc.github.review_outcome",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        for fragment in (
            "gc.github.reused_current_output=true",
            "gc.github.reused_current_output=false",
            "gc.github.review_report_path",
            "gc.github.comment_path",
        ):
            with self.subTest(step="reuse-current-head", fragment=fragment):
                self.assertIn(fragment, reuse_current)
        for fragment in (
            "SUBJECT_PATH=<gc.github.review_dir>/subject.md",
            "REPORT_PATH=<gc.github.review_dir>/review-report.md",
            "gc sling gc.run-operator review --formula",
            "--var subject_path=\"$SUBJECT_PATH\"",
            "--var report_path=\"$REPORT_PATH\"",
            "review-outcome \"$REPORT_PATH\"",
            "gc.github.reused_current_output=true",
            "do not\nlaunch the generic `review` formula",
            "leave the reused\nartifacts untouched",
        ):
            with self.subTest(step="run-review", fragment=fragment):
                self.assertIn(fragment, run_review)
        for fragment in (
            "<gc.github.review_dir>/comment.md",
            "gc.github.reused_current_output=true",
            "do not\nrewrite the rendered comment",
            "real no-op path",
        ):
            with self.subTest(step="render-comment", fragment=fragment):
                self.assertIn(fragment, render_comment)

    def test_github_issue_fix_uses_implementation_plan_artifact_contract(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        text = effective_formula_text(root, "github-issue-fix")

        self.assertIn("implementation-plan.md", text)
        self.assertIn("implementation_plan_file", text)
        self.assertIn("create beads", text.lower())
        self.assertNotIn("design_file", text)

    def test_github_issue_fix_run_setup_publishes_plan_artifact_metadata(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = resolve_formula(root, "github-issue-fix")
        steps = {step["id"]: step for step in data["steps"]}

        setup = node_description(root, steps["resume-or-create-run"])
        requirements = node_description(root, steps["generate-requirements"])
        implementation_plan = node_description(root, steps["implementation-plan"])
        create_beads = node_description(root, steps["create-beads"])
        publish_pr = node_description(root, steps["publish-pr"])
        requirements_normalized = " ".join(requirements.split())
        implementation_plan_normalized = " ".join(implementation_plan.split())

        for fragment in (
            "bd update <root-bead-id>",
            "gc.github.run_dir",
            "gc.github.requirements_path",
            "gc.github.implementation_plan_path",
            "gc.github.design_path",
            "absolute path",
        ):
            with self.subTest(step="resume-or-create-run", fragment=fragment):
                self.assertIn(fragment, setup)
        for fragment in (
            "gc.github.requirements_path",
            "different path",
        ):
            with self.subTest(step="generate-requirements", fragment=fragment):
                self.assertIn(fragment, requirements_normalized)
        self.assertIn("Do not choose or invent", requirements)
        for fragment in (
            "gc.github.implementation_plan_path",
            "different path",
        ):
            with self.subTest(step="implementation-plan", fragment=fragment):
                self.assertIn(fragment, implementation_plan_normalized)
        self.assertIn("Do not choose or invent", implementation_plan)
        for step_name, text in (
            ("resume-or-create-run", setup),
            ("implementation-plan", implementation_plan),
            ("create-beads", create_beads),
            ("publish-pr", publish_pr),
        ):
            for fragment in (
                "passive wait + mail",
                "gc session wait",
                "gc mail send human",
                "mail_sent=true",
                "silence",
            ):
                with self.subTest(step=step_name, fragment=fragment):
                    self.assertIn(fragment, text)

    def test_github_issue_fix_reviews_implementation_plan_without_design_alias_step(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = resolve_formula(root, "github-issue-fix")
        steps = {step["id"]: step for step in data["steps"]}
        step_ids = [step["id"] for step in data["steps"]]

        self.assertNotIn("design", steps)
        self.assertLess(step_ids.index("implementation-plan"), step_ids.index("design-review"))
        self.assertEqual(steps["design-review"]["needs"], ["implementation-plan"])
        self.assertFalse((root / "assets" / "workflows" / "github-issue-fix-base" / "design.md").exists())

    def test_layered_github_issue_overrides_preserve_catalog_and_resolve(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            override_dir = pathlib.Path(tmp)
            (override_dir / "github-issue-fix.formula.toml").write_text(
                """
formula = "github-issue-fix"
extends = ["github-issue-fix-base"]
version = 1
contract = "graph.v2"
target_required = false

[catalog]
name = "github-issue-fix"
description = "Fix a GitHub issue with a local advanced design-review override."

[[steps]]
id = "design-review"
title = "Run local advanced design review"
needs = ["implementation-plan"]
metadata = { "gc.run_target" = "gc.review-synthesizer" }
description = "Override sink that preserves the base issue-fix protocol."
""".lstrip(),
                encoding="utf-8",
            )
            (override_dir / "github-issue-triage.formula.toml").write_text(
                """
formula = "github-issue-triage"
extends = ["github-issue-triage-base"]
version = 1
contract = "graph.v2"
target_required = false

[catalog]
name = "github-issue-triage"
description = "Triage a GitHub issue with a local triage-work override."

[[steps]]
id = "write-triage-report"
title = "Run local issue triage"
needs = ["reuse-current-body-hash"]
metadata = { "gc.run_target" = "gc.issue-triager" }
description = "Override sink that writes the base triage report contract."
""".lstrip(),
                encoding="utf-8",
            )

            layered_dirs = [root / "formulas", override_dir]
            issue_fix = resolve_formula_from_dirs(layered_dirs, "github-issue-fix")
            issue_triage = resolve_formula_from_dirs(layered_dirs, "github-issue-triage")

            self.assertEqual(load_formula_from_dirs(layered_dirs, "github-issue-fix")["catalog"]["name"], "github-issue-fix")
            self.assertEqual(
                load_formula_from_dirs(layered_dirs, "github-issue-triage")["catalog"]["name"],
                "github-issue-triage",
            )
            self.assertEqual(
                next(step for step in issue_fix["steps"] if step["id"] == "design-review")["needs"],
                ["implementation-plan"],
            )
            for data in (issue_fix, issue_triage):
                step_ids = {step["id"] for step in data["steps"]}
                for step in data["steps"]:
                    for need in step.get("needs", []):
                        with self.subTest(formula=data["formula"], step=step["id"], need=need):
                            self.assertIn(need, step_ids)

    def test_github_issue_triage_formula_requires_human_readable_analysis(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        text = effective_formula_text(root, "github-issue-triage")
        self.assertIn("human-readable analysis body", text)
        self.assertIn("## Summary", text)
        self.assertIn("## Evidence", text)
        self.assertIn("## Recommendation", text)
        self.assertIn("render-triage-comment", text)

    def test_github_issue_triage_uses_workflow_metadata_as_context_index(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        text = effective_formula_text(root, "github-issue-triage")

        required_fragments = {
            "workflow root metadata",
            "gc.root_bead_id",
            "gc.github.source_bead_id",
            "gc.github.triage_dir",
            "bd show <root-bead-id> --json",
            "bd update <root-bead-id>",
            "Read `gc.github.snapshot_path`",
            "Do not write a separate triage context file",
        }
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        self.assertNotIn("triage-context.json", text)

    def test_github_issue_triage_reuse_path_noops_downstream_steps(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = resolve_formula(root, "github-issue-triage")
        reuse_current = node_description(root, next(step for step in data["steps"] if step["id"] == "reuse-current-body-hash"))
        write_report = node_description(root, next(step for step in data["steps"] if step["id"] == "write-triage-report"))
        render_comment = node_description(root, next(step for step in data["steps"] if step["id"] == "render-comment"))

        for fragment in (
            "gc.github.reused_current_output=true",
            "gc.github.reused_current_output=false",
            "gc.github.triage_report_path",
            "gc.github.comment_path",
        ):
            with self.subTest(step="reuse-current-body-hash", fragment=fragment):
                self.assertIn(fragment, reuse_current)
        for fragment in (
            "gc.github.reused_current_output=true",
            "do not\n  investigate or rewrite `triage-report.md`",
            "leave the reused artifacts\n  untouched",
        ):
            with self.subTest(step="write-triage-report", fragment=fragment):
                self.assertIn(fragment, write_report)
        for fragment in (
            "gc.github.reused_current_output=true",
            "do not rewrite the rendered comment",
            "real no-op path",
        ):
            with self.subTest(step="render-comment", fragment=fragment):
                self.assertIn(fragment, render_comment)

    def test_github_issue_triage_snapshot_creates_triage_directory(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = resolve_formula(root, "github-issue-triage")
        snapshot = node_description(root, next(step for step in data["steps"] if step["id"] == "snapshot"))

        self.assertIn(
            '--relative "/github/issues/<owner>/<repo>/<number>/triage/<body-hash>/" --directory --mkdir-parents',
            snapshot,
        )

    def test_github_issue_triage_supports_rubric_override_without_protocol_override(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = resolve_formula(root, "github-issue-triage")
        text = effective_formula_text(root, "github-issue-triage")

        self.assertIn("triage_rubric_path", data["vars"])
        self.assertEqual(data["vars"]["triage_rubric_path"]["default"], "")
        self.assertIn("{{triage_rubric_path}}", text)
        self.assertIn("Optional rubric/prompt override path", text)
        self.assertIn("report behavior, not the metadata protocol", text)
        self.assertIn("must not override", text)
        self.assertIn("gc.github-issue-triage-report.v1", text)

    def test_github_issue_triage_human_gate_uses_runtime_metadata_in_step_body(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        data = resolve_formula(root, "github-issue-triage")

        gate = next(step for step in data["steps"] if step["id"] == "human-gate-sensitive-output")
        self.assertNotIn("condition", gate)
        self.assertIn("gc.github.triage_priority", node_description(root, gate))
        self.assertIn("no-op gate", node_description(root, gate))
        self.assertIn("gc.github.public_comment_gate", node_description(root, gate))

    def test_github_public_comment_post_steps_enforce_gate_contract(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        pr_review = resolve_formula(root, "github-pr-review")
        issue_triage = resolve_formula(root, "github-issue-triage")

        pr_gate = next(step for step in pr_review["steps"] if step["id"] == "human-gate-comment")
        self.assertNotIn("condition", pr_gate)
        issue_gate = next(step for step in issue_triage["steps"] if step["id"] == "human-gate-sensitive-output")

        checks = (
            ("github-pr-review gate", node_description(root, pr_gate)),
            (
                "github-pr-review post",
                node_description(root, next(step for step in pr_review["steps"] if step["id"] == "post-comment")),
            ),
            (
                "github-issue-triage gate",
                node_description(root, issue_gate),
            ),
            (
                "github-issue-triage post",
                node_description(root, next(step for step in issue_triage["steps"] if step["id"] == "post-comment")),
            ),
        )
        for label, text in checks:
            for fragment in (
                "gc.github.public_comment_gate",
                "approved",
                "not_required",
                "rejected",
                "revision_requested",
            ):
                with self.subTest(label=label, fragment=fragment):
                    self.assertIn(fragment, text)

        for label, text in (
            ("github-pr-review gate", node_description(root, pr_gate)),
            ("github-issue-triage gate", node_description(root, issue_gate)),
        ):
            for fragment in (
                "passive wait + mail",
                "gc session wait",
                "gc mail send human",
                "mail_sent=true",
                "silence",
            ):
                with self.subTest(label=label, fragment=fragment):
                    self.assertIn(fragment, text)

    def test_all_declared_formula_vars_are_rendered_into_graph_text(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        for path in sorted((root / "formulas").glob("*.formula.toml")):
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            text = effective_formula_text(root, path.name.removesuffix(".formula.toml"))
            for var_name in data.get("vars", {}):
                with self.subTest(formula=path.name, var=var_name):
                    if data.get("type") == "expansion":
                        self.assertTrue(
                            f"{{{{{var_name}}}}}" in text or f"{{{var_name}}}" in text,
                            f"{path.name} must render {var_name} as a runtime or expansion variable",
                        )
                    else:
                        self.assertIn(f"{{{{{var_name}}}}}", text)

    def test_check_scripts_are_executable_and_portable(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        scripts = sorted((root / "assets" / "scripts" / "checks").glob("*.sh"))

        self.assertEqual(
            [script.name for script in scripts],
            ["design-review-approved.sh", "gap-analysis-approved.sh", "implementation-review-approved.sh"],
        )
        for script in scripts:
            text = script.read_text(encoding="utf-8")
            self.assertTrue(os.access(script, os.X_OK), f"{script} must be executable")
            self.assertNotIn("/data/projects", text)
            self.assertNotIn("gascity-packs-worktrees", text)

    def test_bmad_story_development_emits_base_check_verdict(self) -> None:
        gascity_root = pathlib.Path(__file__).resolve().parents[1]
        bmad_root = gascity_root.parent / "bmad"

        for formula_name, step_id in (
            ("bmad-story-development", "implement"),
            ("bmad-story-development-item", "implement-item"),
        ):
            with self.subTest(formula=formula_name):
                formula = load_formula(bmad_root, formula_name)
                step = next(step for step in formula["steps"] if step["id"] == step_id)
                self.assertEqual(
                    step["check"]["check"]["path"],
                    ".gc/scripts/checks/implementation-review-approved.sh",
                )

        story_root = bmad_root / "assets" / "workflows" / "bmad-story-development"
        setup_text = (story_root / "setup-bmad-story-development.md").read_text(encoding="utf-8")
        self.assertIn("gc.outcome=pass", setup_text)

        apply_text = (story_root / "apply-story-findings.md").read_text(encoding="utf-8")
        self.assertIn("bmad_story.verdict=done", apply_text)
        self.assertIn("bmad_story.verdict=iterate", apply_text)
        self.assertIn("bmad_story.report_path=<fix summary path>", apply_text)
        self.assertIn("code_review.verdict=done", apply_text)
        self.assertIn("code_review.verdict=iterate", apply_text)
        self.assertIn("code_review.report_path=<fix summary path>", apply_text)

    def test_design_review_check_scopes_verdict_to_current_loop(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        script = root / "assets" / "scripts" / "checks" / "design-review-approved.sh"

        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            fake_bd = bin_dir / "bd"
            fake_bd.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "case \"$1\" in\n"
                "  show) cat \"$BD_SHOW_JSON\" ;;\n"
                "  list) cat \"$BD_LIST_JSON\" ;;\n"
                "  *) exit 2 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            fake_bd.chmod(0o755)

            show_json = tmp / "show.json"
            list_json = tmp / "list.json"
            show_json.write_text(
                """[
  {
    "id": "loop",
    "metadata": {
      "gc.root_bead_id": "root",
      "gc.attempt": "1",
      "gc.step_ref": "requirements.superpowers-brainstorming-loop.iteration.1"
    }
  }
]""",
                encoding="utf-8",
            )
            list_json.write_text(
                """[
  {
    "id": "current-loop-feedback",
    "metadata": {
      "gc.root_bead_id": "root",
      "gc.attempt": "1",
      "gc.scope_ref": "requirements.superpowers-brainstorming-loop.iteration.1",
      "gc.continuation_group": "design-review-fixes",
      "design_review.verdict": "iterate"
    }
  },
  {
    "id": "old-loop-approval",
    "metadata": {
      "gc.root_bead_id": "root",
      "gc.attempt": "1",
      "gc.scope_ref": "plan-review.superpowers-plan-review-loop.iteration.1",
      "gc.continuation_group": "design-review-fixes",
      "design_review.verdict": "done"
    }
  }
]""",
                encoding="utf-8",
            )

            env = {
                **os.environ,
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                "BD_SHOW_JSON": str(show_json),
                "BD_LIST_JSON": str(list_json),
                "GC_BEAD_ID": "loop",
            }
            result = subprocess.run(
                [str(script)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("needs another pass", result.stdout)

    def test_design_review_check_finds_verdict_from_logical_loop_root(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        script = root / "assets" / "scripts" / "checks" / "design-review-approved.sh"

        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            fake_bd = bin_dir / "bd"
            fake_bd.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "case \"$1\" in\n"
                "  show) cat \"$BD_SHOW_JSON\" ;;\n"
                "  list) cat \"$BD_LIST_JSON\" ;;\n"
                "  *) exit 2 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            fake_bd.chmod(0o755)

            show_json = tmp / "show.json"
            list_json = tmp / "list.json"
            show_json.write_text(
                """[
  {
    "id": "loop-root",
    "metadata": {
      "gc.root_bead_id": "root",
      "gc.step_id": "requirements.superpowers-design-approval-loop",
      "gc.step_ref": "superpowers-build.requirements.superpowers-design-approval-loop"
    }
  }
]""",
                encoding="utf-8",
            )
            list_json.write_text(
                """[
  {
    "id": "unrelated-plan-approval",
    "updated_at": "2026-06-08T09:40:00Z",
    "metadata": {
      "gc.root_bead_id": "root",
      "gc.attempt": "1",
      "gc.ralph_step_id": "plan-review.superpowers-plan-review-loop",
      "gc.scope_ref": "plan-review.superpowers-plan-review-loop.iteration.1",
      "design_review.verdict": "done"
    }
  },
  {
    "id": "design-review-feedback",
    "updated_at": "2026-06-08T09:41:00Z",
    "metadata": {
      "gc.root_bead_id": "root",
      "gc.attempt": "1",
      "gc.ralph_step_id": "requirements.superpowers-design-approval-loop",
      "gc.scope_ref": "requirements.superpowers-design-approval-loop.iteration.1",
      "design_review.verdict": "iterate"
    }
  },
  {
    "id": "design-approval",
    "updated_at": "2026-06-08T09:42:00Z",
    "metadata": {
      "gc.root_bead_id": "root",
      "gc.attempt": "1",
      "gc.ralph_step_id": "requirements.superpowers-design-approval-loop",
      "gc.scope_ref": "requirements.superpowers-design-approval-loop.iteration.1",
      "design_review.verdict": "done"
    }
  }
]""",
                encoding="utf-8",
            )

            env = {
                **os.environ,
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                "BD_SHOW_JSON": str(show_json),
                "BD_LIST_JSON": str(list_json),
                "GC_BEAD_ID": "loop-root",
            }
            result = subprocess.run(
                [str(script)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Design review approved", result.stdout)

    def test_design_review_check_finds_verdict_from_child_loop_member(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        script = root / "assets" / "scripts" / "checks" / "design-review-approved.sh"

        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            bin_dir = tmp / "bin"
            bin_dir.mkdir()
            fake_bd = bin_dir / "bd"
            fake_bd.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "case \"$1\" in\n"
                "  show) cat \"$BD_SHOW_JSON\" ;;\n"
                "  list) cat \"$BD_LIST_JSON\" ;;\n"
                "  *) exit 2 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            fake_bd.chmod(0o755)

            show_json = tmp / "show.json"
            list_json = tmp / "list.json"
            show_json.write_text(
                """[
  {
    "id": "design-approval-child",
    "metadata": {
      "gc.root_bead_id": "root",
      "gc.attempt": "1",
      "gc.step_id": "requirements.confirm-design-approval",
      "gc.step_ref": "requirements.superpowers-design-approval-loop.iteration.1.requirements.confirm-design-approval",
      "gc.scope_ref": "requirements.superpowers-design-approval-loop.iteration.1"
    }
  }
]""",
                encoding="utf-8",
            )
            list_json.write_text(
                """[
  {
    "id": "design-approval-child",
    "updated_at": "2026-06-08T09:42:00Z",
    "metadata": {
      "gc.root_bead_id": "root",
      "gc.attempt": "1",
      "gc.ralph_step_id": "requirements.superpowers-design-approval-loop",
      "gc.scope_ref": "requirements.superpowers-design-approval-loop.iteration.1",
      "design_review.verdict": "done"
    }
  }
]""",
                encoding="utf-8",
            )

            env = {
                **os.environ,
                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
                "BD_SHOW_JSON": str(show_json),
                "BD_LIST_JSON": str(list_json),
                "GC_BEAD_ID": "design-approval-child",
            }
            result = subprocess.run(
                [str(script)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Design review approved", result.stdout)

    def test_superpowers_plan_review_loop_has_single_verdict_owner(self) -> None:
        packs_root = pathlib.Path(__file__).resolve().parents[2]
        setup = (
            packs_root
            / "superpowers"
            / "assets"
            / "workflows"
            / "superpowers-plan-review"
            / "{target}.setup-superpowers-plan-review.md"
        ).read_text(encoding="utf-8")
        review = (
            packs_root
            / "superpowers"
            / "assets"
            / "workflows"
            / "superpowers-plan-review"
            / "{target}.plan-document-review.md"
        ).read_text(encoding="utf-8")
        apply = (
            packs_root
            / "superpowers"
            / "assets"
            / "workflows"
            / "superpowers-plan-review"
            / "{target}.apply-plan-feedback.md"
        ).read_text(encoding="utf-8")
        finalize = (
            packs_root
            / "superpowers"
            / "assets"
            / "workflows"
            / "superpowers-plan-review"
            / "{target}.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn("design_review.verdict=", review)
        self.assertIn("design_review.review_verdict", review)
        self.assertIn("design_review.verdict=done|iterate", apply)
        self.assertIn("gc.outcome=pass", apply)

        self.assertIn("plan-review-context.md", setup)
        self.assertIn("plan-review-report.md", setup)
        self.assertIn("plan-review-apply-summary.md", setup)
        self.assertIn("gc.build.plan_review_context_path", setup)
        self.assertIn("gc.build.plan_review_report_path", setup)
        self.assertIn("gc.build.plan_review_apply_summary_path", setup)
        self.assertIn("gc.build.plan_review_context_path", review)
        self.assertIn("gc.build.plan_review_report_path", review)
        self.assertIn("gc.build.plan_review_apply_summary_path", apply)
        self.assertIn("gc.build.plan_review_status=approved", finalize)
        self.assertIn("gc.build.plan_review_approved_at", finalize)
        self.assertIn("gc.build.plan_review_report_path", finalize)
        self.assertIn("gc.build.plan_review_apply_summary_path", finalize)
        self.assertIn("gc.build.plan_review_status=failed", finalize)

    def test_superpowers_code_review_loop_has_single_verdict_owner(self) -> None:
        packs_root = pathlib.Path(__file__).resolve().parents[2]
        workflow_dir = (
            packs_root
            / "superpowers"
            / "assets"
            / "workflows"
            / "superpowers-code-review"
        )
        setup = (workflow_dir / "{target}.setup-superpowers-code-review.md").read_text(
            encoding="utf-8"
        )
        request = (workflow_dir / "{target}.request-code-review.md").read_text(
            encoding="utf-8"
        )
        gap = (workflow_dir / "{target}.gap-analysis-review.md").read_text(
            encoding="utf-8"
        )
        process = (workflow_dir / "{target}.process-code-review.md").read_text(
            encoding="utf-8"
        )
        finalize = (workflow_dir / "{target}.md").read_text(encoding="utf-8")

        self.assertIn("code-review-context.md", setup)
        self.assertIn("implementation-review-report.md", setup)
        self.assertIn("gap-analysis-report.md", setup)
        self.assertIn("review-fix-summary.md", setup)
        self.assertIn("gc.build.code_review_context_path", setup)
        self.assertIn("gc.build.code_review_report_path", setup)
        self.assertIn("gc.build.gap_analysis_report_path", setup)
        self.assertIn("gc.build.review_fix_summary_path", setup)

        self.assertIn("code_review.review_verdict", request)
        self.assertIn("code_review.review_report_path", request)
        self.assertNotIn("code_review.verdict=done", request)
        self.assertNotIn("code_review.report_path=<", request)

        self.assertIn("code_review.gap_verdict", gap)
        self.assertIn("code_review.gap_report_path", gap)
        self.assertNotIn("code_review.verdict=done", gap)
        self.assertNotIn("code_review.report_path=<", gap)

        self.assertIn("code_review.verdict=done|iterate", process)
        self.assertIn("code_review.report_path=<review fix summary path>", process)
        self.assertIn("gc.build.code_review_status=approved", process)
        self.assertIn("gc.build.code_review_status=draft", process)

        self.assertIn("gc.build.code_review_status=approved", finalize)
        self.assertIn("gc.build.code_review_approved_at", finalize)
        self.assertIn("gc.build.code_review_status=failed", finalize)


if __name__ == "__main__":
    unittest.main()
