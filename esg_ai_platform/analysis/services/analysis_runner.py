from analysis.services.gri_rule_engine import run_rule_engine_analysis


def run_gri_305_analysis(report, analysis_job=None):
    return run_rule_engine_analysis(report, analysis_job=analysis_job)
