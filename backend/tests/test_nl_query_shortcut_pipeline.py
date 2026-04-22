from backend.app.services.query_shortcuts import NlQueryShortcutPipeline

def test_pipeline_exposes_ordered_handlers():
    names = [fn.__name__ for fn in NlQueryShortcutPipeline.HANDLERS]
    assert names[0] == "try_project_guide_answer"
    assert "try_parent_bound_child_answer" in names
    assert "try_risk_success_answer" in names
