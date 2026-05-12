from cxx_modules_converter_lib import (
    find_cycles,
)


def test_find_cycles_no_cycles():
    """Test graph without cycles"""
    graph: dict[str, set[str]] = {'A': {'B', 'C'}, 'B': {'D'}, 'C': {'D'}, 'D': set()}
    cycles = find_cycles(graph)
    assert cycles == []


def test_find_cycles_simple_cycle():
    """Test simple cycle"""
    graph: dict[str, set[str]] = {'A': {'B'}, 'B': {'C'}, 'C': {'A'}}
    cycles = find_cycles(graph)
    assert len(cycles) == 1
    assert set(cycles[0]) == {'A', 'B', 'C'}


def test_find_cycles_self_reference():
    """Test self-reference cycle"""
    graph: dict[str, set[str]] = {'A': {'A'}, 'B': {'C'}, 'C': set()}
    cycles = find_cycles(graph)
    # Self-references should be skipped
    assert len(cycles) == 0


def test_find_cycles_complex_cycles():
    """Test complex cycles"""
    graph: dict[str, set[str]] = {
        'A': {'B', 'C'},
        'B': {'D'},
        'C': {'D', 'E'},
        'D': {'A'},  # Creates cycles A->B->D->A and A->C->D->A
        'E': {'F'},
        'F': {'C'},  # Creates cycle C->E->F->C
    }
    cycles = find_cycles(graph)
    assert len(cycles) == 2

    # Check that both cycles are found
    cycle_sets = [set(cycle) for cycle in cycles]
    # The algorithm may find either A->B->D->A or A->C->D->A cycle
    # Both are valid representations of the same cycle in this graph
    assert {'A', 'B', 'D'} in cycle_sets or {'A', 'C', 'D'} in cycle_sets
    assert {'C', 'E', 'F'} in cycle_sets


def test_find_cycles_disconnected_components():
    """Test disconnected components"""
    graph: dict[str, set[str]] = {
        'A': {'B'},
        'B': {'C'},
        'C': {'A'},  # First cycle
        'D': {'E'},
        'E': {'F'},
        'F': {'D'},  # Second cycle
        'G': set(),  # Isolated node
    }
    cycles = find_cycles(graph)
    assert len(cycles) == 2

    # Check that both cycles are found
    cycle_sets = [set(cycle) for cycle in cycles]
    assert {'A', 'B', 'C'} in cycle_sets
    assert {'D', 'E', 'F'} in cycle_sets
