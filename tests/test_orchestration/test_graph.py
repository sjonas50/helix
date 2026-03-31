"""Tests for LangGraph workflow graph and IPC."""



from helix.orchestration.coordinator import (
    GraphState,
    _route_after_execute,
    create_workflow_graph,
)
from helix.orchestration.workers import (
    TOOLS_BY_ROLE,
    get_tools_for_role,
    validate_hierarchy_depth,
)


class TestWorkflowGraph:
    def test_graph_compiles(self):
        graph = create_workflow_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = create_workflow_graph()
        # LangGraph compiled graphs have a .get_graph() method
        g = graph.get_graph()
        # g.nodes may be a dict (keys are node IDs) or list of objects
        raw = g.nodes
        node_ids = set(raw) if isinstance(raw, dict) else {n.id for n in raw}
        assert "plan" in node_ids
        assert "execute" in node_ids
        assert "approve" in node_ids
        assert "verify" in node_ids
        assert "fail" in node_ids

    def test_route_to_verify_on_success(self):
        state = GraphState(phase="EXECUTING", workflow_id="test", org_id="test")
        assert _route_after_execute(state) == "verify"

    def test_route_to_fail_on_errors(self):
        state = GraphState(phase="EXECUTING", errors=["something broke"])
        assert _route_after_execute(state) == "fail"

    def test_route_to_approve_on_pending(self):
        state = GraphState(
            phase="EXECUTING", pending_approval={"action": "update_opp"}
        )
        assert _route_after_execute(state) == "approve"


class TestWorkers:
    def test_researcher_has_read_only_tools(self):
        tools = get_tools_for_role("researcher")
        tool_names = {t.name for t in tools}
        assert "search_data" in tool_names
        assert "read_record" in tool_names
        assert "write_record" not in tool_names

    def test_implementer_has_write_tools(self):
        tools = get_tools_for_role("implementer")
        tool_names = {t.name for t in tools}
        assert "write_record" in tool_names
        assert "send_notification" in tool_names

    def test_hierarchy_depth_validation(self):
        assert validate_hierarchy_depth(0, max_depth=2)
        assert validate_hierarchy_depth(1, max_depth=2)
        assert not validate_hierarchy_depth(2, max_depth=2)

    def test_all_roles_defined(self):
        assert set(TOOLS_BY_ROLE.keys()) == {
            "researcher",
            "implementer",
            "verifier",
            "coordinator",
        }
